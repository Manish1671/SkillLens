from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.auth_errors import InvalidTokenError
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: UUID | str) -> str:
    return _create_token(
        _as_uuid(user_id),
        TOKEN_TYPE_ACCESS,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID | str) -> str:
    return _create_token(
        _as_uuid(user_id), TOKEN_TYPE_REFRESH, timedelta(days=settings.refresh_token_expire_days)
    )


def _as_uuid(user_id: UUID | str) -> UUID:
    return user_id if isinstance(user_id, UUID) else UUID(str(user_id))


def _create_token(user_id: UUID, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise InvalidTokenError() from None

    token_type = payload.get("type")
    if token_type != expected_type:
        raise InvalidTokenError(
            detail="Invalid token type",
            code="invalid_token_type",
        )

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError()

    try:
        return UUID(str(subject))
    except ValueError:
        raise InvalidTokenError() from None


def create_token_with_expiry(user_id: UUID, token_type: str, expires_at: datetime) -> str:
    """Test helper for expired-token scenarios."""
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": datetime.now(UTC),
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
