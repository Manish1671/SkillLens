"""Pure evidence generation rules — no framework or database imports."""

from dataclasses import dataclass, field
from typing import Any

from app.core.enums import Difficulty, EvidencePolarity, MistakeType

# Evidence type identifiers (V1)
SOLVED_WITHOUT_HINTS = "solved_without_hints"
SOLVED_WITH_HINTS = "solved_with_hints"
FAILED_ATTEMPT = "failed_attempt"
REPEATED_FAILURE = "repeated_failure"
HINT_RELIANCE = "hint_reliance"
PREREQUISITE_BLOCK = "prerequisite_block"
DIFFICULTY_MISMATCH = "difficulty_mismatch"

HINT_RELIANCE_THRESHOLD = 2
REPEATED_FAILURE_WINDOW = 3

BASE_SOLVED_STRENGTH = 0.72
BASE_FAILED_STRENGTH = 0.65
HINT_RELIANCE_STRENGTH = 0.45
REPEATED_FAILURE_STRENGTH = 0.55
DIFFICULTY_MISMATCH_STRENGTH = 0.35
PREREQUISITE_BLOCK_STRENGTH = 0.4

PRIMARY_WEIGHT_THRESHOLD = 1.0
SUPPORTING_WEIGHT_FACTOR = 0.55


@dataclass(frozen=True)
class ProblemSkillInput:
    skill_id: str
    skill_slug: str
    skill_name: str
    weight: float
    is_primary: bool


@dataclass(frozen=True)
class SubmissionContext:
    problem_id: str
    problem_slug: str
    problem_title: str
    difficulty: Difficulty
    is_correct: bool
    hints_used_count: int
    mistake_type: MistakeType | None
    time_spent_seconds: int | None


@dataclass(frozen=True)
class RecentFailureRecord:
    skill_id: str
    problem_id: str
    evidence_type: str


@dataclass(frozen=True)
class EvidenceDraft:
    skill_id: str
    evidence_type: str
    polarity: EvidencePolarity
    strength: float
    summary_text: str
    details: dict[str, Any] = field(default_factory=dict)


def _difficulty_label(difficulty: Difficulty) -> str:
    return difficulty.value.capitalize()


def _weight_factor(weight: float, is_primary: bool) -> float:
    if is_primary or weight >= PRIMARY_WEIGHT_THRESHOLD:
        return 1.0
    return max(0.2, weight) * SUPPORTING_WEIGHT_FACTOR


def _scaled_strength(base: float, weight_factor: float) -> float:
    return round(min(1.0, base * weight_factor), 4)


def _count_recent_failures(
    skill_id: str,
    problem_id: str,
    recent_failures: list[RecentFailureRecord],
) -> int:
    count = 0
    for record in recent_failures:
        if record.skill_id == skill_id and record.evidence_type == FAILED_ATTEMPT:
            count += 1
        if record.skill_id == skill_id and record.problem_id == problem_id:
            count += 1
    return count


