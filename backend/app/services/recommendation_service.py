from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.core.enums import MasteryStatus
from app.domain.recommendation import (
    STATE_COLD_START,
    STATE_NO_ELIGIBLE_PROBLEM,
    STATE_OK,
    STATE_PREREQUISITE_BLOCKED,
    CandidateProblemInput,
    PrerequisiteInput,
    SkillMasteryInput,
    build_explanation_payload,
    evaluate_prerequisite_readiness,
    rank_candidates,
    score_candidate,
    select_target_skill,
)
from app.models.assessment import Recommendation
from app.models.problem import Problem
from app.models.skill import Skill
from app.models.user import User
from app.repositories.assessment_repository import MasteryRepository, RecommendationRepository
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.problem_repository import LearnerProblemStateData, ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.assessment import UserSkillMasteryItem
from app.schemas.catalog import ProblemSkillLink
from app.schemas.recommendation import (
    NextRecommendationResponse,
    RecommendationExplanation,
    RecommendationItem,
    RecommendationListResponse,
    RecommendationProblemSummary,
)
from sqlalchemy.orm import Session


class RecommendationService:
    def __init__(
        self,
        recommendation_repository: RecommendationRepository,
        mastery_repository: MasteryRepository,
        skill_repository: SkillRepository,
        problem_repository: ProblemRepository,
        attempt_repository: AttemptRepository,
        topic_repository: TopicRepository,
    ) -> None:
        self._recommendations = recommendation_repository
        self._mastery = mastery_repository
        self._skills = skill_repository
        self._problems = problem_repository
        self._attempts = attempt_repository
        self._topics = topic_repository

    def generate_for_submission(
        self,
        session: Session,
        user: User,
        source_attempt_id: UUID,
        *,
        limit: int = 5,
    ) -> NextRecommendationResponse:
        if self._recommendations.exists_for_attempt(session, user.id, source_attempt_id):
            return self.get_next(session, user.id)
        return self._generate(session, user.id, source_attempt_id=source_attempt_id, limit=limit)

    def get_recommendations(
        self,
        session: Session,
        user_id: UUID,
        *,
        limit: int = 5,
        target_skill_slug: str | None = None,
        refresh: bool = False,
    ) -> RecommendationListResponse:
        if refresh or not self._recommendations.list_latest_batch(session, user_id, limit=1):
            return self._generate_list(
                session,
                user_id,
                target_skill_slug=target_skill_slug,
                limit=limit,
                source_attempt_id=None,
            )
        batch = self._recommendations.list_latest_batch(session, user_id, limit=limit)
        if target_skill_slug:
            batch = [
                item for item in batch if item.explanation.get("target_skill") == target_skill_slug
            ]
        return self._batch_to_list_response(session, user_id, batch)

    def get_next(
        self,
        session: Session,
        user_id: UUID,
        *,
        target_skill_slug: str | None = None,
        refresh: bool = False,
    ) -> NextRecommendationResponse:
        list_response = self.get_recommendations(
            session,
            user_id,
            limit=1,
            target_skill_slug=target_skill_slug,
            refresh=refresh,
        )
        recommendation = list_response.items[0] if list_response.items else None
        return NextRecommendationResponse(
            recommendation=recommendation,
            target_skill=list_response.target_skill,
            state=list_response.state,
            message=list_response.message,
        )

    def get_recommendation_detail(
        self, session: Session, user_id: UUID, recommendation_id: UUID
    ) -> RecommendationItem | None:
        rec = self._recommendations.find_by_id_for_user(session, user_id, recommendation_id)
        if rec is None:
            return None
        return self._to_item(session, rec)

    def get_for_skill(
        self, session: Session, user_id: UUID, skill_slug: str
    ) -> NextRecommendationResponse:
        existing = self._find_skill_recommendation(session, user_id, skill_slug)
        if existing is not None:
            return NextRecommendationResponse(
                recommendation=existing,
                target_skill=self._target_skill_item(session, user_id, skill_slug),
                state=STATE_OK,
                message=None,
            )
        return self._generate(
            session,
            user_id,
            target_skill_slug=skill_slug,
            limit=1,
            source_attempt_id=None,
        )

    def _find_skill_recommendation(
        self, session: Session, user_id: UUID, skill_slug: str
    ) -> RecommendationItem | None:
        skill = self._skills.find_by_slug(session, skill_slug)
        if skill is None:
            return None
        rec = self._recommendations.list_for_user_skill_latest(session, user_id, skill.id)
        if rec is None:
            return None
        stale_cutoff = datetime.now(UTC) - timedelta(hours=24)
        if rec.generated_at.replace(tzinfo=UTC) < stale_cutoff:
            return None
        return self._to_item(session, rec)

    def _generate_list(
        self,
        session: Session,
        user_id: UUID,
        *,
        target_skill_slug: str | None = None,
        limit: int = 5,
        source_attempt_id: UUID | None = None,
    ) -> RecommendationListResponse:
        next_response = self._generate(
            session,
            user_id,
            target_skill_slug=target_skill_slug,
            limit=limit,
            source_attempt_id=source_attempt_id,
        )
        items: list[RecommendationItem] = []
        if next_response.recommendation is not None:
            items.append(next_response.recommendation)
            batch = self._recommendations.list_latest_batch(session, user_id, limit=limit)
            if len(batch) > 1:
                items = [self._to_item(session, rec) for rec in batch]
        return RecommendationListResponse(
            items=items,
            target_skill=next_response.target_skill,
            state=next_response.state,
            message=next_response.message,
        )

    def _generate(
        self,
        session: Session,
        user_id: UUID,
        *,
        target_skill_slug: str | None = None,
        limit: int = 5,
        source_attempt_id: UUID | None = None,
    ) -> NextRecommendationResponse:
        reference = datetime.now(UTC)
        skill_inputs = self._build_skill_inputs(session, user_id)
        target = select_target_skill(skill_inputs, explicit_skill_slug=target_skill_slug)

        if target is None:
            return NextRecommendationResponse(
                recommendation=None,
                target_skill=None,
                state=STATE_NO_ELIGIBLE_PROBLEM,
                message="No skills with available problems were found.",
            )

        target_uuid = UUID(target.skill_id)
        prerequisites = self._build_prerequisites(session, user_id, target_uuid)
        readiness, eligible, _ = evaluate_prerequisite_readiness(prerequisites)

        if not eligible:
            return NextRecommendationResponse(
                recommendation=None,
                target_skill=self._target_skill_item_from_selection(session, user_id, target),
                state=STATE_PREREQUISITE_BLOCKED,
                message=(
                    f"Prerequisites for {target.skill_name} are not ready yet. "
                    "Strengthen prerequisite skills first."
                ),
            )

        problems = self._skills.find_linked_published_problems(session, target_uuid)
        if not problems:
            return NextRecommendationResponse(
                recommendation=None,
                target_skill=self._target_skill_item_from_selection(session, user_id, target),
                state=STATE_NO_ELIGIBLE_PROBLEM,
                message=f"No published problems are linked to {target.skill_name}.",
            )

        problem_ids = [problem.id for problem in problems]
        learner_states = self._problems.get_learner_states(session, user_id, problem_ids)
        last_success = self._attempts.get_last_success_times(session, user_id, problem_ids)

        scored = []
        for problem in problems:
            candidate = self._build_candidate_input(
                problem,
                target_uuid,
                learner_states,
                last_success,
                reference,
            )
            if candidate is None:
                continue
            result = score_candidate(candidate, target, readiness, eligible)
            if result is not None:
                scored.append(result)

        ranked = rank_candidates(scored)
        if not ranked:
            state = STATE_NO_ELIGIBLE_PROBLEM
            message = "No eligible problems match your current readiness."
            if target.selection_reason == "cold_start":
                state = STATE_COLD_START
                message = "Complete a foundational problem to build initial evidence."
            return NextRecommendationResponse(
                recommendation=None,
                target_skill=self._target_skill_item_from_selection(session, user_id, target),
                state=state,
                message=message,
            )

        generated_at = reference
        persisted: list[Recommendation] = []
        for rank, candidate in enumerate(ranked[:limit], start=1):
            explanation = build_explanation_payload(target, candidate, prerequisites)
            rec = self._recommendations.create(
                session,
                user_id=user_id,
                problem_id=UUID(candidate.problem_id),
                target_skill_id=target_uuid,
                rank=rank,
                score=candidate.components.final_score,
                explanation=explanation,
                generated_at=generated_at,
                source_attempt_id=source_attempt_id,
            )
            persisted.append(rec)

        top = self._to_item(session, persisted[0])
        target_item = self._target_skill_item_from_selection(session, user_id, target)
        state = STATE_COLD_START if target.selection_reason == "cold_start" else STATE_OK
        return NextRecommendationResponse(
            recommendation=top,
            target_skill=target_item,
            state=state,
            message=None,
        )

    def _build_skill_inputs(self, session: Session, user_id: UUID) -> list[SkillMasteryInput]:
        skills = self._skills.list_all(session)
        masteries = {row.skill_id: row for row in self._mastery.list_for_user(session, user_id)}
        inputs: list[SkillMasteryInput] = []
        for skill in skills:
            mastery = masteries.get(skill.id)
            problem_count = self._skills.count_linked_published_problems(session, skill.id)
            inputs.append(
                SkillMasteryInput(
                    skill_id=str(skill.id),
                    skill_slug=skill.slug,
                    skill_name=skill.name,
                    is_foundational=skill.is_foundational,
                    sort_order=skill.sort_order,
                    score=float(mastery.score) if mastery else None,
                    confidence=float(mastery.confidence) if mastery else 0.0,
                    status=mastery.status if mastery else MasteryStatus.INSUFFICIENT,
                    problem_count=problem_count,
                )
            )
        return inputs

    def _build_prerequisites(
        self, session: Session, user_id: UUID, skill_id: UUID
    ) -> list[PrerequisiteInput]:
        skill = session.get(Skill, skill_id)
        if skill is None:
            return []
        all_skills = {item.id: item for item in self._skills.list_all(session)}
        masteries = {row.skill_id: row for row in self._mastery.list_for_user(session, user_id)}
        prereqs: list[PrerequisiteInput] = []
        for edge in skill.prerequisite_edges:
            prereq_skill = all_skills.get(edge.prerequisite_skill_id)
            if prereq_skill is None:
                continue
            mastery = masteries.get(edge.prerequisite_skill_id)
            prereqs.append(
                PrerequisiteInput(
                    prerequisite_skill_id=str(edge.prerequisite_skill_id),
                    prerequisite_slug=prereq_skill.slug,
                    prerequisite_name=prereq_skill.name,
                    score=float(mastery.score) if mastery else None,
                    status=mastery.status if mastery else MasteryStatus.INSUFFICIENT,
                )
            )
        return prereqs

    def _build_candidate_input(
        self,
        problem: Problem,
        target_skill_id: UUID,
        learner_states,
        last_success: dict,
        reference: datetime,
    ) -> CandidateProblemInput | None:
        target_link = None
        for link in problem.problem_skills:
            if link.skill_id == target_skill_id:
                target_link = link
                break
        if target_link is None:
            return None

        state = learner_states.get(
            problem.id,
            LearnerProblemStateData(attempted=False, solved=False, in_progress=False),
        )
        weight = float(target_link.weight)
        return CandidateProblemInput(
            problem_id=str(problem.id),
            problem_slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            estimated_minutes=problem.estimated_minutes,
            target_skill_weight=weight,
            is_primary_for_target=weight >= 1.0,
            attempted=state.attempted,
            solved=state.solved,
            in_progress=state.in_progress,
            last_success_at=last_success.get(problem.id),
            reference=reference,
        )

    def _batch_to_list_response(
        self, session: Session, user_id: UUID, batch: list[Recommendation]
    ) -> RecommendationListResponse:
        if not batch:
            return RecommendationListResponse(
                items=[],
                target_skill=None,
                state=STATE_NO_ELIGIBLE_PROBLEM,
                message="No recommendations yet.",
            )
        items = [self._to_item(session, rec) for rec in batch]
        target_slug = batch[0].explanation.get("target_skill")
        target_item = (
            self._target_skill_item(session, user_id, target_slug) if target_slug else None
        )
        return RecommendationListResponse(
            items=items,
            target_skill=target_item,
            state=STATE_OK,
            message=None,
        )

    def _target_skill_item(
        self, session: Session, user_id: UUID, skill_slug: str | None
    ) -> UserSkillMasteryItem | None:
        if not skill_slug:
            return None
        skill = self._skills.find_by_slug(session, skill_slug)
        if skill is None:
            return None
        mastery = self._mastery.get_for_user_skill(session, user_id, skill.id)
        topics = {topic.id: topic for topic in self._topics.list_all(session)}
        topic_slug = None
        if skill.topic_id and skill.topic_id in topics:
            topic_slug = topics[skill.topic_id].slug
        if mastery is None:
            return UserSkillMasteryItem(
                skill_slug=skill.slug,
                skill_name=skill.name,
                topic_slug=topic_slug,
                score=None,
                confidence="0.0000",
                status=MasteryStatus.INSUFFICIENT,
                evidence_count=0,
                last_attempt_at=None,
            )
        score = f"{float(mastery.score):.4f}" if mastery.status == MasteryStatus.ASSESSED else None
        return UserSkillMasteryItem(
            skill_slug=skill.slug,
            skill_name=skill.name,
            topic_slug=topic_slug,
            score=score,
            confidence=f"{float(mastery.confidence):.4f}",
            status=mastery.status,
            evidence_count=mastery.evidence_count,
            last_attempt_at=mastery.last_attempt_at,
        )

    def _target_skill_item_from_selection(self, session, user_id, target):
        return self._target_skill_item(session, user_id, target.skill_slug)

    def _to_item(self, session: Session, rec: Recommendation) -> RecommendationItem:
        problem = self._problems.find_published_by_id(session, rec.problem_id)
        if problem is None:
            raise ValueError(f"Recommended problem {rec.problem_id} not found")

        target_skill = session.get(Skill, rec.target_skill_id)
        skill_links = [
            ProblemSkillLink(
                slug=link.skill.slug,
                name=link.skill.name,
                weight=link.weight,
                is_primary=float(link.weight) >= 1.0,
            )
            for link in problem.problem_skills
        ]
        target_link = next(
            (
                link
                for link in skill_links
                if link.slug == (target_skill.slug if target_skill else "")
            ),
            skill_links[0]
            if skill_links
            else ProblemSkillLink(
                slug="unknown", name="Unknown", weight=Decimal("1.0"), is_primary=True
            ),
        )

        explanation_data = rec.explanation
        return RecommendationItem(
            id=str(rec.id),
            rank=rec.rank,
            score=f"{float(rec.score):.4f}",
            generated_at=rec.generated_at,
            source_attempt_id=str(rec.source_attempt_id) if rec.source_attempt_id else None,
            problem=RecommendationProblemSummary(
                id=str(problem.id),
                slug=problem.slug,
                title=problem.title,
                difficulty=problem.difficulty,
                estimated_minutes=problem.estimated_minutes,
                skills=skill_links,
                target_skill=target_link,
            ),
            explanation=RecommendationExplanation(
                target_skill=explanation_data.get("target_skill", ""),
                reason_codes=explanation_data.get("reason_codes", []),
                score_components=explanation_data.get("score_components", {}),
                sentences=explanation_data.get("sentences", []),
            ),
        )
