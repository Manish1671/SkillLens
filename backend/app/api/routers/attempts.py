from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.services import attempt_service
from app.schemas.attempt import (
    AttemptDetailResponse,
    AttemptEventResponse,
    AttemptListResponse,
    AttemptResponse,
    RecordAttemptEventRequest,
    StartAttemptRequest,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
)

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("", response_model=AttemptResponse, status_code=201)
def start_attempt(
    payload: StartAttemptRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> AttemptResponse:
    return attempt_service.start_attempt(db, current_user, payload)


@router.get("", response_model=AttemptListResponse)
def list_attempts(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    cursor: Annotated[str | None, Query(description="Pagination cursor (attempt id)")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AttemptListResponse:
    return attempt_service.list_attempts(db, current_user, cursor=cursor, limit=limit)


@router.get("/{attempt_id}", response_model=AttemptDetailResponse)
def get_attempt(
    attempt_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> AttemptDetailResponse:
    return attempt_service.get_attempt_detail(db, current_user, attempt_id)


@router.post("/{attempt_id}/events", response_model=AttemptEventResponse)
def record_event(
    attempt_id: UUID,
    payload: RecordAttemptEventRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> AttemptEventResponse:
    return attempt_service.record_event(db, current_user, attempt_id, payload)


@router.post("/{attempt_id}/submit", response_model=SubmitAttemptResponse)
def submit_attempt(
    attempt_id: UUID,
    payload: SubmitAttemptRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> SubmitAttemptResponse:
    return attempt_service.submit_attempt(db, current_user, attempt_id, payload)


@router.post("/{attempt_id}/abandon", response_model=AttemptResponse)
def abandon_attempt(
    attempt_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
) -> AttemptResponse:
    return attempt_service.abandon_attempt(db, current_user, attempt_id)
