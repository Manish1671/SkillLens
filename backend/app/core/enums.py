import enum

from sqlalchemy import Enum as SAEnum


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ActivityKind(str, enum.Enum):
    CODING = "coding"
    QUIZ = "quiz"


class ActivityKindQuery(str, enum.Enum):
    CODING = "coding"
    QUIZ = "quiz"
    ALL = "all"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"


class MistakeType(str, enum.Enum):
    OFF_BY_ONE = "off_by_one"
    WRONG_DATA_STRUCTURE = "wrong_data_structure"
    MISSED_EDGE_CASE = "missed_edge_case"
    INCORRECT_COMPLEXITY = "incorrect_complexity"
    LOGIC_ERROR = "logic_error"
    UNKNOWN = "unknown"


class EvidencePolarity(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class MasteryStatus(str, enum.Enum):
    INSUFFICIENT = "insufficient"
    ASSESSED = "assessed"


class ReadinessDimension(str, enum.Enum):
    DSA = "dsa"
    CORE_CS = "core_cs"
    PROJECTS = "projects"
    INTERVIEW = "interview"
    PROFILE = "profile"


class DimensionStatus(str, enum.Enum):
    NOT_ASSESSED = "not_assessed"
    EARLY = "early"
    DEVELOPING = "developing"
    NEAR_READY = "near_ready"
    READY = "ready"


class PlacementState(str, enum.Enum):
    NOT_ASSESSED = "not_assessed"
    EARLY = "early"
    DEVELOPING = "developing"
    NEAR_READY = "near_ready"
    READY = "ready"


class GapRequirementStatus(str, enum.Enum):
    EXCEEDS = "exceeds"
    MEETS = "meets"
    BELOW = "below"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class GapSeverity(str, enum.Enum):
    CRITICAL_BLOCKER = "critical_blocker"
    SECONDARY = "secondary"
    WATCH = "watch"


class PlacementRisk(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlacementActionKind(str, enum.Enum):
    DSA_PROBLEM = "dsa_problem"
    CS_QUIZ = "cs_quiz"
    ASSESS_DIMENSION = "assess_dimension"


class AttemptEventType(str, enum.Enum):
    STARTED = "started"
    HINT_REVEALED = "hint_revealed"
    SELF_REPORT = "self_report"
    SUBMITTED = "submitted"
    ABANDONED = "abandoned"


def pg_enum(enum_class: type[enum.Enum], name: str) -> SAEnum:
    """PostgreSQL native enum mapped to lowercase string values in app.core.enums."""
    return SAEnum(
        enum_class,
        name=name,
        native_enum=True,
        create_constraint=True,
        values_callable=lambda _enum: [member.value for member in enum_class],
    )
