import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ActivityKind, Difficulty, pg_enum
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.skill import Skill
    from app.models.topic import Topic


class Problem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "problems"

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_md: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        pg_enum(Difficulty, "difficulty"), nullable=False
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_kind: Mapped[ActivityKind] = mapped_column(
        pg_enum(ActivityKind, "activity_kind"),
        nullable=False,
        default=ActivityKind.CODING,
        server_default="coding",
    )
    quiz_spec: Mapped[dict] = mapped_column(JSONB, nullable=True)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    solution_outline_md: Mapped[str] = mapped_column(Text, nullable=True)

    topic: Mapped["Topic"] = relationship(back_populates="problems")
    problem_skills: Mapped[list["ProblemSkill"]] = relationship(back_populates="problem")
    hints: Mapped[list["Hint"]] = relationship(back_populates="problem", order_by="Hint.ordinal")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="problem")


class ProblemSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "problem_skills"
    __table_args__ = (UniqueConstraint("problem_id", "skill_id", name="uq_problem_skills_pair"),)

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="RESTRICT"),
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("1.0"))

    problem: Mapped["Problem"] = relationship(back_populates="problem_skills")
    skill: Mapped["Skill"] = relationship(back_populates="problem_skills")


class Hint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hints"
    __table_args__ = (UniqueConstraint("problem_id", "ordinal", name="uq_hints_problem_ordinal"),)

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)

    problem: Mapped["Problem"] = relationship(back_populates="hints")
