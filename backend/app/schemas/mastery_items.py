from datetime import datetime

from app.core.enums import MasteryStatus
from pydantic import BaseModel


class UserSkillMasteryItem(BaseModel):
    skill_slug: str
    skill_name: str
    topic_slug: str | None
    score: str | None
    confidence: str
    status: MasteryStatus
    evidence_count: int
    last_attempt_at: datetime | None
