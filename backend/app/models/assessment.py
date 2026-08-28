import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EvidencePolarity, MasteryStatus, pg_enum
from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.problem import Problem
    from app.models.skill import Skill
    from app.models.user import User


class EvidenceItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        Index("ix_evidence_items_user_skill_created", "user_id", "skill_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    polarity: Mapped[EvidencePolarity] = mapped_column(
        pg_enum(EvidencePolarity, "evidence_polarity"),
        nullable=False,
    )
    strength: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped["User"] = relationship(back_populates="evidence_items")
    skill: Mapped["Skill"] = relationship(back_populates="evidence_items")
    attempt: Mapped["Attempt"] = relationship(back_populates="evidence_items")


class SkillMastery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skill_masteries"
    __table_args__ = (Index("uq_skill_masteries_user_skill", "user_id", "skill_id", unique=True),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MasteryStatus] = mapped_column(
        pg_enum(MasteryStatus, "mastery_status"),
        nullable=False,
        default=MasteryStatus.INSUFFICIENT,
    )

    user: Mapped["User"] = relationship(back_populates="skill_masteries")
    skill: Mapped["Skill"] = relationship(back_populates="skill_masteries")


class SkillAssessmentSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "skill_assessment_snapshots"
    __table_args__ = (
        Index("ix_snapshots_user_skill_computed", "user_id", "skill_id", "computed_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="skill_assessment_snapshots")
    skill: Mapped["Skill"] = relationship(back_populates="skill_assessment_snapshots")
    attempt: Mapped["Attempt"] = relationship(back_populates="skill_assessment_snapshots")


class Recommendation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_user_generated", "user_id", "generated_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="recommendations")
    problem: Mapped["Problem"] = relationship()
    target_skill: Mapped["Skill"] = relationship(
        back_populates="targeted_recommendations",
        foreign_keys=[target_skill_id],
    )
    source_attempt: Mapped["Attempt"] = relationship(foreign_keys=[source_attempt_id])
