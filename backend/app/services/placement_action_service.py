from datetime import UTC, datetime
from uuid import UUID

from app.core.enums import ActivityKind, MasteryStatus, PlacementActionKind, ReadinessDimension
from app.domain.placement_actions import (
    PlacementActionCandidate,
    attach_problem,
    batch_fingerprint,
    generate_candidates,
    score_and_rank,
)
from app.domain.readiness import DIMENSION_DISPLAY_NAMES
from app.domain.recommendation import (
    CandidateProblemInput,
    PrerequisiteInput,
    TargetSkillSelection,
    evaluate_prerequisite_readiness,
    score_candidate,
)
from app.models.placement_action import PlacementAction
from app.models.problem import Problem
from app.models.skill import Skill
from app.repositories.assessment_repository import MasteryRepository
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.placement_action_repository import PlacementActionRepository
from app.repositories.problem_repository import LearnerProblemStateData, ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.schemas.placement_action import (
    NextPlacementActionResponse,
    PlacementActionItem,
    PlacementActionListResponse,
    PlacementActionSkill,
)
from app.services.readiness_service import ReadinessService
from app.services.recommendation_service import RecommendationService
from sqlalchemy.orm import Session

STATE_OK = "ok"
STATE_NO_TARGET = "no_target"
STATE_NO_ACTION = "no_eligible_action"

NO_TARGET_MESSAGE = "Choose a target profile to evaluate placement actions."
NO_ACTION_MESSAGE = "No eligible placement action for the current target and evidence."


