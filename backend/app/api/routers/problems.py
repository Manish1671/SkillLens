from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import OptionalUser
from app.core.enums import ActivityKindQuery, Difficulty
from app.repositories.problem_repository import ProblemRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.catalog import ProblemDetailResponse, ProblemListResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/problems", tags=["catalog"])

catalog_service = CatalogService(
    TopicRepository(),
    SkillRepository(),
    ProblemRepository(),
)


@router.get("", response_model=ProblemListResponse)
def list_problems(
    db: Annotated[Session, Depends(get_db)],
    current_user: OptionalUser,
    topic: Annotated[str | None, Query(description="Filter by topic slug")] = None,
    skill: Annotated[str | None, Query(description="Filter by skill slug")] = None,
    difficulty: Annotated[Difficulty | None, Query(description="Filter by difficulty")] = None,
    activity_kind: Annotated[
        ActivityKindQuery,
        Query(description="Filter by activity kind. Default coding. Use all to include quizzes."),
    ] = ActivityKindQuery.CODING,
    q: Annotated[str | None, Query(description="Search title or slug")] = None,
    cursor: Annotated[str | None, Query(description="Pagination cursor (problem slug)")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProblemListResponse:
    return catalog_service.list_problems(
        db,
        topic=topic,
        skill=skill,
        difficulty=difficulty,
        activity_kind=activity_kind,
        search_query=q,
        cursor=cursor,
        limit=limit,
        current_user=current_user,
    )


@router.get("/{slug}", response_model=ProblemDetailResponse)
def get_problem(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: OptionalUser,
) -> ProblemDetailResponse:
    return catalog_service.get_problem_detail(db, slug, current_user=current_user)
