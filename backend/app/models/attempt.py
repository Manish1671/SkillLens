import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AttemptEventType, AttemptStatus, MistakeType, pg_enum
from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.assessment import EvidenceItem, SkillAssessmentSnapshot
    from app.models.problem import Problem
    from app.models.user import User


class Attempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "client_attempt_id", name="uq_attempts_user_client_attempt"),
        Index("ix_attempts_user_created_at", "user_id", "created_at"),
        Index("ix_attempts_user_problem", "user_id", "problem_id"),
        Index(
            "uq_attempts_user_problem_in_progress",
            "user_id",
            "problem_id",
            unique=True,
            postgresql_where="status = 'in_progress'",
        ),
    )

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
    status: Mapped[AttemptStatus] = mapped_column(
        pg_enum(AttemptStatus, "attempt_status"),
        nullable=False,
        default=AttemptStatus.IN_PROGRESS,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    hints_used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_correct: Mapped[bool] = mapped_column(nullable=True)
    mistake_type: Mapped[MistakeType] = mapped_column(
        pg_enum(MistakeType, "mistake_type"),
        nullable=True,
    )
    code_text: Mapped[str] = mapped_column(Text, nullable=True)
    client_attempt_id: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped["User"] = relationship(back_populates="attempts")
    problem: Mapped["Problem"] = relationship(back_populates="attempts")
    events: Mapped[list["AttemptEvent"]] = relationship(back_populates="attempt")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="attempt")
    skill_assessment_snapshots: Mapped[list["SkillAssessmentSnapshot"]] = relationship(
        back_populates="attempt"
    )


class AttemptEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "attempt_events"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[AttemptEventType] = mapped_column(
        pg_enum(AttemptEventType, "attempt_event_type"),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    attempt: Mapped["Attempt"] = relationship(back_populates="events")
