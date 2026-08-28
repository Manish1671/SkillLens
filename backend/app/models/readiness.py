import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.skill import Skill
    from app.models.user import User

DIMENSION_VALUES = ("dsa", "core_cs", "projects", "interview", "profile")
_DIMENSION_SQL = ", ".join(f"'{value}'" for value in DIMENSION_VALUES)


class TargetProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "target_profiles"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    requirements: Mapped[list["TargetRequirement"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    learner_targets: Mapped[list["LearnerTarget"]] = relationship(back_populates="profile")


class TargetRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "target_requirements"
    __table_args__ = (
        CheckConstraint(
            f"dimension IN ({_DIMENSION_SQL})", name="ck_target_requirements_dimension"
        ),
        CheckConstraint(
            "min_score >= 0 AND min_score <= 1", name="ck_target_requirements_min_score"
        ),
        CheckConstraint(
            "min_confidence >= 0 AND min_confidence <= 1",
            name="ck_target_requirements_min_confidence",
        ),
        CheckConstraint("weight >= 0 AND weight <= 1", name="ck_target_requirements_weight"),
        Index(
            "uq_target_requirements_profile_dimension",
            "profile_id",
            "dimension",
            unique=True,
            postgresql_where=text("skill_id IS NULL"),
        ),
        Index(
            "uq_target_requirements_profile_dimension_skill",
            "profile_id",
            "dimension",
            "skill_id",
            unique=True,
            postgresql_where=text("skill_id IS NOT NULL"),
        ),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("target_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    min_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    min_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    profile: Mapped[TargetProfile] = relationship(back_populates="requirements")
    skill: Mapped["Skill"] = relationship()


class LearnerTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learner_targets"
    __table_args__ = (UniqueConstraint("user_id", name="uq_learner_targets_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("target_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="learner_target")
    profile: Mapped[TargetProfile] = relationship(back_populates="learner_targets")


class DimensionSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dimension_skills"
    __table_args__ = (
        UniqueConstraint("dimension", "skill_id", name="uq_dimension_skills_dimension_skill"),
        CheckConstraint(f"dimension IN ({_DIMENSION_SQL})", name="ck_dimension_skills_dimension"),
    )

    dimension: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    skill: Mapped["Skill"] = relationship()
