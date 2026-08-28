from uuid import UUID

from app.core.catalog_errors import NotFoundError
from app.core.enums import MasteryStatus, ReadinessDimension
from app.domain.readiness import (
    ALL_DIMENSIONS,
    SkillReadinessInput,
    TargetRequirementInput,
    compute_dimension_readiness,
    compute_placement_readiness,
    explain_placement,
)
from app.models.readiness import TargetProfile
from app.models.user import User
from app.repositories.assessment_repository import MasteryRepository
from app.repositories.readiness_repository import (
    DimensionSkillRepository,
    LearnerTargetRepository,
    TargetProfileRepository,
)
from app.repositories.skill_repository import SkillRepository
from app.schemas.readiness import (
    BlockerResponse,
    DimensionReadinessResponse,
    GapListResponse,
    LearnerTargetResponse,
    PlacementReadinessResponse,
    SkillHighlightResponse,
    TargetProfileListResponse,
    TargetProfileSummary,
)
from sqlalchemy.orm import Session


class ReadinessService:
    def __init__(
        self,
        profiles: TargetProfileRepository,
        learner_targets: LearnerTargetRepository,
        dimension_skills: DimensionSkillRepository,
        mastery: MasteryRepository,
        skills: SkillRepository,
    ) -> None:
        self._profiles = profiles
        self._learner_targets = learner_targets
        self._dimension_skills = dimension_skills
        self._mastery = mastery
        self._skills = skills

    def list_profiles(self, session: Session) -> TargetProfileListResponse:
        items = [self._profile_summary(profile) for profile in self._profiles.list_all(session)]
        return TargetProfileListResponse(items=items)

    def get_learner_target(self, session: Session, user_id: UUID) -> LearnerTargetResponse:
        row = self._learner_targets.get_for_user(session, user_id)
        if row is None:
            return LearnerTargetResponse(profile=None, selected_at=None)
        return LearnerTargetResponse(
            profile=self._profile_summary(row.profile),
            selected_at=row.selected_at,
        )

    def set_learner_target(
        self, session: Session, user: User, profile_slug: str
    ) -> LearnerTargetResponse:
        profile = self._profiles.find_by_slug(session, profile_slug)
        if profile is None:
            raise NotFoundError(detail="Target profile not found", code="target_profile_not_found")
        row = self._learner_targets.upsert(session, user.id, profile.id)
        session.refresh(row)
        loaded = self._learner_targets.get_for_user(session, user.id)
        assert loaded is not None
        return LearnerTargetResponse(
            profile=self._profile_summary(loaded.profile),
            selected_at=loaded.selected_at,
        )

    def get_readiness(self, session: Session, user_id: UUID) -> PlacementReadinessResponse:
        profile, placement = self._compute(session, user_id)
        dim_gaps = {gap.dimension: gap for gap in placement.gaps if gap.skill_slug is None}
        explanation = explain_placement(
            has_target=profile is not None,
            target_name=profile.name if profile else None,
            dimensions=placement.dimensions,
            gaps=placement.gaps,
        )
        return PlacementReadinessResponse(
            target=self._profile_summary(profile) if profile else None,
            state=placement.state,
            confidence=placement.confidence,
            risk=placement.risk,
            dimensions=[
                self._dimension_response(item, dim_gaps.get(item.key))
                for item in placement.dimensions
            ],
            blockers=[self._blocker_response(item) for item in placement.blockers],
            score=None,
            explanation=list(explanation),
        )

    def get_gaps(self, session: Session, user_id: UUID) -> GapListResponse:
        _profile, placement = self._compute(session, user_id)
        return GapListResponse(items=[self._blocker_response(item) for item in placement.gaps])

    def compute_placement(self, session: Session, user_id: UUID):
        return self._compute(session, user_id)

    def _compute(self, session: Session, user_id: UUID):
        learner_target = self._learner_targets.get_for_user(session, user_id)
        profile = learner_target.profile if learner_target else None

        skills = self._skills.list_all(session)
        masteries = {row.skill_id: row for row in self._mastery.list_for_user(session, user_id)}
        mapping = self._dimension_skills.list_all(session)
        skills_by_id = {skill.id: skill for skill in skills}

        inputs_by_slug: dict[str, SkillReadinessInput] = {}
        for skill in skills:
            mastery = masteries.get(skill.id)
            status = mastery.status if mastery else MasteryStatus.INSUFFICIENT
            assessed = status == MasteryStatus.ASSESSED
            score = float(mastery.score) if mastery is not None and assessed else None
            confidence = float(mastery.confidence) if mastery is not None else 0.0
            evidence_count = mastery.evidence_count if mastery is not None else 0
            inputs_by_slug[skill.slug] = SkillReadinessInput(
                skill_slug=skill.slug,
                skill_name=skill.name,
                status=status,
                score=score,
                confidence=confidence,
                evidence_count=evidence_count,
            )

        skills_by_dimension: dict[ReadinessDimension, list[SkillReadinessInput]] = {
            key: [] for key in ALL_DIMENSIONS
        }
        for link in mapping:
            skill = skills_by_id.get(link.skill_id)
            if skill is None:
                continue
            dimension = ReadinessDimension(link.dimension)
            skills_by_dimension[dimension].append(inputs_by_slug[skill.slug])

        requirements: list[TargetRequirementInput] = []
        critical_floors: dict[ReadinessDimension, dict[str, float]] = {
            key: {} for key in ALL_DIMENSIONS
        }
        if profile is not None:
            for row in profile.requirements:
                dimension = ReadinessDimension(row.dimension)
                skill = skills_by_id.get(row.skill_id) if row.skill_id else None
                skill_slug = skill.slug if skill else None
                if skill_slug and row.is_critical:
                    critical_floors[dimension][skill_slug] = float(row.min_score)
                requirements.append(
                    TargetRequirementInput(
                        dimension=dimension,
                        skill_slug=skill_slug,
                        skill_name=skill.name if skill else None,
                        min_score=float(row.min_score),
                        min_confidence=float(row.min_confidence),
                        weight=float(row.weight),
                        is_critical=row.is_critical,
                    )
                )

        dimension_results = [
            compute_dimension_readiness(
                key,
                skills_by_dimension[key],
                critical_floors=critical_floors[key],
            )
            for key in ALL_DIMENSIONS
        ]
        placement = compute_placement_readiness(
            has_target=profile is not None,
            dimensions=dimension_results,
            requirements=requirements,
            skills_by_slug=inputs_by_slug,
        )
        return profile, placement

    def _profile_summary(self, profile: TargetProfile) -> TargetProfileSummary:
        return TargetProfileSummary(
            slug=profile.slug,
            name=profile.name,
            description=profile.description,
        )

    def _dimension_response(self, item, gap=None) -> DimensionReadinessResponse:
        extra_skills = item.key in {ReadinessDimension.DSA, ReadinessDimension.CORE_CS}
        return DimensionReadinessResponse(
            key=item.key,
            display_name=item.display_name,
            status=item.status,
            score=item.score,
            confidence=item.confidence,
            coverage=item.coverage,
            assessed_count=item.assessed_count,
            in_scope_count=item.in_scope_count,
            strongest_skills=(
                [
                    SkillHighlightResponse(
                        skill_slug=row.skill_slug,
                        skill_name=row.skill_name,
                        score=row.score,
                    )
                    for row in item.strongest_skills
                ]
                if extra_skills
                else []
            ),
            weakest_actionable_skill=(
                SkillHighlightResponse(
                    skill_slug=item.weakest_actionable_skill.skill_slug,
                    skill_name=item.weakest_actionable_skill.skill_name,
                    score=item.weakest_actionable_skill.score,
                )
                if extra_skills and item.weakest_actionable_skill
                else None
            ),
            target_min_score=gap.required if gap is not None else None,
            requirement_status=gap.status if gap is not None else None,
        )

    def _blocker_response(self, item) -> BlockerResponse:
        return BlockerResponse(
            dimension=item.dimension,
            skill_slug=item.skill_slug,
            skill_name=item.skill_name,
            current=item.current,
            required=item.required,
            delta=item.delta,
            status=item.status,
            severity=item.severity,
            why=item.why,
            rank=item.rank,
            is_critical=item.is_critical,
        )
