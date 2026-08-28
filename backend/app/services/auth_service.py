from app.core.auth_errors import EmailAlreadyExistsError, InvalidCredentialsError
from app.core.security import hash_password, normalize_email, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from sqlalchemy.orm import Session


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    def register(self, session: Session, payload: RegisterRequest) -> User:
        normalized_email = normalize_email(payload.email)
        if self._users.email_exists(session, normalized_email):
            raise EmailAlreadyExistsError()

        user = self._users.create(
            session,
            email=normalized_email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
        )
        session.commit()
        session.refresh(user)
        return user

    def authenticate(self, session: Session, payload: LoginRequest) -> User:
        user = self._users.find_by_email(session, payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError()
        return user

    def get_user_by_id(self, session: Session, user_id: str) -> User | None:
        return self._users.find_by_id(session, user_id)
