from uuid import UUID

from app.core.security import normalize_email
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    def find_by_email(self, session: Session, email: str) -> User | None:
        normalized = normalize_email(email)
        return session.scalar(select(User).where(User.email == normalized))

    def find_by_id(self, session: Session, user_id: str | UUID) -> User | None:
        return session.get(User, user_id)

    def email_exists(self, session: Session, email: str) -> bool:
        return self.find_by_email(session, email) is not None

    def create(
        self,
        session: Session,
        email: str,
        password_hash: str,
        display_name: str,
    ) -> User:
        user = User(
            email=normalize_email(email),
            password_hash=password_hash,
            display_name=display_name.strip(),
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        return user
