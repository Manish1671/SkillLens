from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.enums import ActivityKind, AttemptEventType, AttemptStatus, Difficulty, MistakeType
from app.schemas.assessment import SubmitAssessmentOutcome
from app.schemas.catalog import QuizOptionPublic
from pydantic import BaseModel, Field, field_validator


class StartAttemptRequest(BaseModel):
    problem_id: UUID
    client_attempt_id: str = Field(min_length=1, max_length=64)


class SubmitAttemptRequest(BaseModel):
    is_correct: bool | None = None
    time_spent_seconds: int = Field(ge=0)
    mistake_type: MistakeType | None = None
    code_text: str | None = None
    selected_option: str | None = Field(default=None, max_length=64)

    @field_validator("code_text")
    @classmethod
    def strip_code_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("selected_option")
    @classmethod
    def strip_selected_option(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class RecordAttemptEventRequest(BaseModel):
    event_type: AttemptEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class AttemptProblemSummary(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    activity_kind: ActivityKind = ActivityKind.CODING


class AttemptProblemDetail(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: Difficulty
    prompt_md: str
    hint_count: int
    activity_kind: ActivityKind = ActivityKind.CODING
    options: list[QuizOptionPublic] | None = None


class AttemptHintMeta(BaseModel):
    id: str
    ordinal: int


class AttemptResponse(BaseModel):
    id: str
    problem_id: str
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    time_spent_seconds: int | None
    hints_used_count: int
    is_correct: bool | None
    mistake_type: MistakeType | None
    code_text: str | None
    client_attempt_id: str


class AttemptListItem(BaseModel):
    id: str
    problem: AttemptProblemSummary
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    time_spent_seconds: int | None
    hints_used_count: int
    is_correct: bool | None
    mistake_type: MistakeType | None


class AttemptListResponse(BaseModel):
    items: list[AttemptListItem]
    next_cursor: str | None
    has_more: bool


class AttemptEventResponse(BaseModel):
    id: str
    event_type: AttemptEventType
    payload: dict[str, Any]
    occurred_at: datetime
    hint_body_md: str | None = None


class AttemptDetailResponse(BaseModel):
    attempt: AttemptResponse
    problem: AttemptProblemDetail
    events: list[AttemptEventResponse]
    available_hints: list[AttemptHintMeta]


class SubmitAttemptResponse(AttemptResponse):
    assessment: SubmitAssessmentOutcome | None = None
