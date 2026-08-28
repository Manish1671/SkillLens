from uuid import UUID

from app.core.enums import MasteryStatus, ReadinessDimension
from app.domain.assessment_plan import (
    PlanDimensionInput,
    PlanProblemInput,
    PlanSkillInput,
    PlanTargetInput,
    build_assessment_plan,
)
from app.domain.readiness import DimensionReadinessResult
from app.models.problem import Problem
from app.repositories.assessment_repository import MasteryRepository
from app.repositories.problem_repository import LearnerProblemStateData, ProblemRepository
from app.repositories.readiness_repository import DimensionSkillRepository
from app.repositories.skill_repository import SkillRepository
from app.schemas.assessment_plan import (
    AssessmentPlanItemResponse,
    AssessmentPlanResponse,
    AssessmentPlanTarget,
)
from app.services.readiness_service import ReadinessService
from sqlalchemy.orm import Session

STATE_OK = "ok"
STATE_NO_TARGET = "no_target"
NO_TARGET_MESSAGE = "Choose a target before assessing readiness."


class AssessmentPlanService:
    def __init__(
        self,
        readiness: ReadinessService,
        skills: SkillRepository,
        problems: ProblemRepository,
        mastery: MasteryRepository,
        dimension_skills: DimensionSkillRepository,
    ) -> None:
        self._readiness = readiness
        self._skills = skills
        self._problems = problems
        self._mastery = mastery
        self._dimension_skills = dimension_skills

    def get_plan(
        self,
        session: Session,
        user_id: UUID,
        *,
        dimension: str | None = None,
    ) -> AssessmentPlanResponse:
        profile, placement = self._readiness.compute_placement(session, user_id)
        if profile is None:
            return AssessmentPlanResponse(
                assessment_id=None,
                state=STATE_NO_TARGET,
                message=NO_TARGET_MESSAGE,
                target=None,
                total_items=0,
                items=[],
            )

        bias = None
        if dimension in {ReadinessDimension.DSA.value, ReadinessDimension.CORE_CS.value}:
            bias = ReadinessDimension(dimension)

        dsa_weight = 0.0
        cs_weight = 0.0
        for row in profile.requirements:
            if row.skill_id:
                continue
            if row.dimension == ReadinessDimension.DSA.value:
                dsa_weight = float(row.weight)
            elif row.dimension == ReadinessDimension.CORE_CS.value:
                cs_weight = float(row.weight)

        target = PlanTargetInput(
            slug=profile.slug,
            name=profile.name,
            dsa_weight=dsa_weight,
            core_cs_weight=cs_weight,
        )
        skill_inputs, problems = self._load_catalog(session, user_id)
        dim_inputs = [_to_dimension_input(item) for item in placement.dimensions]
        plan = build_assessment_plan(
            user_id=str(user_id),
            target=target,
            skills=skill_inputs,
            problems=problems,
            dimensions=dim_inputs,
            bias_dimension=bias,
        )
        return AssessmentPlanResponse(
            assessment_id=plan.assessment_id,
            state=STATE_OK,
            message=None,
            target=AssessmentPlanTarget(slug=plan.target_slug, name=plan.target_name),
            total_items=plan.total_items,
            items=[
                AssessmentPlanItemResponse(
                    position=item.position,
                    activity_kind=item.activity_kind,
                    problem_slug=item.problem_slug,
                    problem_title=item.problem_title,
                    dimension=item.dimension,
                    skill_slug=item.skill_slug,
                    skill_name=item.skill_name,
                    estimated_minutes=item.estimated_minutes,
                    difficulty=item.difficulty,
                )
                for item in plan.items
            ],
        )

    def _load_catalog(
        self, session: Session, user_id: UUID
    ) -> tuple[list[PlanSkillInput], list[PlanProblemInput]]:
        mapping = self._dimension_skills.list_all(session)
        all_skills = {skill.id: skill for skill in self._skills.list_all(session)}
        masteries = {row.skill_id: row for row in self._mastery.list_for_user(session, user_id)}
        slug_by_id = {skill.id: skill.slug for skill in all_skills.values()}

        dimension_by_skill: dict[UUID, ReadinessDimension] = {}
        for link in mapping:
            if link.skill_id in all_skills and link.dimension in {
                ReadinessDimension.DSA.value,
                ReadinessDimension.CORE_CS.value,
            }:
                dimension_by_skill[link.skill_id] = ReadinessDimension(link.dimension)

        skill_inputs: list[PlanSkillInput] = []
        problem_models: list[Problem] = []
        seen_problem_ids: set[UUID] = set()

        ordered_ids = sorted(
            dimension_by_skill.items(),
            key=lambda pair: (
                pair[1].value,
                all_skills[pair[0]].sort_order,
                all_skills[pair[0]].slug,
            ),
        )
        for skill_id, dimension in ordered_ids:
            skill = all_skills[skill_id]
            mastery = masteries.get(skill.id)
            prereq_slugs = tuple(
                sorted(
                    slug_by_id[edge.prerequisite_skill_id]
                    for edge in skill.prerequisite_edges
                    if edge.prerequisite_skill_id in slug_by_id
                )
            )
            assessed = mastery is not None
            skill_inputs.append(
                PlanSkillInput(
                    slug=skill.slug,
                    name=skill.name,
                    dimension=dimension,
                    is_foundational=skill.is_foundational,
                    sort_order=skill.sort_order,
                    prerequisite_slugs=prereq_slugs,
                    score=float(mastery.score) if assessed else None,
                    confidence=float(mastery.confidence) if assessed else 0.0,
                    status=mastery.status if assessed else MasteryStatus.INSUFFICIENT,
                    evidence_count=mastery.evidence_count if assessed else 0,
                )
            )
            for problem in self._skills.find_linked_published_problems(session, skill.id):
                if problem.id in seen_problem_ids:
                    continue
                seen_problem_ids.add(problem.id)
                problem_models.append(problem)

        states = self._problems.get_learner_states(
            session, user_id, [problem.id for problem in problem_models]
        )
        problems = [
            _to_problem_input(problem, states.get(problem.id), slug_by_id)
            for problem in problem_models
        ]
        return skill_inputs, problems


def _to_dimension_input(item: DimensionReadinessResult) -> PlanDimensionInput:
    return PlanDimensionInput(
        key=item.key,
        status=item.status,
        score=item.score,
        coverage=item.coverage,
        assessed_count=item.assessed_count,
    )


def _to_problem_input(
    problem: Problem,
    state: LearnerProblemStateData | None,
    slug_by_id: dict[UUID, str],
) -> PlanProblemInput:
    weights: list[tuple[str, float]] = []
    slugs: list[str] = []
    primary: str | None = None
    for link in problem.problem_skills:
        slug = slug_by_id.get(link.skill_id)
        if slug is None and link.skill is not None:
            slug = link.skill.slug
        if not slug:
            continue
        slugs.append(slug)
        weights.append((slug, float(link.weight)))
        if float(link.weight) >= 1.0:
            primary = slug
    if primary is None and slugs:
        primary = slugs[0]
    return PlanProblemInput(
        problem_id=str(problem.id),
        slug=problem.slug,
        title=problem.title,
        activity_kind=problem.activity_kind,
        difficulty=problem.difficulty,
        estimated_minutes=problem.estimated_minutes,
        skill_slugs=tuple(slugs),
        primary_skill_slug=primary,
        skill_weights=tuple(weights),
        is_published=bool(problem.is_published),
        attempted=bool(state.attempted) if state else False,
        solved=bool(state.solved) if state else False,
        in_progress=bool(state.in_progress) if state else False,
    )
