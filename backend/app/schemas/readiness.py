from datetime import datetime

from app.core.enums import (
    DimensionStatus,
    GapRequirementStatus,
    GapSeverity,
    PlacementRisk,
    PlacementState,
    ReadinessDimension,
)
from app.domain.readiness import READINESS_RISK_DISCLAIMER, TARGET_PROFILE_DISCLAIMER
from pydantic import BaseModel, Field


class TargetProfileSummary(BaseModel):
    slug: str
    name: str
    description: str
    disclaimer: str = TARGET_PROFILE_DISCLAIMER


class TargetProfileListResponse(BaseModel):
    items: list[TargetProfileSummary]
    disclaimer: str = TARGET_PROFILE_DISCLAIMER


class LearnerTargetResponse(BaseModel):
    profile: TargetProfileSummary | None
    selected_at: datetime | None
    disclaimer: str = TARGET_PROFILE_DISCLAIMER


class SetLearnerTargetRequest(BaseModel):
    profile_slug: str = Field(min_length=1, max_length=80)


class SkillHighlightResponse(BaseModel):
    skill_slug: str
    skill_name: str
    score: float


class DimensionReadinessResponse(BaseModel):
    key: ReadinessDimension
    display_name: str
    status: DimensionStatus
    score: float | None
    confidence: float | None
    coverage: float
    assessed_count: int
    in_scope_count: int
    strongest_skills: list[SkillHighlightResponse] = Field(default_factory=list)
    weakest_actionable_skill: SkillHighlightResponse | None = None
    target_min_score: float | None = None
    requirement_status: GapRequirementStatus | None = None


class BlockerResponse(BaseModel):
    dimension: ReadinessDimension
    skill_slug: str | None
    skill_name: str | None
    current: float | None
    required: float
    delta: float | None
    status: GapRequirementStatus
    severity: GapSeverity
    why: str
    rank: int
    is_critical: bool = False


class GapListResponse(BaseModel):
    items: list[BlockerResponse] = Field(default_factory=list)
    disclaimer: str = TARGET_PROFILE_DISCLAIMER


class PlacementReadinessResponse(BaseModel):
    target: TargetProfileSummary | None
    state: PlacementState
    confidence: float | None
    risk: PlacementRisk
    dimensions: list[DimensionReadinessResponse]
    blockers: list[BlockerResponse]
    score: float | None = None
    disclaimer: str = TARGET_PROFILE_DISCLAIMER
    explanation: list[str] = Field(default_factory=list)
    risk_disclaimer: str = READINESS_RISK_DISCLAIMER
