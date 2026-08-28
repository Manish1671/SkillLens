from datetime import UTC, datetime
from uuid import UUID

from app.models.readiness import DimensionSkill, LearnerTarget, TargetProfile
from app.models.skill import Skill
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


class TargetProfileRepository:
    def list_all(self, session: Session) -> list[TargetProfile]:
        return list(
            session.scalars(
                select(TargetProfile)
                .options(selectinload(TargetProfile.requirements))
                .order_by(TargetProfile.sort_order, TargetProfile.slug)
            ).all()
        )

    def find_by_slug(self, session: Session, slug: str) -> TargetProfile | None:
        return session.scalar(
            select(TargetProfile)
            .where(TargetProfile.slug == slug)
            .options(selectinload(TargetProfile.requirements))
        )


class LearnerTargetRepository:
    def get_for_user(self, session: Session, user_id: UUID) -> LearnerTarget | None:
        return session.scalar(
            select(LearnerTarget)
            .where(LearnerTarget.user_id == user_id)
            .options(selectinload(LearnerTarget.profile).selectinload(TargetProfile.requirements))
        )

    def upsert(self, session: Session, user_id: UUID, profile_id: UUID) -> LearnerTarget:
        existing = self.get_for_user(session, user_id)
        now = datetime.now(UTC)
        if existing is None:
            existing = LearnerTarget(user_id=user_id, profile_id=profile_id, selected_at=now)
            session.add(existing)
        else:
            existing.profile_id = profile_id
            existing.selected_at = now
        session.flush()
        session.refresh(existing)
        return existing


class DimensionSkillRepository:
    def list_all(self, session: Session) -> list[DimensionSkill]:
        return list(
            session.scalars(
                select(DimensionSkill).options(selectinload(DimensionSkill.skill))
            ).all()
        )

    def skills_for_dimension(self, session: Session, dimension: str) -> list[Skill]:
        return list(
            session.scalars(
                select(Skill)
                .join(DimensionSkill, DimensionSkill.skill_id == Skill.id)
                .where(DimensionSkill.dimension == dimension)
                .order_by(Skill.sort_order, Skill.slug)
            ).all()
        )
