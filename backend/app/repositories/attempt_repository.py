from datetime import datetime
from uuid import UUID

from app.core.enums import AttemptEventType, AttemptStatus
from app.models.attempt import Attempt, AttemptEvent
from app.models.problem import Problem
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload


class AttemptRepository:
    def find_by_id_for_user(
        self, session: Session, attempt_id: UUID, user_id: UUID
    ) -> Attempt | None:
        return session.scalar(
            select(Attempt)
            .where(Attempt.id == attempt_id, Attempt.user_id == user_id)
            .options(
                selectinload(Attempt.events),
                selectinload(Attempt.problem).selectinload(Problem.hints),
            )
        )

    def find_by_client_attempt_id(
        self, session: Session, user_id: UUID, client_attempt_id: str
    ) -> Attempt | None:
        return session.scalar(
            select(Attempt)
            .where(
                Attempt.user_id == user_id,
                Attempt.client_attempt_id == client_attempt_id,
            )
            .options(
                selectinload(Attempt.events),
                selectinload(Attempt.problem).selectinload(Problem.hints),
            )
        )

    def find_in_progress_for_problem(
        self, session: Session, user_id: UUID, problem_id: UUID
    ) -> Attempt | None:
        return session.scalar(
            select(Attempt)
            .where(
                Attempt.user_id == user_id,
                Attempt.problem_id == problem_id,
                Attempt.status == AttemptStatus.IN_PROGRESS,
            )
            .options(
                selectinload(Attempt.events),
                selectinload(Attempt.problem).selectinload(Problem.hints),
            )
        )

    def create_attempt(
        self,
        session: Session,
        *,
        user_id: UUID,
        problem_id: UUID,
        client_attempt_id: str,
    ) -> Attempt:
        attempt = Attempt(
            user_id=user_id,
            problem_id=problem_id,
            client_attempt_id=client_attempt_id,
            status=AttemptStatus.IN_PROGRESS,
        )
        session.add(attempt)
        session.flush()
        return attempt

    def add_event(
        self,
        session: Session,
        attempt_id: UUID,
        event_type: AttemptEventType,
        payload: dict,
        occurred_at: datetime | None = None,
    ) -> AttemptEvent:
        event = AttemptEvent(
            attempt_id=attempt_id,
            event_type=event_type,
            payload=payload,
        )
        if occurred_at is not None:
            event.occurred_at = occurred_at
        session.add(event)
        session.flush()
        return event

    def has_hint_revealed_event(self, session: Session, attempt_id: UUID, hint_id: UUID) -> bool:
        events = session.scalars(
            select(AttemptEvent).where(
                AttemptEvent.attempt_id == attempt_id,
                AttemptEvent.event_type == AttemptEventType.HINT_REVEALED,
            )
        ).all()
        hint_id_str = str(hint_id)
        for event in events:
            payload_hint_id = event.payload.get("hint_id")
            if payload_hint_id is not None and str(payload_hint_id) == hint_id_str:
                return True
        return False

    def count_submitted_events(self, session: Session, attempt_id: UUID) -> int:
        from sqlalchemy import func

        count = session.scalar(
            select(func.count())
            .select_from(AttemptEvent)
            .where(
                AttemptEvent.attempt_id == attempt_id,
                AttemptEvent.event_type == AttemptEventType.SUBMITTED,
            )
        )
        return int(count or 0)

    def list_for_user(
        self,
        session: Session,
        user_id: UUID,
        *,
        cursor_attempt_id: UUID | None = None,
        limit: int = 20,
    ) -> tuple[list[Attempt], bool]:
        stmt = (
            select(Attempt)
            .where(Attempt.user_id == user_id)
            .options(selectinload(Attempt.problem))
            .order_by(Attempt.started_at.desc(), Attempt.id.desc())
        )

        if cursor_attempt_id is not None:
            cursor_attempt = session.scalar(
                select(Attempt).where(
                    Attempt.id == cursor_attempt_id,
                    Attempt.user_id == user_id,
                )
            )
            if cursor_attempt is not None:
                stmt = stmt.where(
                    or_(
                        Attempt.started_at < cursor_attempt.started_at,
                        and_(
                            Attempt.started_at == cursor_attempt.started_at,
                            Attempt.id < cursor_attempt.id,
                        ),
                    )
                )

        attempts = list(session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(attempts) > limit
        if has_more:
            attempts = attempts[:limit]
        return attempts, has_more

    def count_submitted_for_user(self, session: Session, user_id: UUID) -> int:
        count = session.scalar(
            select(func.count())
            .select_from(Attempt)
            .where(
                Attempt.user_id == user_id,
                Attempt.status == AttemptStatus.SUBMITTED,
            )
        )
        return int(count or 0)

    def get_last_success_times(
        self,
        session: Session,
        user_id: UUID,
        problem_ids: list[UUID],
    ) -> dict[UUID, datetime]:
        if not problem_ids:
            return {}
        rows = session.execute(
            select(Attempt.problem_id, func.max(Attempt.submitted_at))
            .where(
                Attempt.user_id == user_id,
                Attempt.problem_id.in_(problem_ids),
                Attempt.status == AttemptStatus.SUBMITTED,
                Attempt.is_correct.is_(True),
                Attempt.submitted_at.is_not(None),
            )
            .group_by(Attempt.problem_id)
        ).all()
        return {row[0]: row[1] for row in rows if row[1] is not None}
