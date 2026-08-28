from datetime import datetime

from app.core.enums import Difficulty
from app.schemas.catalog import ProblemSkillLink
from app.schemas.mastery_items import UserSkillMasteryItem
from pydantic import BaseModel


class RecommendationExplanation(BaseModel):
    target_skill: str
    reason_codes: list[str]
    score_components: dict[str, float]
    sentences: list[str]


class RecommendationProblemSummary(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    estimated_minutes: int
    skills: list[ProblemSkillLink]
    target_skill: ProblemSkillLink


class RecommendationItem(BaseModel):
    id: str
    rank: int
    score: str
    generated_at: datetime
    source_attempt_id: str | None
    problem: RecommendationProblemSummary
    explanation: RecommendationExplanation


class RecommendationListResponse(BaseModel):
    items: list[RecommendationItem]
    target_skill: UserSkillMasteryItem | None
    state: str
    message: str | None = None


class NextRecommendationResponse(BaseModel):
    recommendation: RecommendationItem | None
    target_skill: UserSkillMasteryItem | None
    state: str
    message: str | None = None