class PlacementActionService:
    def __init__(
        self,
        actions: PlacementActionRepository,
        readiness: ReadinessService,
        recommendations: RecommendationService,
        mastery: MasteryRepository,
        skills: SkillRepository,
        problems: ProblemRepository,
        attempts: AttemptRepository,
    ) -> None:
        self._actions = actions
        self._readiness = readiness
        self._recommendations = recommendations
        self._mastery = mastery
        self._skills = skills
        self._problems = problems
        self._attempts = attempts

    def get_next(
        self,
        session: Session,
        user_id: UUID,
        *,
        refresh: bool = False,
        commit: bool = True,
    ) -> NextPlacementActionResponse:
        listing = self.get_actions(session, user_id, limit=1, refresh=refresh, commit=commit)
        action = listing.items[0] if listing.items else None
        return NextPlacementActionResponse(
            action=action,
            state=listing.state,
            message=listing.message,
        )

    def get_actions(
        self,
        session: Session,
        user_id: UUID,
        *,
        limit: int = 5,
        dimension: str | None = None,
        refresh: bool = False,
        commit: bool = True,
        source_attempt_id: UUID | None = None,
    ) -> PlacementActionListResponse:
        batch = self._ensure_batch(
            session,
            user_id,
            refresh=refresh,
            commit=commit,
            source_attempt_id=source_attempt_id,
        )
        if isinstance(batch, PlacementActionListResponse):
            return batch
        items = [self._to_item(row) for row in batch]
        if dimension:
            items = [item for item in items if item.target_dimension.value == dimension]
        return PlacementActionListResponse(
            items=items[:limit],
            state=STATE_OK if items else STATE_NO_ACTION,
            message=None if items else NO_ACTION_MESSAGE,
        )

    def get_detail(
        self, session: Session, user_id: UUID, action_id: UUID
    ) -> PlacementActionItem | None:
        row = self._actions.find_by_id_for_user(session, user_id, action_id)
        if row is None:
            return None
        return self._to_item(row)

    def refresh_after_submission(self, session: Session, user_id: UUID, attempt_id: UUID) -> None:
        if self._actions.exists_for_attempt(session, user_id, attempt_id):
            return
        self._ensure_batch(
            session,
            user_id,
            refresh=True,
            commit=False,
            source_attempt_id=attempt_id,
        )

    def _ensure_batch(
        self,
        session: Session,
        user_id: UUID,
        *,
        refresh: bool,
        commit: bool,
        source_attempt_id: UUID | None,
    ) -> list[PlacementAction] | PlacementActionListResponse:
        profile, placement = self._readiness.compute_placement(session, user_id)
        if profile is None:
            return PlacementActionListResponse(
                items=[],
                state=STATE_NO_TARGET,
                message=NO_TARGET_MESSAGE,
            )

        ranked = self._build_ranked(session, user_id, placement, profile.name)
        if not ranked:
            return PlacementActionListResponse(
                items=[],
                state=STATE_NO_ACTION,
                message=NO_ACTION_MESSAGE,
            )

        fingerprint = batch_fingerprint(ranked)
        latest = self._actions.list_latest_batch(session, user_id, limit=20)
        stale = self._is_stale(session, user_id, latest)
        if latest and not stale:
            existing_fp = latest[0].payload.get("batch_fingerprint")
            if existing_fp == fingerprint and (not refresh or source_attempt_id is None):
                return latest
            if existing_fp == fingerprint and source_attempt_id is not None:
                if self._actions.exists_for_attempt(session, user_id, source_attempt_id):
                    return latest

        generated_at = datetime.now(UTC)
        persisted: list[PlacementAction] = []
        for item in ranked:
            candidate = item.candidate
            skill_id = None
            if candidate.target_skill_slug:
                skill = self._skills.find_by_slug(session, candidate.target_skill_slug)
                skill_id = skill.id if skill else None
            problem_id = UUID(candidate.problem_id) if candidate.problem_id else None
            payload = {
                "batch_fingerprint": fingerprint,
                "dimension": candidate.target_dimension.value,
                "estimated_effort_minutes": candidate.estimated_effort_minutes,
            }
            if candidate.problem_slug:
                payload["problem_id"] = candidate.problem_id
                payload["problem_slug"] = candidate.problem_slug
            if candidate.action_kind == PlacementActionKind.ASSESS_DIMENSION:
                payload["dimension"] = candidate.target_dimension.value
            explanation = {
                "reason_codes": list(item.reason_codes),
                "sentences": list(item.explanation),
                "description": candidate.description,
            }
            row = self._actions.create(
                session,
                user_id=user_id,
                action_kind=candidate.action_kind.value,
                target_dimension=candidate.target_dimension.value,
                target_skill_id=skill_id,
                problem_id=problem_id,
                rank=item.rank,
                score=item.score,
                title=candidate.title,
                explanation=explanation,
                payload=payload,
                generated_at=generated_at,
                source_attempt_id=source_attempt_id,
            )
            persisted.append(row)
        if commit:
            session.commit()
            persisted = self._actions.list_latest_batch(session, user_id, limit=20)
        return persisted

    def _build_ranked(self, session: Session, user_id: UUID, placement, target_name: str):
        slots = generate_candidates(placement, target_name=target_name)
        filled: list[PlacementActionCandidate] = []
        reference = datetime.now(UTC)
        for slot in slots:
            filled_one = self._fill_slot(session, user_id, slot, reference)
            if filled_one is not None:
                filled.append(filled_one)
        return score_and_rank(filled)

    def _fill_slot(
        self,
        session: Session,
        user_id: UUID,
        slot: PlacementActionCandidate,
        reference: datetime,
    ) -> PlacementActionCandidate | None:
        if slot.action_kind == PlacementActionKind.ASSESS_DIMENSION:
            return slot
        if slot.action_kind == PlacementActionKind.DSA_PROBLEM:
            rec = self._recommendations.get_next(
                session,
                user_id,
                target_skill_slug=slot.target_skill_slug,
                refresh=False,
            )
            if rec.recommendation is None:
                rec = self._recommendations.get_next(session, user_id, refresh=False)
            if rec.recommendation is None:
                return None
            problem = rec.recommendation.problem
            return attach_problem(
                slot,
                problem_id=problem.id,
                problem_slug=problem.slug,
                problem_title=problem.title,
                estimated_effort_minutes=problem.estimated_minutes,
            )
        return self._fill_quiz(session, user_id, slot, reference)

    def _fill_quiz(
        self,
        session: Session,
        user_id: UUID,
        slot: PlacementActionCandidate,
        reference: datetime,
    ) -> PlacementActionCandidate | None:
        slugs: list[str] = []
        if slot.target_skill_slug:
            slugs.append(slot.target_skill_slug)
        for slug in slugs:
            picked = self._pick_quiz_for_skill(session, user_id, slug, reference)
            if picked is not None:
                problem, prereq = picked
                updated = attach_problem(
                    slot,
                    problem_id=str(problem.id),
                    problem_slug=problem.slug,
                    problem_title=problem.title,
                    estimated_effort_minutes=problem.estimated_minutes,
                )
                return PlacementActionCandidate(
                    **{**updated.__dict__, "prerequisite_ready": prereq}
                )
        return PlacementActionCandidate(
            **{
                **slot.__dict__,
                "action_kind": PlacementActionKind.ASSESS_DIMENSION,
                "title": f"Assess {DIMENSION_DISPLAY_NAMES[slot.target_dimension]}",
                "stable_key": (
                    f"{PlacementActionKind.ASSESS_DIMENSION.value}:"
                    f"{slot.target_dimension.value}:-:-"
                ),
                "problem_id": None,
                "problem_slug": None,
                "problem_title": None,
            }
        )

    def _pick_quiz_for_skill(
        self,
        session: Session,
        user_id: UUID,
        skill_slug: str,
        reference: datetime,
    ) -> tuple[Problem, float] | None:
        skill = self._skills.find_by_slug(session, skill_slug)
        if skill is None:
            return None
        mastery = self._mastery.get_for_user_skill(session, user_id, skill.id)
        target = TargetSkillSelection(
            skill_id=str(skill.id),
            skill_slug=skill.slug,
            skill_name=skill.name,
            score=float(mastery.score)
            if mastery and mastery.status == MasteryStatus.ASSESSED
            else None,
            confidence=float(mastery.confidence) if mastery else 0.0,
            status=mastery.status if mastery else MasteryStatus.INSUFFICIENT,
            selection_reason="cs_weak_skill",
        )
        prereqs = self._prerequisites(session, user_id, skill.id)
        readiness, eligible, _ = evaluate_prerequisite_readiness(prereqs)
        if not eligible:
            return None
        problems = [
            problem
            for problem in self._skills.find_linked_published_problems(session, skill.id)
            if problem.activity_kind == ActivityKind.QUIZ
        ]
        if not problems:
            return None
        problem_ids = [problem.id for problem in problems]
        learner_states = self._problems.get_learner_states(session, user_id, problem_ids)
        last_success = self._attempts.get_last_success_times(session, user_id, problem_ids)
        scored = []
        for problem in problems:
            candidate = self._quiz_candidate_input(
                problem, skill.id, learner_states, last_success, reference
            )
            if candidate is None:
                continue
            result = score_candidate(candidate, target, readiness, eligible)
            if result is not None:
                scored.append((result, problem))
        if not scored:
            return None
        scored.sort(key=lambda pair: (-pair[0].components.final_score, pair[0].problem_slug))
        return scored[0][1], readiness

    def _quiz_candidate_input(
        self,
        problem: Problem,
        target_skill_id: UUID,
        learner_states,
        last_success: dict,
        reference: datetime,
    ) -> CandidateProblemInput | None:
        target_link = next(
            (link for link in problem.problem_skills if link.skill_id == target_skill_id),
            None,
        )
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

    def _prerequisites(
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

    def _is_stale(self, session: Session, user_id: UUID, latest: list[PlacementAction]) -> bool:
        if not latest:
            return True
        generated = latest[0].generated_at
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        version = self._state_version(session, user_id)
        if version is None:
            return False
        if version.tzinfo is None:
            version = version.replace(tzinfo=UTC)
        return generated < version

    def _state_version(self, session: Session, user_id: UUID) -> datetime | None:
        times: list[datetime] = []
        for row in self._mastery.list_for_user(session, user_id):
            if row.updated_at is not None:
                times.append(row.updated_at)
        target = self._readiness.get_learner_target(session, user_id)
        if target.selected_at is not None:
            times.append(target.selected_at)
        return max(times) if times else None

    def _to_item(self, row: PlacementAction) -> PlacementActionItem:
        explanation = row.explanation or {}
        payload = dict(row.payload or {})
        payload.pop("batch_fingerprint", None)
        skill = None
        if row.target_skill is not None:
            skill = PlacementActionSkill(slug=row.target_skill.slug, name=row.target_skill.name)
        return PlacementActionItem(
            id=str(row.id),
            action_kind=PlacementActionKind(row.action_kind),
            title=row.title,
            description=explanation.get("description", ""),
            target_dimension=ReadinessDimension(row.target_dimension),
            target_skill=skill,
            estimated_effort_minutes=int(
                payload.get("estimated_effort_minutes")
                or (row.problem.estimated_minutes if row.problem else 20)
            ),
            score=f"{float(row.score):.4f}",
            rank=row.rank,
            why=list(explanation.get("sentences", [])),
            reason_codes=list(explanation.get("reason_codes", [])),
            payload=payload,
            generated_at=row.generated_at,
        )
