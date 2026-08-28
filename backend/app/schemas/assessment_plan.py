from app.core.enums import ActivityKind, Difficulty, ReadinessDimension
from pydantic import BaseModel, Field


class AssessmentPlanTarget(BaseModel):
    slug: str
    name: str


class AssessmentPlanItemResponse(BaseModel):
    position: int
    activity_kind: ActivityKind
    problem_slug: str
    problem_title: str
    dimension: ReadinessDimension
    skill_slug: str
    skill_name: str
    estimated_minutes: int
    difficulty: Difficulty


class AssessmentPlanResponse(BaseModel):
    assessment_id: str | None
    state: str
    message: str | None = None
    target: AssessmentPlanTarget | None
    total_items: int = 0
    items: list[AssessmentPlanItemResponse] = Field(default_factory=list)
