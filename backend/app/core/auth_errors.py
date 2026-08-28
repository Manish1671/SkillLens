from app.core.exceptions import AppError


class AuthenticationError(AppError):
    def __init__(self, detail: str = "Authentication required", code: str = "unauthorized") -> None:
        super().__init__(detail=detail, code=code, status_code=401)


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="Invalid email or password",
            code="invalid_credentials",
            status_code=401,
        )


class EmailAlreadyExistsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="An account with this email already exists",
            code="email_already_exists",
            status_code=409,
        )


class InvalidTokenError(AppError):
    def __init__(
        self, detail: str = "Invalid or expired token", code: str = "invalid_token"
    ) -> None:
        super().__init__(detail=detail, code=code, status_code=401)
