from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.auth_errors import AuthenticationError, InvalidTokenError
from app.core.config import settings
from app.core.database import get_db
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

user_repository = UserRepository()


def get_current_user_id(
    access_token: Annotated[str | None, Cookie(alias=settings.access_cookie_name)] = None,
) -> str:
    if not access_token:
        raise AuthenticationError()
    try:
        user_id = decode_token(access_token, TOKEN_TYPE_ACCESS)
    except InvalidTokenError:
        raise AuthenticationError(
            detail="Invalid or expired access token", code="invalid_token"
        ) from None
    return str(user_id)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> User:
    user = user_repository.find_by_id(db, user_id)
    if user is None:
        raise AuthenticationError(detail="User not found", code="unauthorized")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_current_user(
    db: Annotated[Session, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias=settings.access_cookie_name)] = None,
) -> User | None:
    if not access_token:
        return None
    try:
        user_id = decode_token(access_token, TOKEN_TYPE_ACCESS)
    except InvalidTokenError:
        return None
    return user_repository.find_by_id(db, str(user_id))


OptionalUser = Annotated[User | None, Depends(get_optional_current_user)]
