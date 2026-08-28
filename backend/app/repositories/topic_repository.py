from app.models.topic import Topic
from sqlalchemy import select
from sqlalchemy.orm import Session


class TopicRepository:
    def list_all(self, session: Session) -> list[Topic]:
        return list(session.scalars(select(Topic).order_by(Topic.sort_order, Topic.slug)).all())

    def find_by_slug(self, session: Session, slug: str) -> Topic | None:
        return session.scalar(select(Topic).where(Topic.slug == slug))