def generate_evidence_drafts(
    submission: SubmissionContext,
    problem_skills: list[ProblemSkillInput],
    recent_failures: list[RecentFailureRecord],
    *,
    prerequisite_blocks: list[tuple[str, str, str, float]] | None = None,
) -> list[EvidenceDraft]:
    """Generate immutable evidence drafts for one submitted attempt."""
    drafts: list[EvidenceDraft] = []
    if not problem_skills:
        return drafts

    for link in problem_skills:
        weight_factor = _weight_factor(link.weight, link.is_primary)
        role = (
            "primary"
            if link.is_primary or link.weight >= PRIMARY_WEIGHT_THRESHOLD
            else "supporting"
        )

        if submission.is_correct:
            diff_label = _difficulty_label(submission.difficulty)
            if submission.hints_used_count == 0:
                evidence_type = SOLVED_WITHOUT_HINTS
                summary = (
                    f"Solved '{submission.problem_title}' ({diff_label}) "
                    f"without hints — {role} skill {link.skill_name}."
                )
            else:
                evidence_type = SOLVED_WITH_HINTS
                summary = (
                    f"Solved '{submission.problem_title}' ({diff_label}) "
                    f"with {submission.hints_used_count} hint(s) — {role} skill {link.skill_name}."
                )

            strength = _scaled_strength(BASE_SOLVED_STRENGTH, weight_factor)
            if submission.hints_used_count > 0:
                hint_factor = max(0.6, 1.0 - 0.12 * submission.hints_used_count)
                strength = round(strength * hint_factor, 4)

            drafts.append(
                EvidenceDraft(
                    skill_id=link.skill_id,
                    evidence_type=evidence_type,
                    polarity=EvidencePolarity.POSITIVE,
                    strength=strength,
                    summary_text=summary,
                    details={
                        "problem_id": submission.problem_id,
                        "problem_slug": submission.problem_slug,
                        "difficulty": submission.difficulty.value,
                        "hints_used_count": submission.hints_used_count,
                        "skill_weight": link.weight,
                        "is_primary": link.is_primary,
                    },
                )
            )

            if submission.hints_used_count >= HINT_RELIANCE_THRESHOLD:
                drafts.append(
                    EvidenceDraft(
                        skill_id=link.skill_id,
                        evidence_type=HINT_RELIANCE,
                        polarity=EvidencePolarity.NEGATIVE,
                        strength=_scaled_strength(HINT_RELIANCE_STRENGTH, weight_factor),
                        summary_text=(
                            f"Relied on {submission.hints_used_count} hints while solving "
                            f"'{submission.problem_title}' — {link.skill_name}."
                        ),
                        details={
                            "problem_id": submission.problem_id,
                            "hints_used_count": submission.hints_used_count,
                        },
                    )
                )

            if submission.difficulty == Difficulty.HARD:
                drafts.append(
                    EvidenceDraft(
                        skill_id=link.skill_id,
                        evidence_type=DIFFICULTY_MISMATCH,
                        polarity=EvidencePolarity.POSITIVE,
                        strength=_scaled_strength(DIFFICULTY_MISMATCH_STRENGTH, weight_factor),
                        summary_text=(
                            f"Solved a Hard problem '{submission.problem_title}' — "
                            f"strong signal for {link.skill_name}."
                        ),
                        details={
                            "problem_id": submission.problem_id,
                            "difficulty": submission.difficulty.value,
                            "direction": "solved_hard",
                        },
                    )
                )
        else:
            strength = _scaled_strength(BASE_FAILED_STRENGTH, weight_factor)
            mistake = submission.mistake_type.value if submission.mistake_type else "unknown"
            diff_label = _difficulty_label(submission.difficulty)
            drafts.append(
                EvidenceDraft(
                    skill_id=link.skill_id,
                    evidence_type=FAILED_ATTEMPT,
                    polarity=EvidencePolarity.NEGATIVE,
                    strength=strength,
                    summary_text=(
                        f"Failed '{submission.problem_title}' ({diff_label}) "
                        f"— {role} skill {link.skill_name}."
                    ),
                    details={
                        "problem_id": submission.problem_id,
                        "problem_slug": submission.problem_slug,
                        "difficulty": submission.difficulty.value,
                        "mistake_type": mistake,
                        "skill_weight": link.weight,
                    },
                )
            )

            failure_count = _count_recent_failures(
                link.skill_id, submission.problem_id, recent_failures
            )
            if failure_count >= 1:
                drafts.append(
                    EvidenceDraft(
                        skill_id=link.skill_id,
                        evidence_type=REPEATED_FAILURE,
                        polarity=EvidencePolarity.NEGATIVE,
                        strength=_scaled_strength(REPEATED_FAILURE_STRENGTH, weight_factor),
                        summary_text=(
                            f"Repeated failure on '{submission.problem_title}' "
                            f"for skill {link.skill_name}."
                        ),
                        details={
                            "problem_id": submission.problem_id,
                            "recent_failure_count": failure_count + 1,
                        },
                    )
                )

            if submission.difficulty == Difficulty.EASY:
                drafts.append(
                    EvidenceDraft(
                        skill_id=link.skill_id,
                        evidence_type=DIFFICULTY_MISMATCH,
                        polarity=EvidencePolarity.NEGATIVE,
                        strength=_scaled_strength(DIFFICULTY_MISMATCH_STRENGTH, weight_factor),
                        summary_text=(
                            f"Failed an Easy problem '{submission.problem_title}' — "
                            f"gap signal for {link.skill_name}."
                        ),
                        details={
                            "problem_id": submission.problem_id,
                            "difficulty": submission.difficulty.value,
                            "direction": "failed_easy",
                        },
                    )
                )

    if prerequisite_blocks:
        for skill_id, skill_name, prereq_name, prereq_score in prerequisite_blocks:
            drafts.append(
                EvidenceDraft(
                    skill_id=skill_id,
                    evidence_type=PREREQUISITE_BLOCK,
                    polarity=EvidencePolarity.NEUTRAL,
                    strength=PREREQUISITE_BLOCK_STRENGTH,
                    summary_text=(
                        f"Mastery for {skill_name} capped because prerequisite "
                        f"{prereq_name} is weak (score {prereq_score:.2f})."
                    ),
                    details={
                        "prerequisite_name": prereq_name,
                        "prerequisite_score": prereq_score,
                    },
                )
            )

    return drafts
