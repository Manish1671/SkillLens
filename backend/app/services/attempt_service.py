import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.attempt_errors import (
    AttemptNotFoundError,
    HintAlreadyRevealedError,
    HintNotFoundError,
    InvalidAttemptTransitionError,
    InvalidEventTypeError,
    InvalidQuizAnswerError,
    InvalidTimeSpentError,
    MissingCodingOutcomeError,
)
from app.core.catalog_errors import NotFoundError
from app.core.enums import ActivityKind, AttemptEventType, AttemptStatus, MistakeType
from app.domain.attempt_sm import (
    FORBIDDEN_EVENT_TYPES_VIA_API,
    abandon_transition,
    can_abandon,
    can_submit,
    event_type_allowed_during_attempt,
    validate_time_spent_seconds,
)
from app.domain.quiz import (
    QuizSpecError,
    encode_quiz_response,
    evaluate_quiz_selection,
    public_quiz_options,
    valid_option_ids,
)
from app.models.attempt import Attempt, AttemptEvent
from app.models.problem import Problem
from app.models.user import User
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.problem_repository import ProblemRepository
from app.schemas.assessment import SubmitAssessmentOutcome
from app.schemas.attempt import (
    AttemptDetailResponse,
    AttemptEventResponse,
    AttemptHintMeta,
    AttemptListItem,
    AttemptListResponse,
    AttemptProblemDetail,
    AttemptProblemSummary,
    AttemptResponse,
    RecordAttemptEventRequest,
    StartAttemptRequest,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
)
from app.schemas.catalog import QuizOptionPublic
from app.services.assessment_service import AssessmentService
from app.services.placement_action_service import PlacementActionService
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AttemptService:
    def __init__(
        self,
        attempt_repository: AttemptRepository,
        problem_repository: ProblemRepository,
        assessment_service: AssessmentService | None = None,
        placement_action_service: PlacementActionService | None = None,
    ) -> None:
        self._attempts = attempt_repository
        self._problems = problem_repository
        self._assessment = assessment_service
        self._placement_actions = placement_action_service

    def start_attempt(
        self,
        session: Session,
        user: User,
        payload: StartAttemptRequest,
    ) -> AttemptResponse:
        problem = self._problems.find_published_by_id(session, payload.problem_id)
        if problem is None:
            raise NotFoundError(detail="Problem not found", code="problem_not_found")

        existing_by_client = self._attempts.find_by_client_attempt_id(
            session, user.id, payload.client_attempt_id
        )
        if existing_by_client is not None:
            return self._to_attempt_response(existing_by_client)

        existing_in_progress = self._attempts.find_in_progress_for_problem(
            session, user.id, payload.problem_id
        )
        if existing_in_progress is not None:
            return self._to_attempt_response(existing_in_progress)

        try:
            attempt = self._attempts.create_attempt(
                session,
                user_id=user.id,
                problem_id=payload.problem_id,
                client_attempt_id=payload.client_attempt_id,
            )
            self._attempts.add_event(session, attempt.id, AttemptEventType.STARTED, {})
            session.commit()
            session.refresh(attempt)
            logger.info(
                "attempt_started user_id=%s attempt_id=%s problem_id=%s",
                user.id,
                attempt.id,
                payload.problem_id,
            )
            return self._to_attempt_response(attempt)
        except IntegrityError:
            session.rollback()
            recovered = self._attempts.find_by_client_attempt_id(
                session, user.id, payload.client_attempt_id
            )
            if recovered is not None:
                return self._to_attempt_response(recovered)
            recovered = self._attempts.find_in_progress_for_problem(
                session, user.id, payload.problem_id
            )
            if recovered is not None:
                return self._to_attempt_response(recovered)
            raise

    def record_event(
        self,
        session: Session,
        user: User,
        attempt_id: UUID,
        payload: RecordAttemptEventRequest,
    ) -> AttemptEventResponse:
        attempt = self._attempts.find_by_id_for_user(session, attempt_id, user.id)
        if attempt is None:
            raise AttemptNotFoundError()

        if payload.event_type in FORBIDDEN_EVENT_TYPES_VIA_API:
            raise InvalidEventTypeError(
                f"Event type '{payload.event_type.value}' must use the dedicated endpoint"
            )

        if attempt.status != AttemptStatus.IN_PROGRESS:
            raise InvalidAttemptTransitionError(
                detail="Events can only be recorded on in-progress attempts",
                code="attempt_not_in_progress",
            )

        if not event_type_allowed_during_attempt(payload.event_type):
            raise InvalidEventTypeError(f"Event type '{payload.event_type.value}' is not supported")

        if payload.event_type == AttemptEventType.HINT_REVEALED:
            return self._record_hint_revealed(session, attempt, payload.payload)

        return self._record_self_report(session, attempt, payload.payload)

    def submit_attempt(
        self,
        session: Session,
        user: User,
        attempt_id: UUID,
        payload: SubmitAttemptRequest,
    ) -> SubmitAttemptResponse:
        attempt = self._attempts.find_by_id_for_user(session, attempt_id, user.id)
        if attempt is None:
            raise AttemptNotFoundError()

        if attempt.status == AttemptStatus.SUBMITTED:
            return self._to_submit_response(attempt, None)

        if attempt.status == AttemptStatus.ABANDONED:
            raise InvalidAttemptTransitionError(
                detail="Abandoned attempts cannot be submitted",
                code="attempt_abandoned",
            )

        if not can_submit(attempt.status):
            raise InvalidAttemptTransitionError(
                detail="Attempt cannot be submitted in its current state",
                code="invalid_attempt_transition",
            )

        if not validate_time_spent_seconds(payload.time_spent_seconds):
            raise InvalidTimeSpentError()

        if payload.mistake_type is not None and not isinstance(payload.mistake_type, MistakeType):
            raise InvalidAttemptTransitionError(
                detail="Invalid mistake_type",
                code="invalid_mistake_type",
            )

        problem = self._problems.find_published_by_id(session, attempt.problem_id)
        if problem is None:
            raise NotFoundError(detail="Problem not found", code="problem_not_found")

        is_correct, code_text, submit_event_payload = self._resolve_submission(problem, payload)

        attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = datetime.now(UTC)
        attempt.time_spent_seconds = payload.time_spent_seconds
        attempt.is_correct = is_correct
        attempt.mistake_type = payload.mistake_type
        attempt.code_text = code_text

        assessment_outcome: SubmitAssessmentOutcome | None = None
        try:
            if self._attempts.count_submitted_events(session, attempt.id) == 0:
                self._attempts.add_event(
                    session,
                    attempt.id,
                    AttemptEventType.SUBMITTED,
                    submit_event_payload,
                )
                if self._assessment is not None:
                    assessment_outcome = self._assessment.process_submission(
                        session, user, attempt, problem
                    )
                if self._placement_actions is not None:
                    self._placement_actions.refresh_after_submission(session, user.id, attempt.id)

            session.commit()
            session.refresh(attempt)
        except Exception:
            session.rollback()
            logger.exception(
                "attempt_submit_failed user_id=%s attempt_id=%s",
                user.id,
                attempt_id,
            )
            raise

        logger.info(
            "attempt_submitted user_id=%s attempt_id=%s is_correct=%s",
            user.id,
            attempt.id,
            is_correct,
        )
        return self._to_submit_response(attempt, assessment_outcome)

    def abandon_attempt(
        self,
        session: Session,
        user: User,
        attempt_id: UUID,
    ) -> AttemptResponse:
        attempt = self._attempts.find_by_id_for_user(session, attempt_id, user.id)
        if attempt is None:
            raise AttemptNotFoundError()

        if attempt.status == AttemptStatus.ABANDONED:
            return self._to_attempt_response(attempt)

        if attempt.status == AttemptStatus.SUBMITTED:
            raise InvalidAttemptTransitionError(
                detail="Submitted attempts cannot be abandoned",
                code="attempt_already_submitted",
            )

        if not can_abandon(attempt.status):
            raise InvalidAttemptTransitionError(
                detail="Attempt cannot be abandoned in its current state",
                code="invalid_attempt_transition",
            )

        new_status = abandon_transition(attempt.status)
        if new_status is None:
            raise InvalidAttemptTransitionError(
                detail="Attempt cannot be abandoned in its current state",
                code="invalid_attempt_transition",
            )

        attempt.status = new_status
        attempt.submitted_at = datetime.now(UTC)
        self._attempts.add_event(session, attempt.id, AttemptEventType.ABANDONED, {})
        session.commit()
        session.refresh(attempt)
        return self._to_attempt_response(attempt)

    def list_attempts(
        self,
        session: Session,
        user: User,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> AttemptListResponse:
        cursor_id: UUID | None = None
        if cursor:
            try:
                cursor_id = UUID(cursor)
            except ValueError:
                cursor_id = None

        attempts, has_more = self._attempts.list_for_user(
            session,
            user.id,
            cursor_attempt_id=cursor_id,
            limit=limit,
        )
        next_cursor = str(attempts[-1].id) if has_more and attempts else None
        return AttemptListResponse(
            items=[self._to_attempt_list_item(attempt) for attempt in attempts],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_attempt_detail(
        self,
        session: Session,
        user: User,
        attempt_id: UUID,
    ) -> AttemptDetailResponse:
        attempt = self._attempts.find_by_id_for_user(session, attempt_id, user.id)
        if attempt is None:
            raise AttemptNotFoundError()

        problem = attempt.problem
        if problem is None:
            problem = self._problems.find_published_by_id(session, attempt.problem_id)
        if problem is None:
            raise NotFoundError(detail="Problem not found", code="problem_not_found")

        hints = sorted(problem.hints, key=lambda hint: hint.ordinal) if problem.hints else []
        events = sorted(attempt.events, key=lambda event: event.occurred_at)
        return AttemptDetailResponse(
            attempt=self._to_attempt_response(attempt),
            problem=self._to_problem_detail(problem),
            events=[
                self._enrich_event_response(session, attempt.problem_id, event) for event in events
            ],
            available_hints=[
                AttemptHintMeta(id=str(hint.id), ordinal=hint.ordinal) for hint in hints
            ],
        )

    def _resolve_submission(
        self,
        problem: Problem,
        payload: SubmitAttemptRequest,
    ) -> tuple[bool, str | None, dict]:
        if problem.activity_kind == ActivityKind.QUIZ:
            if not payload.selected_option:
                raise InvalidQuizAnswerError(
                    "Quiz attempts require selected_option",
                    code="quiz_answer_required",
                )
            allowed = valid_option_ids(problem.quiz_spec)
            if payload.selected_option not in allowed:
                raise InvalidQuizAnswerError(
                    "selected_option is not a valid choice for this quiz",
                    code="invalid_quiz_option",
                )
            try:
                is_correct = evaluate_quiz_selection(problem.quiz_spec, payload.selected_option)
            except QuizSpecError as exc:
                raise InvalidQuizAnswerError(str(exc), code="quiz_spec_invalid") from exc
            code_text = encode_quiz_response(payload.selected_option)
            event_payload = {
                "is_correct": is_correct,
                "time_spent_seconds": payload.time_spent_seconds,
                "mistake_type": payload.mistake_type.value if payload.mistake_type else None,
                "selected_option": payload.selected_option,
                "activity_kind": ActivityKind.QUIZ.value,
            }
            return is_correct, code_text, event_payload

        if payload.is_correct is None:
            raise MissingCodingOutcomeError()
        event_payload = {
            "is_correct": payload.is_correct,
            "time_spent_seconds": payload.time_spent_seconds,
            "mistake_type": payload.mistake_type.value if payload.mistake_type else None,
        }
        return payload.is_correct, payload.code_text, event_payload

    def _record_hint_revealed(
        self,
        session: Session,
        attempt: Attempt,
        payload: dict,
    ) -> AttemptEventResponse:
        hint_id_raw = payload.get("hint_id")
        if hint_id_raw is None:
            raise InvalidEventTypeError("hint_revealed requires payload.hint_id")

        try:
            hint_id = UUID(str(hint_id_raw))
        except ValueError:
            raise InvalidEventTypeError("payload.hint_id must be a valid UUID") from None

        hint = self._problems.find_hint_for_problem(session, attempt.problem_id, hint_id)
        if hint is None:
            raise HintNotFoundError()

        if self._attempts.has_hint_revealed_event(session, attempt.id, hint_id):
            raise HintAlreadyRevealedError()

        attempt.hints_used_count += 1
        event = self._attempts.add_event(
            session,
            attempt.id,
            AttemptEventType.HINT_REVEALED,
            {"hint_id": str(hint_id), "ordinal": hint.ordinal},
        )
        session.commit()
        session.refresh(event)
        return self._to_event_response(event, hint_body_md=hint.body_md)

    def _record_self_report(
        self,
        session: Session,
        attempt: Attempt,
        payload: dict,
    ) -> AttemptEventResponse:
        event = self._attempts.add_event(
            session,
            attempt.id,
            AttemptEventType.SELF_REPORT,
            payload,
        )
        session.commit()
        session.refresh(event)
        return self._to_event_response(event)

    def _to_submit_response(
        self,
        attempt: Attempt,
        assessment: SubmitAssessmentOutcome | None,
    ) -> SubmitAttemptResponse:
        base = self._to_attempt_response(attempt)
        return SubmitAttemptResponse(
            **base.model_dump(),
            assessment=assessment,
        )

    def _to_attempt_response(self, attempt: Attempt) -> AttemptResponse:
        return AttemptResponse(
            id=str(attempt.id),
            problem_id=str(attempt.problem_id),
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            time_spent_seconds=attempt.time_spent_seconds,
            hints_used_count=attempt.hints_used_count,
            is_correct=attempt.is_correct,
            mistake_type=attempt.mistake_type,
            code_text=attempt.code_text,
            client_attempt_id=attempt.client_attempt_id,
        )

    def _to_attempt_list_item(self, attempt: Attempt) -> AttemptListItem:
        problem = attempt.problem
        if problem is None:
            raise NotFoundError(detail="Problem not found", code="problem_not_found")
        return AttemptListItem(
            id=str(attempt.id),
            problem=self._to_problem_summary(problem),
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            time_spent_seconds=attempt.time_spent_seconds,
            hints_used_count=attempt.hints_used_count,
            is_correct=attempt.is_correct,
            mistake_type=attempt.mistake_type,
        )

    def _to_problem_summary(self, problem: Problem) -> AttemptProblemSummary:
        return AttemptProblemSummary(
            id=str(problem.id),
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            activity_kind=problem.activity_kind,
        )

    def _to_problem_detail(self, problem: Problem) -> AttemptProblemDetail:
        hint_count = len(problem.hints) if problem.hints else 0
        options = None
        if problem.activity_kind == ActivityKind.QUIZ:
            options = [
                QuizOptionPublic(id=item["id"], label=item["label"])
                for item in public_quiz_options(problem.quiz_spec)
            ]
        return AttemptProblemDetail(
            id=str(problem.id),
            slug=problem.slug,
            title=problem.title,
            difficulty=problem.difficulty,
            prompt_md=problem.prompt_md,
            hint_count=hint_count,
            activity_kind=problem.activity_kind,
            options=options,
        )

    def _enrich_event_response(
        self,
        session: Session,
        problem_id: UUID,
        event: AttemptEvent,
    ) -> AttemptEventResponse:
        hint_body_md: str | None = None
        if event.event_type == AttemptEventType.HINT_REVEALED:
            hint_id_raw = event.payload.get("hint_id")
            if hint_id_raw is not None:
                try:
                    hint_id = UUID(str(hint_id_raw))
                    hint = self._problems.find_hint_for_problem(session, problem_id, hint_id)
                    if hint is not None:
                        hint_body_md = hint.body_md
                except ValueError:
                    pass
        return self._to_event_response(event, hint_body_md=hint_body_md)

    def _to_event_response(
        self,
        event: AttemptEvent,
        hint_body_md: str | None = None,
    ) -> AttemptEventResponse:
        return AttemptEventResponse(
            id=str(event.id),
            event_type=event.event_type,
            payload=event.payload,
            occurred_at=event.occurred_at,
            hint_body_md=hint_body_md,
        )
