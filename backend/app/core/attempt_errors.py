from app.core.exceptions import AppError


class AttemptNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="Attempt not found",
            code="attempt_not_found",
            status_code=404,
        )


class InvalidAttemptTransitionError(AppError):
    def __init__(self, detail: str, code: str = "invalid_attempt_transition") -> None:
        super().__init__(detail=detail, code=code, status_code=409)


class InvalidTimeSpentError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="time_spent_seconds must be between 0 and 14400",
            code="invalid_time_spent",
            status_code=422,
        )


class HintNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="Hint not found for this problem",
            code="hint_not_found",
            status_code=404,
        )


class HintAlreadyRevealedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="Hint has already been revealed",
            code="hint_already_revealed",
            status_code=409,
        )


class InvalidEventTypeError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            detail=detail,
            code="invalid_event_type",
            status_code=422,
        )


class InvalidQuizAnswerError(AppError):
    def __init__(self, detail: str, code: str = "invalid_quiz_option") -> None:
        super().__init__(detail=detail, code=code, status_code=422)


class MissingCodingOutcomeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="Coding attempts require is_correct",
            code="coding_outcome_required",
            status_code=422,
        )
