from app.core.exceptions import AppError


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found", code: str = "not_found") -> None:
        super().__init__(detail=detail, code=code, status_code=404)
