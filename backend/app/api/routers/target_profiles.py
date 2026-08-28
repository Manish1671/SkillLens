from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.services import readiness_service
from app.schemas.readiness import TargetProfileListResponse

router = APIRouter(prefix="/target-profiles", tags=["readiness"])


@router.get("", response_model=TargetProfileListResponse)
def list_target_profiles(db: Annotated[Session, Depends(get_db)]) -> TargetProfileListResponse:
    return readiness_service.list_profiles(db)
