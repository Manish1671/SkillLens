from datetime import datetime

from app.core.enums import EvidencePolarity, MasteryStatus
from app.schemas.mastery_items import UserSkillMasteryItem
from app.schemas.recommendation import NextRecommendationResponse
from pydantic import BaseModel


class EvidenceSummary(BaseModel):
    id: str
    evidence_type: str
    polarity: EvidencePolarity
    strength: str
    summary_text: str
    skill_slug: str
    skill_name: str
    created_at: datetime


class SkillMasteryDelta(BaseModel):
    skill_slug: str
    skill_name: str
    previous_score: str | None
    new_score: str | None
    delta: str | None
    status: MasteryStatus
    confidence: str
    prerequisite_capped: bool = False


class SubmitAssessmentOutcome(BaseModel):
    evidence_items: list[EvidenceSummary]
    mastery_deltas: list[SkillMasteryDelta]
    recommendation: NextRecommendationResponse | None = None


class UserMasteryResponse(BaseModel):
    items: list[UserSkillMasteryItem]


class EvidenceTimelineItem(BaseModel):
    id: str
    evidence_type: str
    polarity: EvidencePolarity
    strength: str
    summary_text: str
    created_at: datetime
    attempt_id: str
    details: dict


class SnapshotItem(BaseModel):
    score: str
    confidence: str
    computed_at: datetime
    attempt_id: str


class UserSkillDetailResponse(BaseModel):
    slug: str
    name: str
    description: str
    topic_slug: str | None
    score: str | None
    confidence: str
    status: MasteryStatus
    evidence_count: int
    last_attempt_at: datetime | None
    prerequisites: list[UserSkillMasteryItem]
    dependents: list[UserSkillMasteryItem]
    evidence_timeline: list[EvidenceTimelineItem]
    snapshots: list[SnapshotItem]
