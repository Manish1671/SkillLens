from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.assessment import (
        EvidenceItem,
        Recommendation,
        SkillAssessmentSnapshot,
        SkillMastery,
    )
    from app.models.attempt import Attempt
    from app.models.placement_action import PlacementAction
    from app.models.readiness import LearnerTarget


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="user")
    skill_masteries: Mapped[list["SkillMastery"]] = relationship(back_populates="user")
    skill_assessment_snapshots: Mapped[list["SkillAssessmentSnapshot"]] = relationship(
        back_populates="user"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="user")
    placement_actions: Mapped[list["PlacementAction"]] = relationship(back_populates="user")
    learner_target: Mapped["LearnerTarget"] = relationship(
        back_populates="user",
        uselist=False,
    )
