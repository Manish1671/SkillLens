from datetime import datetime

from app.core.enums import PlacementActionKind, ReadinessDimension
from pydantic import BaseModel, Field


class PlacementActionSkill(BaseModel):
    slug: str
    name: str


class PlacementActionItem(BaseModel):
    id: str
    action_kind: PlacementActionKind
    title: str
    description: str
    target_dimension: ReadinessDimension
    target_skill: PlacementActionSkill | None
    estimated_effort_minutes: int
    score: str
    rank: int
    why: list[str]
    reason_codes: list[str]
    payload: dict = Field(default_factory=dict)
    generated_at: datetime


class NextPlacementActionResponse(BaseModel):
    action: PlacementActionItem | None
    state: str
    message: str | None = None


class PlacementActionListResponse(BaseModel):
    items: list[PlacementActionItem]
    state: str
    message: str | None = None
