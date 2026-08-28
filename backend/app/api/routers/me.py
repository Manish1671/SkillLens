from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.catalog_errors import NotFoundError
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.services import (
    assessment_plan_service,
    assessment_service,
    attempt_service,
    placement_action_service,
    readiness_service,
    recommendation_service,
)
from app.schemas.assessment import UserMasteryResponse, UserSkillDetailResponse
from app.schemas.assessment_plan import AssessmentPlanResponse
from app.schemas.attempt import AttemptListResponse
from app.schemas.placement_action import (
    NextPlacementActionResponse,
    PlacementActionItem,
    PlacementActionListResponse,
)
from app.schemas.readiness import (
    GapListResponse,
    LearnerTargetResponse,
    PlacementReadinessResponse,
    SetLearnerTargetRequest,
)
from app.schemas.recommendation import (
    NextRecommendationResponse,
    RecommendationItem,
    RecommendationListResponse,
)

router = APIRouter(prefix="/me", tags=["learner"])


@router.get("/target", response_model=LearnerTargetResponse)
def get_my_target(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> LearnerTargetResponse:
    return readiness_service.get_learner_target(db, current_user.id)


@router.put("/target", response_model=LearnerTargetResponse)
def set_my_target(
    payload: SetLearnerTargetRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> LearnerTargetResponse:
    result = readiness_service.set_learner_target(db, current_user, payload.profile_slug)
    placement_action_service.get_actions(db, current_user.id, refresh=True, commit=True, limit=5)
    return result


@router.get("/readiness", response_model=PlacementReadinessResponse)
def get_my_readiness(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> PlacementReadinessResponse:
    return readiness_service.get_readiness(db, current_user.id)


@router.get("/gaps", response_model=GapListResponse)
def get_my_gaps(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> GapListResponse:
    return readiness_service.get_gaps(db, current_user.id)


@router.get("/actions/next", response_model=NextPlacementActionResponse)
def get_next_placement_action(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    refresh: Annotated[bool, Query()] = False,
) -> NextPlacementActionResponse:
    return placement_action_service.get_next(db, current_user.id, refresh=refresh, commit=True)


@router.get("/actions", response_model=PlacementActionListResponse)
def list_placement_actions(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    dimension: Annotated[str | None, Query()] = None,
    refresh: Annotated[bool, Query()] = False,
) -> PlacementActionListResponse:
    return placement_action_service.get_actions(
        db,
        current_user.id,
        limit=limit,
        dimension=dimension,
        refresh=refresh,
        commit=True,
    )


@router.get("/actions/{action_id}", response_model=PlacementActionItem)
def get_placement_action_detail(
    action_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> PlacementActionItem:
    detail = placement_action_service.get_detail(db, current_user.id, action_id)
    if detail is None:
        raise NotFoundError(detail="Placement action not found", code="placement_action_not_found")
    return detail


@router.get("/assessment/plan", response_model=AssessmentPlanResponse)
def get_assessment_plan(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    dimension: Annotated[str | None, Query()] = None,
) -> AssessmentPlanResponse:
    return assessment_plan_service.get_plan(db, current_user.id, dimension=dimension)


@router.get("/mastery", response_model=UserMasteryResponse)
def get_my_mastery(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> UserMasteryResponse:
    return assessment_service.get_user_mastery(db, current_user.id)


@router.get("/skills/{slug}", response_model=UserSkillDetailResponse)
def get_my_skill_detail(
    slug: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> UserSkillDetailResponse:
    detail = assessment_service.get_user_skill_detail(db, current_user.id, slug)
    if detail is None:
        raise NotFoundError(detail="Skill not found", code="skill_not_found")
    return detail


@router.get("/history", response_model=AttemptListResponse)
def get_my_history(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = 20,
) -> AttemptListResponse:
    return attempt_service.list_attempts(db, current_user, cursor=cursor, limit=limit)


@router.get("/recommendations", response_model=RecommendationListResponse)
def get_my_recommendations(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
    target_skill: Annotated[str | None, Query(alias="target_skill")] = None,
    refresh: Annotated[bool, Query()] = False,
) -> RecommendationListResponse:
    return recommendation_service.get_recommendations(
        db,
        current_user.id,
        limit=limit,
        target_skill_slug=target_skill,
        refresh=refresh,
    )


@router.get("/recommendations/next", response_model=NextRecommendationResponse)
def get_next_recommendation(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    target_skill: Annotated[str | None, Query(alias="target_skill")] = None,
    refresh: Annotated[bool, Query()] = False,
) -> NextRecommendationResponse:
    return recommendation_service.get_next(
        db,
        current_user.id,
        target_skill_slug=target_skill,
        refresh=refresh,
    )


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationItem)
def get_recommendation_detail(
    recommendation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> RecommendationItem:
    detail = recommendation_service.get_recommendation_detail(
        db, current_user.id, recommendation_id
    )
    if detail is None:
        raise NotFoundError(detail="Recommendation not found", code="recommendation_not_found")
    return detail
