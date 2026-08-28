import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth_errors import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthMessageResponse, LoginRequest, PublicUserResponse, RegisterRequest
from app.schemas.mappers import to_public_user
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

auth_service = AuthService(UserRepository())


def _set_auth_cookies(response: Response, user_id: str) -> None:
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    response.set_cookie(
        key=settings.access_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path=settings.cookie_path,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=settings.cookie_path,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.access_cookie_name,
        path=settings.cookie_path,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.cookie_path,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=PublicUserResponse)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PublicUserResponse:
    user = auth_service.register(db, payload)
    return to_public_user(user)


@router.post("/login", response_model=PublicUserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> PublicUserResponse:
    try:
        user = auth_service.authenticate(db, payload)
    except InvalidCredentialsError:
        logger.info("authentication_failed email=%s", payload.email)
        raise
    _set_auth_cookies(response, str(user.id))
    return to_public_user(user)


@router.post("/logout", response_model=AuthMessageResponse)
def logout(response: Response) -> AuthMessageResponse:
    _clear_auth_cookies(response)
    return AuthMessageResponse(message="Logged out")


@router.post("/refresh", response_model=AuthMessageResponse)
def refresh(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=settings.refresh_cookie_name)] = None,
) -> AuthMessageResponse:
    if not refresh_token:
        raise AuthenticationError(detail="Refresh token missing", code="unauthorized")

    try:
        user_id = decode_token(refresh_token, TOKEN_TYPE_REFRESH)
    except InvalidTokenError:
        raise AuthenticationError(
            detail="Invalid or expired refresh token",
            code="invalid_token",
        ) from None

    user = auth_service.get_user_by_id(db, str(user_id))
    if user is None:
        raise AuthenticationError(detail="User not found", code="unauthorized")

    # Rotate refresh token on each refresh.
    _set_auth_cookies(response, str(user.id))
    return AuthMessageResponse(message="Token refreshed")


@router.get("/me", response_model=PublicUserResponse)
def me(current_user: CurrentUser) -> PublicUserResponse:
    return to_public_user(current_user)
