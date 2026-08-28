"""Pure attempt lifecycle rules — no framework or database imports."""

from app.core.enums import AttemptEventType, AttemptStatus

ALLOWED_EVENT_TYPES_IN_PROGRESS = frozenset(
    {
        AttemptEventType.HINT_REVEALED,
        AttemptEventType.SELF_REPORT,
    }
)

FORBIDDEN_EVENT_TYPES_VIA_API = frozenset(
    {
        AttemptEventType.STARTED,
        AttemptEventType.SUBMITTED,
        AttemptEventType.ABANDONED,
    }
)

MAX_TIME_SPENT_SECONDS = 14_400  # 4 hours — generous but bounded


def can_submit(status: AttemptStatus) -> bool:
    return status == AttemptStatus.IN_PROGRESS


def can_abandon(status: AttemptStatus) -> bool:
    return status == AttemptStatus.IN_PROGRESS


def is_terminal(status: AttemptStatus) -> bool:
    return status in {AttemptStatus.SUBMITTED, AttemptStatus.ABANDONED}


def submit_transition(status: AttemptStatus) -> AttemptStatus | None:
    if status == AttemptStatus.IN_PROGRESS:
        return AttemptStatus.SUBMITTED
    return None


def abandon_transition(status: AttemptStatus) -> AttemptStatus | None:
    if status == AttemptStatus.IN_PROGRESS:
        return AttemptStatus.ABANDONED
    return None


def validate_time_spent_seconds(value: int) -> bool:
    return 0 <= value <= MAX_TIME_SPENT_SECONDS


def event_type_allowed_during_attempt(event_type: AttemptEventType) -> bool:
    return event_type in ALLOWED_EVENT_TYPES_IN_PROGRESS
