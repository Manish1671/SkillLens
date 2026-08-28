from decimal import Decimal

from app.core.enums import ActivityKind, Difficulty
from pydantic import BaseModel, Field


class TopicSummary(BaseModel):
    slug: str
    name: str
    sort_order: int


class SkillSummary(BaseModel):
    slug: str
    name: str
    description: str
    topic_slug: str | None
    is_foundational: bool
    sort_order: int
    prerequisite_skill_ids: list[str] = Field(default_factory=list)


class QuizOptionPublic(BaseModel):
    id: str
    label: str


class SkillProblemSummary(BaseModel):
    slug: str
    title: str
    difficulty: Difficulty
    estimated_minutes: int
    activity_kind: ActivityKind = ActivityKind.CODING


class SkillDetailResponse(BaseModel):
    slug: str
    name: str
    description: str
    topic_slug: str | None
    is_foundational: bool
    sort_order: int
    prerequisites: list[SkillSummary]
    dependents: list[SkillSummary]
    linked_problems: list[SkillProblemSummary]


class ProblemSkillLink(BaseModel):
    slug: str
    name: str
    weight: Decimal
    is_primary: bool


class LearnerProblemState(BaseModel):
    attempted: bool
    solved: bool
    in_progress: bool


class ProblemListItem(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    estimated_minutes: int
    activity_kind: ActivityKind = ActivityKind.CODING
    topic: TopicSummary
    skills: list[ProblemSkillLink]
    learner_state: LearnerProblemState | None = None


class ProblemListResponse(BaseModel):
    items: list[ProblemListItem]
    next_cursor: str | None
    has_more: bool


class ProblemDetailResponse(BaseModel):
    id: str
    slug: str
    title: str
    prompt_md: str
    difficulty: Difficulty
    estimated_minutes: int
    activity_kind: ActivityKind = ActivityKind.CODING
    topic: TopicSummary
    skills: list[ProblemSkillLink]
    hint_count: int
    options: list[QuizOptionPublic] | None = None
    learner_state: LearnerProblemState | None = None
