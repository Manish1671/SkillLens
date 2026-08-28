import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.assessment import (
        EvidenceItem,
        Recommendation,
        SkillAssessmentSnapshot,
        SkillMastery,
    )
    from app.models.problem import ProblemSkill
    from app.models.topic import Topic


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_foundational: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    topic: Mapped["Topic"] = relationship(back_populates="skills")
    problem_skills: Mapped[list["ProblemSkill"]] = relationship(back_populates="skill")
    prerequisite_edges: Mapped[list["SkillDependency"]] = relationship(
        back_populates="skill",
        foreign_keys="SkillDependency.skill_id",
    )
    dependent_edges: Mapped[list["SkillDependency"]] = relationship(
        back_populates="prerequisite_skill",
        foreign_keys="SkillDependency.prerequisite_skill_id",
    )
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="skill")
    skill_masteries: Mapped[list["SkillMastery"]] = relationship(back_populates="skill")
    skill_assessment_snapshots: Mapped[list["SkillAssessmentSnapshot"]] = relationship(
        back_populates="skill"
    )
    targeted_recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="target_skill",
        foreign_keys="Recommendation.target_skill_id",
    )


class SkillDependency(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skill_dependencies"
    __table_args__ = (
        UniqueConstraint("prerequisite_skill_id", "skill_id", name="uq_skill_dependencies_pair"),
        CheckConstraint(
            "prerequisite_skill_id != skill_id",
            name="ck_skill_dependencies_no_self",
        ),
    )

    prerequisite_skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    prerequisite_skill: Mapped["Skill"] = relationship(
        back_populates="dependent_edges",
        foreign_keys=[prerequisite_skill_id],
    )
    skill: Mapped["Skill"] = relationship(
        back_populates="prerequisite_edges",
        foreign_keys=[skill_id],
    )
