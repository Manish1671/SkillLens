from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.problem_repository import ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.catalog import TopicSummary
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/topics", tags=["catalog"])

catalog_service = CatalogService(
    TopicRepository(),
    SkillRepository(),
    ProblemRepository(),
)


@router.get("", response_model=list[TopicSummary])
def list_topics(db: Annotated[Session, Depends(get_db)]) -> list[TopicSummary]:
    return catalog_service.list_topics(db)
