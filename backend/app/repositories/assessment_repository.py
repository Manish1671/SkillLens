from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.core.enums import EvidencePolarity
from app.models.assessment import (
    EvidenceItem,
    Recommendation,
    SkillAssessmentSnapshot,
    SkillMastery,
)
from app.models.skill import SkillDependency
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class EvidenceRepository:
    def exists_for_attempt(self, session: Session, attempt_id: UUID) -> bool:
        item = session.scalar(
            select(EvidenceItem.id).where(EvidenceItem.attempt_id == attempt_id).limit(1)
        )
        return item is not None

    def create(
        self,
        session: Session,
        *,
        user_id: UUID,
        skill_id: UUID,
        attempt_id: UUID,
        evidence_type: str,
        polarity: EvidencePolarity,
        strength: float,
        summary_text: str,
        details: dict,
    ) -> EvidenceItem:
        item = EvidenceItem(
            user_id=user_id,
            skill_id=skill_id,
            attempt_id=attempt_id,
            evidence_type=evidence_type,
            polarity=polarity,
            strength=Decimal(str(round(strength, 4))),
            summary_text=summary_text,
            details=details,
        )
        session.add(item)
        session.flush()
        return item

    def list_for_user_skill(
        self, session: Session, user_id: UUID, skill_id: UUID
    ) -> list[EvidenceItem]:
        return list(
            session.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.user_id == user_id, EvidenceItem.skill_id == skill_id)
                .order_by(EvidenceItem.created_at.asc())
            ).all()
        )

    def list_for_user_skill_recent(
        self, session: Session, user_id: UUID, skill_id: UUID, limit: int = 20
    ) -> list[EvidenceItem]:
        return list(
            session.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.user_id == user_id, EvidenceItem.skill_id == skill_id)
                .order_by(EvidenceItem.created_at.desc())
                .limit(limit)
            ).all()
        )

    def list_for_user(self, session: Session, user_id: UUID, limit: int = 50) -> list[EvidenceItem]:
        return list(
            session.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.user_id == user_id)
                .order_by(EvidenceItem.created_at.desc())
                .limit(limit)
            ).all()
        )

    def recent_failure_records(
        self, session: Session, user_id: UUID, skill_ids: list[UUID], limit: int = 30
    ) -> list[EvidenceItem]:
        if not skill_ids:
            return []
        return list(
            session.scalars(
                select(EvidenceItem)
                .where(
                    EvidenceItem.user_id == user_id,
                    EvidenceItem.skill_id.in_(skill_ids),
                    EvidenceItem.evidence_type == "failed_attempt",
                )
                .order_by(EvidenceItem.created_at.desc())
                .limit(limit)
            ).all()
        )


class MasteryRepository:
    def get_for_user_skill(
        self, session: Session, user_id: UUID, skill_id: UUID
    ) -> SkillMastery | None:
        return session.scalar(
            select(SkillMastery).where(
                SkillMastery.user_id == user_id,
                SkillMastery.skill_id == skill_id,
            )
        )

    def list_for_user(self, session: Session, user_id: UUID) -> list[SkillMastery]:
        return list(
            session.scalars(select(SkillMastery).where(SkillMastery.user_id == user_id)).all()
        )

    def upsert(
        self,
        session: Session,
        *,
        user_id: UUID,
        skill_id: UUID,
        score: Decimal,
        confidence: Decimal,
        evidence_count: int,
        last_attempt_at: datetime | None,
        status,
    ) -> SkillMastery:
        existing = self.get_for_user_skill(session, user_id, skill_id)
        if existing is None:
            mastery = SkillMastery(
                user_id=user_id,
                skill_id=skill_id,
                score=score,
                confidence=confidence,
                evidence_count=evidence_count,
                last_attempt_at=last_attempt_at,
                status=status,
            )
            session.add(mastery)
            session.flush()
            return mastery

        existing.score = score
        existing.confidence = confidence
        existing.evidence_count = evidence_count
        existing.last_attempt_at = last_attempt_at
        existing.status = status
        session.flush()
        return existing

    def get_prerequisite_scores(
        self, session: Session, user_id: UUID, skill_id: UUID
    ) -> list[tuple[UUID, str, float]]:
        rows = session.execute(
            select(
                SkillDependency.prerequisite_skill_id,
                SkillMastery.score,
            )
            .join(
                SkillMastery,
                SkillMastery.skill_id == SkillDependency.prerequisite_skill_id,
            )
            .where(
                SkillDependency.skill_id == skill_id,
                SkillMastery.user_id == user_id,
            )
        ).all()
        return [(row[0], float(row[1])) for row in rows]


