from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from app.core.enums import EvidencePolarity, MasteryStatus
from app.domain.evidence import (
    ProblemSkillInput,
    RecentFailureRecord,
    SubmissionContext,
    generate_evidence_drafts,
)
from app.domain.mastery import EvidenceInput, compute_mastery
from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.user import User
from app.repositories.assessment_repository import (
    EvidenceRepository,
    MasteryRepository,
    SnapshotRepository,
)
from app.repositories.problem_repository import ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.assessment import (
    EvidenceSummary,
    EvidenceTimelineItem,
    SkillMasteryDelta,
    SnapshotItem,
    SubmitAssessmentOutcome,
    UserMasteryResponse,
    UserSkillDetailResponse,
)
from app.schemas.mastery_items import UserSkillMasteryItem
from app.schemas.recommendation import NextRecommendationResponse
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.recommendation_service import RecommendationService


class AssessmentService:
    def __init__(
        self,
        evidence_repository: EvidenceRepository,
        mastery_repository: MasteryRepository,
        snapshot_repository: SnapshotRepository,
        skill_repository: SkillRepository,
        problem_repository: ProblemRepository,
        topic_repository: TopicRepository,
        recommendation_service: "RecommendationService | None" = None,
    ) -> None:
        self._evidence = evidence_repository
        self._mastery = mastery_repository
        self._snapshots = snapshot_repository
        self._skills = skill_repository
        self._problems = problem_repository
        self._topics = topic_repository
        self._recommendations = recommendation_service

    def process_submission(
        self,
        session: Session,
        user: User,
        attempt: Attempt,
        problem: Problem,
    ) -> SubmitAssessmentOutcome:
        if self._evidence.exists_for_attempt(session, attempt.id):
            recommendation = None
            if self._recommendations is not None:
                recommendation = self._recommendations.get_next(session, user.id)
            return SubmitAssessmentOutcome(
                evidence_items=[], mastery_deltas=[], recommendation=recommendation
            )

        reference = attempt.submitted_at or datetime.now(UTC)
        problem_skills = self._build_problem_skill_inputs(problem)
        skill_ids = [UUID(link.skill_id) for link in problem_skills]

        recent_items = self._evidence.recent_failure_records(session, user.id, skill_ids)
        recent_failures = [
            RecentFailureRecord(
                skill_id=str(item.skill_id),
                problem_id=str(item.details.get("problem_id", "")),
                evidence_type=item.evidence_type,
            )
            for item in recent_items
        ]

        submission = SubmissionContext(
            problem_id=str(problem.id),
            problem_slug=problem.slug,
            problem_title=problem.title,
            difficulty=problem.difficulty,
            is_correct=bool(attempt.is_correct),
            hints_used_count=attempt.hints_used_count,
            mistake_type=attempt.mistake_type,
            time_spent_seconds=attempt.time_spent_seconds,
        )

        drafts = generate_evidence_drafts(submission, problem_skills, recent_failures)
        skills_by_id = {skill.id: skill for skill in self._skills.list_all(session)}

        created_summaries: list[EvidenceSummary] = []
        for draft in drafts:
            item = self._evidence.create(
                session,
                user_id=user.id,
                skill_id=UUID(draft.skill_id),
                attempt_id=attempt.id,
                evidence_type=draft.evidence_type,
                polarity=draft.polarity,
                strength=draft.strength,
                summary_text=draft.summary_text,
                details=draft.details,
            )
            skill = skills_by_id.get(UUID(draft.skill_id))
            created_summaries.append(
                EvidenceSummary(
                    id=str(item.id),
                    evidence_type=item.evidence_type,
                    polarity=item.polarity,
                    strength=str(item.strength),
                    summary_text=item.summary_text,
                    skill_slug=skill.slug if skill else draft.skill_id,
                    skill_name=skill.name if skill else draft.skill_id,
                    created_at=item.created_at,
                )
            )

        affected_skill_ids = {UUID(link.skill_id) for link in problem_skills}
        deltas = self._update_mastery_for_skills(
            session,
            user.id,
            attempt.id,
            affected_skill_ids,
            reference,
            skills_by_id,
        )

        recommendation: NextRecommendationResponse | None = None
        if self._recommendations is not None:
            recommendation = self._recommendations.generate_for_submission(
                session, user, attempt.id
            )

        return SubmitAssessmentOutcome(
            evidence_items=created_summaries,
            mastery_deltas=deltas,
            recommendation=recommendation,
        )

    def _update_mastery_for_skills(
        self,
        session: Session,
        user_id: UUID,
        attempt_id: UUID,
        skill_ids: set[UUID],
        reference: datetime,
        skills_by_id: dict[UUID, object],
    ) -> list[SkillMasteryDelta]:
        deltas: list[SkillMasteryDelta] = []

        for skill_id in skill_ids:
            skill = skills_by_id.get(skill_id)
            if skill is None:
                continue

            previous = self._mastery.get_for_user_skill(session, user_id, skill_id)
            previous_score = float(previous.score) if previous else None

            evidence_rows = self._evidence.list_for_user_skill(session, user_id, skill_id)
            evidence_inputs = self._to_evidence_inputs(evidence_rows)

            prereq_pairs = self._mastery.get_prerequisite_scores(session, user_id, skill_id)
            prereq_scores = [score for _, score in prereq_pairs]

            result = compute_mastery(evidence_inputs, reference, prereq_scores)

            if result.prerequisite_capped:
                weak_prereq = min(prereq_scores)
                weak_name = "prerequisite"
                for prereq_id, score in prereq_pairs:
                    if score == weak_prereq:
                        prereq_skill = skills_by_id.get(prereq_id)
                        if prereq_skill:
                            weak_name = prereq_skill.name
                        break
                block_item = self._evidence.create(
                    session,
                    user_id=user_id,
                    skill_id=skill_id,
                    attempt_id=attempt_id,
                    evidence_type="prerequisite_block",
                    polarity=EvidencePolarity.NEUTRAL,
                    strength=0.4,
                    summary_text=(
                        f"Mastery for {skill.name} capped because prerequisite "
                        f"{weak_name} is weak (score {weak_prereq:.2f})."
                    ),
                    details={"prerequisite_score": weak_prereq},
                )
                evidence_inputs.append(
                    EvidenceInput(
                        polarity=block_item.polarity,
                        strength=float(block_item.strength),
                        created_at=block_item.created_at,
                        evidence_type=block_item.evidence_type,
                    )
                )
                result = compute_mastery(evidence_inputs, reference, prereq_scores)

            display_score = result.score if result.status == MasteryStatus.ASSESSED else None
            score_decimal = Decimal(str(result.score))
            confidence_decimal = Decimal(str(result.confidence))

            final_evidence_count = len(
                self._evidence.list_for_user_skill(session, user_id, skill_id)
            )

            self._mastery.upsert(
                session,
                user_id=user_id,
                skill_id=skill_id,
                score=score_decimal,
                confidence=confidence_decimal,
                evidence_count=final_evidence_count,
                last_attempt_at=reference,
                status=result.status,
            )

            self._snapshots.create(
                session,
                user_id=user_id,
                skill_id=skill_id,
                attempt_id=attempt_id,
                score=score_decimal,
                confidence=confidence_decimal,
                computed_at=reference,
            )

            delta_value = None
            if previous_score is not None and display_score is not None:
                delta_value = round(display_score - previous_score, 4)
            elif display_score is not None and previous_score is None:
                delta_value = display_score

            deltas.append(
                SkillMasteryDelta(
                    skill_slug=skill.slug,
                    skill_name=skill.name,
                    previous_score=f"{previous_score:.4f}" if previous_score is not None else None,
                    new_score=f"{display_score:.4f}" if display_score is not None else None,
                    delta=f"{delta_value:.4f}" if delta_value is not None else None,
                    status=result.status,
                    confidence=f"{result.confidence:.4f}",
                    prerequisite_capped=result.prerequisite_capped,
                )
            )

        return deltas

    def get_user_mastery(self, session: Session, user_id: UUID) -> UserMasteryResponse:
        masteries = self._mastery.list_for_user(session, user_id)
        skills = {skill.id: skill for skill in self._skills.list_all(session)}
        topics = {topic.id: topic for topic in self._topics.list_all(session)}

        items: list[UserSkillMasteryItem] = []
        for mastery in masteries:
            skill = skills.get(mastery.skill_id)
            if skill is None:
                continue
            topic_slug = None
            if skill.topic_id and skill.topic_id in topics:
                topic_slug = topics[skill.topic_id].slug
            score = (
                f"{float(mastery.score):.4f}" if mastery.status == MasteryStatus.ASSESSED else None
            )
            items.append(
                UserSkillMasteryItem(
                    skill_slug=skill.slug,
                    skill_name=skill.name,
                    topic_slug=topic_slug,
                    score=score,
                    confidence=f"{float(mastery.confidence):.4f}",
                    status=mastery.status,
                    evidence_count=mastery.evidence_count,
                    last_attempt_at=mastery.last_attempt_at,
                )
            )
        items.sort(key=lambda item: item.skill_name)
        return UserMasteryResponse(items=items)

    def get_user_skill_detail(
        self, session: Session, user_id: UUID, slug: str
    ) -> UserSkillDetailResponse | None:
        skill = self._skills.find_by_slug(session, slug)
        if skill is None:
            return None

        mastery = self._mastery.get_for_user_skill(session, user_id, skill.id)
        evidence_rows = self._evidence.list_for_user_skill_recent(session, user_id, skill.id, 30)
        snapshots = self._snapshots.list_for_user_skill(session, user_id, skill.id, 15)

        all_skills = self._skills.list_all(session)
        skills_by_id = {item.id: item for item in all_skills}
        topic_by_id = {topic.id: topic for topic in self._topics.list_all(session)}

        prerequisites = [
            item
            for edge in skill.prerequisite_edges
            if (
                item := self._mastery_item_for(
                    session, user_id, edge.prerequisite_skill_id, skills_by_id, topic_by_id
                )
            )
            is not None
        ]
        dependents = [
            item
            for edge in skill.dependent_edges
            if (
                item := self._mastery_item_for(
                    session, user_id, edge.skill_id, skills_by_id, topic_by_id
                )
            )
            is not None
        ]

        score = None
        confidence = "0.0000"
        status = MasteryStatus.INSUFFICIENT
        evidence_count = 0
        last_attempt_at = None
        if mastery is not None:
            confidence = f"{float(mastery.confidence):.4f}"
            status = mastery.status
            evidence_count = mastery.evidence_count
            last_attempt_at = mastery.last_attempt_at
            if mastery.status == MasteryStatus.ASSESSED:
                score = f"{float(mastery.score):.4f}"

        topic_slug = None
        if skill.topic_id and skill.topic_id in topic_by_id:
            topic_slug = topic_by_id[skill.topic_id].slug

        return UserSkillDetailResponse(
            slug=skill.slug,
            name=skill.name,
            description=skill.description,
            topic_slug=topic_slug,
            score=score,
            confidence=confidence,
            status=status,
            evidence_count=evidence_count,
            last_attempt_at=last_attempt_at,
            prerequisites=prerequisites,
            dependents=dependents,
            evidence_timeline=[
                EvidenceTimelineItem(
                    id=str(row.id),
                    evidence_type=row.evidence_type,
                    polarity=row.polarity,
                    strength=str(row.strength),
                    summary_text=row.summary_text,
                    created_at=row.created_at,
                    attempt_id=str(row.attempt_id),
                    details=row.details,
                )
                for row in evidence_rows
            ],
            snapshots=[
                SnapshotItem(
                    score=f"{float(row.score):.4f}",
                    confidence=f"{float(row.confidence):.4f}",
                    computed_at=row.computed_at,
                    attempt_id=str(row.attempt_id),
                )
                for row in snapshots
            ],
        )

    def _mastery_item_for(
        self,
        session: Session,
        user_id: UUID,
        skill_id: UUID,
        skills_by_id: dict,
        topic_by_id: dict,
    ) -> UserSkillMasteryItem | None:
        linked = skills_by_id.get(skill_id)
        if linked is None:
            return None
        row = self._mastery.get_for_user_skill(session, user_id, skill_id)
        topic_slug = None
        if linked.topic_id and linked.topic_id in topic_by_id:
            topic_slug = topic_by_id[linked.topic_id].slug
        if row is None:
            return UserSkillMasteryItem(
                skill_slug=linked.slug,
                skill_name=linked.name,
                topic_slug=topic_slug,
                score=None,
                confidence="0.0000",
                status=MasteryStatus.INSUFFICIENT,
                evidence_count=0,
                last_attempt_at=None,
            )
        score = f"{float(row.score):.4f}" if row.status == MasteryStatus.ASSESSED else None
        return UserSkillMasteryItem(
            skill_slug=linked.slug,
            skill_name=linked.name,
            topic_slug=topic_slug,
            score=score,
            confidence=f"{float(row.confidence):.4f}",
            status=row.status,
            evidence_count=row.evidence_count,
            last_attempt_at=row.last_attempt_at,
        )

    def _build_problem_skill_inputs(self, problem: Problem) -> list[ProblemSkillInput]:
        links: list[ProblemSkillInput] = []
        for link in problem.problem_skills:
            links.append(
                ProblemSkillInput(
                    skill_id=str(link.skill_id),
                    skill_slug=link.skill.slug,
                    skill_name=link.skill.name,
                    weight=float(link.weight),
                    is_primary=float(link.weight) >= 1.0,
                )
            )
        return links

    def _to_evidence_inputs(self, evidence_rows: list) -> list[EvidenceInput]:
        return [
            EvidenceInput(
                polarity=row.polarity,
                strength=float(row.strength),
                created_at=row.created_at,
                evidence_type=row.evidence_type,
            )
            for row in evidence_rows
        ]
