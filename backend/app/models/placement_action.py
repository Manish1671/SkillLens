import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.problem import Problem
    from app.models.skill import Skill
    from app.models.user import User

ACTION_KINDS = ("dsa_problem", "cs_quiz", "assess_dimension")
_ACTION_KIND_SQL = ", ".join(f"'{value}'" for value in ACTION_KINDS)
DIMENSION_VALUES = ("dsa", "core_cs", "projects", "interview", "profile")
_DIMENSION_SQL = ", ".join(f"'{value}'" for value in DIMENSION_VALUES)


class PlacementAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "placement_actions"
    __table_args__ = (
        CheckConstraint(
            f"action_kind IN ({_ACTION_KIND_SQL})",
            name="ck_placement_actions_action_kind",
        ),
        CheckConstraint(
            f"target_dimension IN ({_DIMENSION_SQL})",
            name="ck_placement_actions_target_dimension",
        ),
        Index("ix_placement_actions_user_generated", "user_id", "generated_at"),
        Index("ix_placement_actions_user_rank", "user_id", "generated_at", "rank"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_dimension: Mapped[str] = mapped_column(String(32), nullable=False)
    target_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
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

    user: Mapped["User"] = relationship(back_populates="placement_actions")
    target_skill: Mapped["Skill"] = relationship()
    problem: Mapped["Problem"] = relationship()
    source_attempt: Mapped["Attempt"] = relationship()
