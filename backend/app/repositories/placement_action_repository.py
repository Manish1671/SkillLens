from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.placement_action import PlacementAction
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload


class PlacementActionRepository:
    def create(
        self,
        session: Session,
        *,
        user_id: UUID,
        action_kind: str,
        target_dimension: str,
        target_skill_id: UUID | None,
        problem_id: UUID | None,
        rank: int,
        score: float,
        title: str,
        explanation: dict,
        payload: dict,
        generated_at: datetime,
        source_attempt_id: UUID | None,
    ) -> PlacementAction:
        row = PlacementAction(
            user_id=user_id,
            action_kind=action_kind,
            target_dimension=target_dimension,
            target_skill_id=target_skill_id,
            problem_id=problem_id,
            rank=rank,
            score=Decimal(str(round(score, 4))),
            title=title,
            explanation=explanation,
            payload=payload,
            generated_at=generated_at,
            source_attempt_id=source_attempt_id,
        )
        session.add(row)
        session.flush()
        return row

    def find_by_id_for_user(
        self, session: Session, user_id: UUID, action_id: UUID
    ) -> PlacementAction | None:
        return session.scalar(
            select(PlacementAction)
            .where(PlacementAction.id == action_id, PlacementAction.user_id == user_id)
            .options(
                selectinload(PlacementAction.target_skill),
                selectinload(PlacementAction.problem),
            )
        )

    def get_latest_generated_at(self, session: Session, user_id: UUID) -> datetime | None:
        return session.scalar(
            select(func.max(PlacementAction.generated_at)).where(PlacementAction.user_id == user_id)
        )

    def list_latest_batch(
        self, session: Session, user_id: UUID, *, limit: int = 10
    ) -> list[PlacementAction]:
        latest = self.get_latest_generated_at(session, user_id)
        if latest is None:
            return []
        return list(
            session.scalars(
                select(PlacementAction)
                .where(
                    PlacementAction.user_id == user_id,
                    PlacementAction.generated_at == latest,
                )
                .options(
                    selectinload(PlacementAction.target_skill),
                    selectinload(PlacementAction.problem),
                )
                .order_by(PlacementAction.rank.asc())
                .limit(limit)
            ).all()
        )

    def exists_for_attempt(self, session: Session, user_id: UUID, attempt_id: UUID) -> bool:
        item = session.scalar(
            select(PlacementAction.id)
            .where(
                PlacementAction.user_id == user_id,
                PlacementAction.source_attempt_id == attempt_id,
            )
            .limit(1)
        )
        return item is not None
