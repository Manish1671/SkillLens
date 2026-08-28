"""Pure deterministic mastery calculation — no framework or database imports."""

from dataclasses import dataclass
from datetime import datetime
from math import pow

from app.core.enums import EvidencePolarity, MasteryStatus

# Recency: 21-day half-life per approved architecture
HALF_LIFE_DAYS = 21

# Cold start: minimum effective weighted evidence before showing a score
EFFECTIVE_EVIDENCE_THRESHOLD = 1.5

# Prior stabilization — prevents one lucky attempt → near-perfect mastery
PRIOR_SCORE = 0.35
PRIOR_WEIGHT = 1.25

# Score bounds
SCORE_MIN = 0.0
SCORE_MAX = 1.0

# Confidence scaling
CONFIDENCE_SCALE = 4.0
INCONSISTENCY_PENALTY = 0.35

# Prerequisite cap: weak prerequisite limits dependent displayed mastery
PREREQUISITE_WEAK_THRESHOLD = 0.45

# Difficulty multipliers for signed credit (used when computing from attempt context)
DIFFICULTY_POSITIVE_MULT = {
    "easy": 0.88,
    "medium": 1.0,
    "hard": 1.12,
}
DIFFICULTY_NEGATIVE_MULT = {
    "easy": 1.12,
    "medium": 1.0,
    "hard": 0.88,
}

MAX_TIME_BONUS_SECONDS = 600
TIME_BONUS_CAP = 0.05


@dataclass(frozen=True)
class EvidenceInput:
    polarity: EvidencePolarity
    strength: float
    created_at: datetime
    evidence_type: str


@dataclass(frozen=True)
class MasteryResult:
    score: float
    confidence: float
    effective_evidence: float
    status: MasteryStatus
    raw_score: float
    capped_score: float
    prerequisite_capped: bool


def recency_weight(created_at: datetime, reference: datetime) -> float:
    age_days = max(0.0, (reference - created_at).total_seconds() / 86400.0)
    return pow(2.0, -age_days / HALF_LIFE_DAYS)


def _polarity_sign(polarity: EvidencePolarity) -> float:
    if polarity == EvidencePolarity.POSITIVE:
        return 1.0
    if polarity == EvidencePolarity.NEGATIVE:
        return -1.0
    return 0.0


def _clamp(value: float, low: float = SCORE_MIN, high: float = SCORE_MAX) -> float:
    return max(low, min(high, value))


def compute_effective_evidence(evidence_items: list[EvidenceInput], reference: datetime) -> float:
    total = 0.0
    for item in evidence_items:
        weight = recency_weight(item.created_at, reference)
        total += abs(item.strength) * weight
    return total


def compute_confidence(evidence_items: list[EvidenceInput], reference: datetime) -> float:
    if not evidence_items:
        return 0.0

    effective = compute_effective_evidence(evidence_items, reference)
    base = _clamp(effective / CONFIDENCE_SCALE)

    recent = sorted(evidence_items, key=lambda item: item.created_at, reverse=True)[:5]
    positives = sum(1 for item in recent if item.polarity == EvidencePolarity.POSITIVE)
    negatives = sum(1 for item in recent if item.polarity == EvidencePolarity.NEGATIVE)
    if positives > 0 and negatives > 0:
        inconsistency = min(positives, negatives) / len(recent)
        base *= 1.0 - INCONSISTENCY_PENALTY * inconsistency

    return round(_clamp(base), 4)


def compute_raw_score(evidence_items: list[EvidenceInput], reference: datetime) -> float:
    if not evidence_items:
        return PRIOR_SCORE

    weighted_sum = 0.0
    weight_total = 0.0
    for item in evidence_items:
        recency = recency_weight(item.created_at, reference)
        magnitude = abs(item.strength) * recency
        signed = item.strength * _polarity_sign(item.polarity) * recency
        weighted_sum += signed
        weight_total += magnitude

    denominator = weight_total + PRIOR_WEIGHT
    score = (weighted_sum + PRIOR_WEIGHT * PRIOR_SCORE) / denominator
    return round(_clamp(score), 4)


def apply_prerequisite_cap(
    score: float,
    prerequisite_scores: list[float],
) -> tuple[float, bool]:
    if not prerequisite_scores:
        return score, False

    weak_prereqs = [value for value in prerequisite_scores if value < PREREQUISITE_WEAK_THRESHOLD]
    if not weak_prereqs:
        return score, False

    cap = min(weak_prereqs)
    capped = min(score, cap)
    return round(capped, 4), capped < score


def compute_mastery(
    evidence_items: list[EvidenceInput],
    reference: datetime,
    prerequisite_scores: list[float] | None = None,
) -> MasteryResult:
    effective = compute_effective_evidence(evidence_items, reference)
    raw_score = compute_raw_score(evidence_items, reference)
    capped_score, was_capped = apply_prerequisite_cap(raw_score, prerequisite_scores or [])
    confidence = compute_confidence(evidence_items, reference)

    status = (
        MasteryStatus.ASSESSED
        if effective >= EFFECTIVE_EVIDENCE_THRESHOLD
        else MasteryStatus.INSUFFICIENT
    )

    display_score = capped_score if status == MasteryStatus.ASSESSED else raw_score
    if status == MasteryStatus.INSUFFICIENT:
        display_score = raw_score

    return MasteryResult(
        score=round(display_score, 4),
        confidence=confidence,
        effective_evidence=round(effective, 4),
        status=status,
        raw_score=raw_score,
        capped_score=capped_score,
        prerequisite_capped=was_capped,
    )


def compute_attempt_credit(
    is_correct: bool,
    difficulty: str,
    skill_weight: float,
    hints_used_count: int,
    time_spent_seconds: int | None,
) -> float:
    """Signed per-attempt credit used for documentation and optional diagnostics."""
    weight_factor = 1.0 if skill_weight >= 1.0 else max(0.2, skill_weight) * 0.55
    if is_correct:
        mult = DIFFICULTY_POSITIVE_MULT.get(difficulty, 1.0)
        credit = 0.7 * mult * weight_factor
        if hints_used_count > 0:
            credit *= max(0.6, 1.0 - 0.12 * hints_used_count)
    else:
        mult = DIFFICULTY_NEGATIVE_MULT.get(difficulty, 1.0)
        credit = -0.65 * mult * weight_factor

    if time_spent_seconds is not None and is_correct:
        time_bonus = min(
            TIME_BONUS_CAP, time_spent_seconds / MAX_TIME_BONUS_SECONDS * TIME_BONUS_CAP
        )
        credit += time_bonus

    return round(_clamp(credit, -1.0, 1.0), 4)