class SnapshotRepository:
    def create(
        self,
        session: Session,
        *,
        user_id: UUID,
        skill_id: UUID,
        attempt_id: UUID,
        score: Decimal,
        confidence: Decimal,
        computed_at: datetime,
    ) -> SkillAssessmentSnapshot:
        snapshot = SkillAssessmentSnapshot(
            user_id=user_id,
            skill_id=skill_id,
            attempt_id=attempt_id,
            score=score,
            confidence=confidence,
            computed_at=computed_at,
        )
        session.add(snapshot)
        session.flush()
        return snapshot

    def list_for_user_skill(
        self, session: Session, user_id: UUID, skill_id: UUID, limit: int = 20
    ) -> list[SkillAssessmentSnapshot]:
        return list(
            session.scalars(
                select(SkillAssessmentSnapshot)
                .where(
                    SkillAssessmentSnapshot.user_id == user_id,
                    SkillAssessmentSnapshot.skill_id == skill_id,
                )
                .order_by(SkillAssessmentSnapshot.computed_at.desc())
                .limit(limit)
            ).all()
        )


class RecommendationRepository:
    def create(
        self,
        session: Session,
        *,
        user_id: UUID,
        problem_id: UUID,
        target_skill_id: UUID,
        rank: int,
        score: float,
        explanation: dict,
        generated_at: datetime,
        source_attempt_id: UUID | None = None,
    ) -> Recommendation:
        rec = Recommendation(
            user_id=user_id,
            problem_id=problem_id,
            target_skill_id=target_skill_id,
            rank=rank,
            score=Decimal(str(round(score, 4))),
            explanation=explanation,
            generated_at=generated_at,
            source_attempt_id=source_attempt_id,
        )
        session.add(rec)
        session.flush()
        return rec

    def find_by_id_for_user(
        self, session: Session, user_id: UUID, recommendation_id: UUID
    ) -> Recommendation | None:
        return session.scalar(
            select(Recommendation).where(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user_id,
            )
        )

    def exists_for_attempt(self, session: Session, user_id: UUID, attempt_id: UUID) -> bool:
        item = session.scalar(
            select(Recommendation.id)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.source_attempt_id == attempt_id,
            )
            .limit(1)
        )
        return item is not None

    def get_latest_generated_at(self, session: Session, user_id: UUID) -> datetime | None:
        return session.scalar(
            select(func.max(Recommendation.generated_at)).where(Recommendation.user_id == user_id)
        )

    def list_latest_batch(
        self, session: Session, user_id: UUID, limit: int = 10
    ) -> list[Recommendation]:
        latest = self.get_latest_generated_at(session, user_id)
        if latest is None:
            return []
        return list(
            session.scalars(
                select(Recommendation)
                .where(
                    Recommendation.user_id == user_id,
                    Recommendation.generated_at == latest,
                )
                .order_by(Recommendation.rank.asc())
                .limit(limit)
            ).all()
        )

    def list_for_user_skill_latest(
        self, session: Session, user_id: UUID, skill_id: UUID
    ) -> Recommendation | None:
        return session.scalar(
            select(Recommendation)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.target_skill_id == skill_id,
            )
            .order_by(Recommendation.generated_at.desc(), Recommendation.rank.asc())
            .limit(1)
        )
