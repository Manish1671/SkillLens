from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.problem_repository import ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.catalog import SkillDetailResponse, SkillSummary
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/skills", tags=["catalog"])

catalog_service = CatalogService(
    TopicRepository(),
    SkillRepository(),
    ProblemRepository(),
)


@router.get("", response_model=list[SkillSummary])
def list_skills(db: Annotated[Session, Depends(get_db)]) -> list[SkillSummary]:
    return catalog_service.list_skills(db)


@router.get("/{slug}", response_model=SkillDetailResponse)
def get_skill(slug: str, db: Annotated[Session, Depends(get_db)]) -> SkillDetailResponse:
    return catalog_service.get_skill_detail(db, slug)
