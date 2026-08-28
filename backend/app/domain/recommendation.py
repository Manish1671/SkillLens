"""Pure deterministic recommendation scoring — no framework or database imports."""

from dataclasses import dataclass, field
from datetime import datetime

from app.core.enums import Difficulty, MasteryStatus

# Prerequisite readiness — aligned with domain/mastery.py
PREREQUISITE_READY_THRESHOLD = 0.45

# Difficulty adaptation thresholds
CONFIDENCE_LOW_THRESHOLD = 0.30
MASTERY_VERY_WEAK_THRESHOLD = 0.45
MASTERY_MODERATE_THRESHOLD = 0.65
MASTERY_STRONG_THRESHOLD = 0.75

# Novelty scores (0–1)
NOVELTY_NEVER_ATTEMPTED = 1.0
NOVELTY_ATTEMPTED_UNSOLVED = 0.65
NOVELTY_SOLVED_RECENT = 0.12
NOVELTY_SOLVED_REVIEW = 0.40

# Spacing windows (days)
SPACING_RECENT_DAYS = 7
SPACING_MEDIUM_DAYS = 21
REVIEW_ELIGIBLE_DAYS = 30

# Component weights for final candidate score
WEIGHT_WEAKNESS = 0.25
WEIGHT_SKILL_MATCH = 0.20
WEIGHT_PREREQUISITE = 0.15
WEIGHT_DIFFICULTY = 0.20
WEIGHT_NOVELTY = 0.12
WEIGHT_SPACING = 0.08

# Primary vs supporting skill relevance
PRIMARY_WEIGHT_THRESHOLD = 1.0
SUPPORTING_WEIGHT_FACTOR = 0.55

# Staleness — recommendations older than this may be regenerated
RECOMMENDATION_STALE_HOURS = 24

# Cold-start: foundational skills tried in sort order
COLD_START_FOUNDATIONAL_SLUGS = ("arrays", "linked-lists", "trees")

# Reason codes
REASON_WEAK_SKILL = "weak_skill"
REASON_COLD_START = "cold_start"
REASON_PREREQUISITE_READY = "prerequisite_ready"
REASON_PREREQUISITE_BLOCKED = "prerequisite_blocked"
REASON_DIFFICULTY_FIT = "difficulty_fit"
REASON_NOVEL_PROBLEM = "novel_problem"
REASON_SPACED_REVIEW = "spaced_review"
REASON_PRIMARY_SKILL = "primary_skill"
REASON_SUPPORTING_SKILL = "supporting_skill"

# No-candidate states
STATE_OK = "ok"
STATE_COLD_START = "cold_start"
STATE_NO_ELIGIBLE_PROBLEM = "no_eligible_problem"
STATE_PREREQUISITE_BLOCKED = "all_candidates_blocked"
STATE_NO_WEAK_SKILL = "no_weak_skill"
STATE_REVIEW_NEEDED = "review_needed"


@dataclass(frozen=True)
class SkillMasteryInput:
    skill_id: str
    skill_slug: str
    skill_name: str
    is_foundational: bool
    sort_order: int
    score: float | None
    confidence: float
    status: MasteryStatus
    problem_count: int


@dataclass(frozen=True)
class PrerequisiteInput:
    prerequisite_skill_id: str
    prerequisite_slug: str
    prerequisite_name: str
    score: float | None
    status: MasteryStatus


@dataclass(frozen=True)
class CandidateProblemInput:
    problem_id: str
    problem_slug: str
    title: str
    difficulty: Difficulty
    estimated_minutes: int
    target_skill_weight: float
    is_primary_for_target: bool
    attempted: bool
    solved: bool
    in_progress: bool
    last_success_at: datetime | None
    reference: datetime


@dataclass(frozen=True)
class ScoreComponents:
    skill_match: float
    weakness: float
    prerequisite_ready: float
    difficulty_fit: float
    novelty: float
    spacing: float
    final_score: float


@dataclass(frozen=True)
class ScoredCandidate:
    problem_id: str
    problem_slug: str
    title: str
    difficulty: Difficulty
    estimated_minutes: int
    target_skill_id: str
    target_skill_slug: str
    target_skill_name: str
    components: ScoreComponents
    reason_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TargetSkillSelection:
    skill_id: str
    skill_slug: str
    skill_name: str
    score: float | None
    confidence: float
    status: MasteryStatus
    selection_reason: str


def _days_between(earlier: datetime, later: datetime) -> float:
    return max(0.0, (later - earlier).total_seconds() / 86400.0)


def evaluate_prerequisite_readiness(
    prerequisites: list[PrerequisiteInput],
) -> tuple[float, bool, list[str]]:
    """Return readiness score (0–1), whether eligible, and reason codes."""
    if not prerequisites:
        return 1.0, True, [REASON_PREREQUISITE_READY]

    readiness_values: list[float] = []
    for prereq in prerequisites:
        if prereq.status != MasteryStatus.ASSESSED or prereq.score is None:
            return 0.0, False, [REASON_PREREQUISITE_BLOCKED]
        if prereq.score < PREREQUISITE_READY_THRESHOLD:
            return 0.0, False, [REASON_PREREQUISITE_BLOCKED]
        readiness_values.append(min(1.0, prereq.score / PREREQUISITE_READY_THRESHOLD))

    avg = sum(readiness_values) / len(readiness_values)
    return round(avg, 4), True, [REASON_PREREQUISITE_READY]


def difficulty_fit_score(
    skill_score: float | None,
    skill_confidence: float,
    skill_status: MasteryStatus,
    difficulty: Difficulty,
) -> float:
    """How well problem difficulty matches learner readiness (0–1)."""
    if skill_status != MasteryStatus.ASSESSED or skill_score is None:
        if difficulty == Difficulty.EASY:
            return 1.0
        if difficulty == Difficulty.MEDIUM:
            return 0.35
        return 0.1

    if skill_confidence < CONFIDENCE_LOW_THRESHOLD:
        return {Difficulty.EASY: 1.0, Difficulty.MEDIUM: 0.4, Difficulty.HARD: 0.1}[difficulty]

    if skill_score < MASTERY_VERY_WEAK_THRESHOLD:
        return {Difficulty.EASY: 1.0, Difficulty.MEDIUM: 0.55, Difficulty.HARD: 0.15}[difficulty]

    if skill_score < MASTERY_MODERATE_THRESHOLD:
        return {Difficulty.EASY: 0.85, Difficulty.MEDIUM: 1.0, Difficulty.HARD: 0.35}[difficulty]

    if skill_score < MASTERY_STRONG_THRESHOLD:
        return {Difficulty.EASY: 0.5, Difficulty.MEDIUM: 0.95, Difficulty.HARD: 0.7}[difficulty]

    return {Difficulty.EASY: 0.35, Difficulty.MEDIUM: 0.8, Difficulty.HARD: 1.0}[difficulty]


def novelty_score(candidate: CandidateProblemInput) -> float:
    if candidate.in_progress:
        return 0.0
    if not candidate.attempted:
        return NOVELTY_NEVER_ATTEMPTED
    if not candidate.solved:
        return NOVELTY_ATTEMPTED_UNSOLVED
    if candidate.last_success_at is None:
        return NOVELTY_SOLVED_RECENT
    days = _days_between(candidate.last_success_at, candidate.reference)
    if days < SPACING_RECENT_DAYS:
        return NOVELTY_SOLVED_RECENT
    if days >= REVIEW_ELIGIBLE_DAYS:
        return NOVELTY_SOLVED_REVIEW
    return NOVELTY_SOLVED_RECENT + (days / REVIEW_ELIGIBLE_DAYS) * (
        NOVELTY_SOLVED_REVIEW - NOVELTY_SOLVED_RECENT
    )


def spacing_score(candidate: CandidateProblemInput) -> float:
    if not candidate.solved or candidate.last_success_at is None:
        return 1.0
    days = _days_between(candidate.last_success_at, candidate.reference)
    if days < SPACING_RECENT_DAYS:
        return 0.2
    if days < SPACING_MEDIUM_DAYS:
        return 0.5
    if days >= REVIEW_ELIGIBLE_DAYS:
        return 0.85
    return 0.5 + (days - SPACING_MEDIUM_DAYS) / (REVIEW_ELIGIBLE_DAYS - SPACING_MEDIUM_DAYS) * 0.35


def skill_match_score(weight: float, is_primary: bool) -> float:
    if is_primary or weight >= PRIMARY_WEIGHT_THRESHOLD:
        return 1.0
    return max(0.2, weight) * SUPPORTING_WEIGHT_FACTOR


def weakness_score(skill_score: float | None, skill_status: MasteryStatus) -> float:
    if skill_status != MasteryStatus.ASSESSED or skill_score is None:
        return 0.85
    return round(1.0 - skill_score, 4)


def select_target_skill(
    skills: list[SkillMasteryInput],
    *,
    explicit_skill_slug: str | None = None,
) -> TargetSkillSelection | None:
    """Pick the highest-priority skill to target for recommendations."""
    if not skills:
        return None

    if explicit_skill_slug:
        for skill in skills:
            if skill.skill_slug == explicit_skill_slug and skill.problem_count > 0:
                return TargetSkillSelection(
                    skill_id=skill.skill_id,
                    skill_slug=skill.skill_slug,
                    skill_name=skill.skill_name,
                    score=skill.score,
                    confidence=skill.confidence,
                    status=skill.status,
                    selection_reason=REASON_WEAK_SKILL,
                )
        return None

    assessed = [s for s in skills if s.status == MasteryStatus.ASSESSED and s.problem_count > 0]
    if assessed:
        assessed.sort(
            key=lambda s: (s.score if s.score is not None else 1.0, s.sort_order, s.skill_slug)
        )
        weakest = assessed[0]
        return TargetSkillSelection(
            skill_id=weakest.skill_id,
            skill_slug=weakest.skill_slug,
            skill_name=weakest.skill_name,
            score=weakest.score,
            confidence=weakest.confidence,
            status=weakest.status,
            selection_reason=REASON_WEAK_SKILL,
        )

    # Cold start — no assessed skills with problems
    foundational = [
        s
        for s in skills
        if s.is_foundational
        and s.problem_count > 0
        and s.skill_slug in COLD_START_FOUNDATIONAL_SLUGS
    ]
    foundational.sort(
        key=lambda s: (COLD_START_FOUNDATIONAL_SLUGS.index(s.skill_slug), s.sort_order)
    )
    if foundational:
        chosen = foundational[0]
        return TargetSkillSelection(
            skill_id=chosen.skill_id,
            skill_slug=chosen.skill_slug,
            skill_name=chosen.skill_name,
            score=chosen.score,
            confidence=chosen.confidence,
            status=chosen.status,
            selection_reason=REASON_COLD_START,
        )

    with_problems = [s for s in skills if s.problem_count > 0]
    if not with_problems:
        return None
    with_problems.sort(key=lambda s: (s.sort_order, s.skill_slug))
    chosen = with_problems[0]
    return TargetSkillSelection(
        skill_id=chosen.skill_id,
        skill_slug=chosen.skill_slug,
        skill_name=chosen.skill_name,
        score=chosen.score,
        confidence=chosen.confidence,
        status=chosen.status,
        selection_reason=REASON_COLD_START,
    )


def score_candidate(
    candidate: CandidateProblemInput,
    target: TargetSkillSelection,
    prerequisite_readiness: float,
    prerequisites_eligible: bool,
) -> ScoredCandidate | None:
    if candidate.in_progress:
        return None
    if not prerequisites_eligible:
        return None

    weakness = weakness_score(target.score, target.status)
    skill_match = skill_match_score(candidate.target_skill_weight, candidate.is_primary_for_target)
    diff_fit = difficulty_fit_score(
        target.score, target.confidence, target.status, candidate.difficulty
    )
    novelty = novelty_score(candidate)
    spacing = spacing_score(candidate)

    if novelty <= 0.0:
        return None

    final = round(
        WEIGHT_WEAKNESS * weakness
        + WEIGHT_SKILL_MATCH * skill_match
        + WEIGHT_PREREQUISITE * prerequisite_readiness
        + WEIGHT_DIFFICULTY * diff_fit
        + WEIGHT_NOVELTY * novelty
        + WEIGHT_SPACING * spacing,
        4,
    )

    reason_codes: list[str] = []
    if target.selection_reason == REASON_COLD_START:
        reason_codes.append(REASON_COLD_START)
    else:
        reason_codes.append(REASON_WEAK_SKILL)
    reason_codes.append(REASON_PREREQUISITE_READY)
    if diff_fit >= 0.7:
        reason_codes.append(REASON_DIFFICULTY_FIT)
    if novelty >= NOVELTY_NEVER_ATTEMPTED - 0.01:
        reason_codes.append(REASON_NOVEL_PROBLEM)
    elif spacing >= 0.8:
        reason_codes.append(REASON_SPACED_REVIEW)
    if candidate.is_primary_for_target:
        reason_codes.append(REASON_PRIMARY_SKILL)
    else:
        reason_codes.append(REASON_SUPPORTING_SKILL)

    components = ScoreComponents(
        skill_match=round(skill_match, 4),
        weakness=round(weakness, 4),
        prerequisite_ready=round(prerequisite_readiness, 4),
        difficulty_fit=round(diff_fit, 4),
        novelty=round(novelty, 4),
        spacing=round(spacing, 4),
        final_score=final,
    )

    return ScoredCandidate(
        problem_id=candidate.problem_id,
        problem_slug=candidate.problem_slug,
        title=candidate.title,
        difficulty=candidate.difficulty,
        estimated_minutes=candidate.estimated_minutes,
        target_skill_id=target.skill_id,
        target_skill_slug=target.skill_slug,
        target_skill_name=target.skill_name,
        components=components,
        reason_codes=reason_codes,
    )


def rank_candidates(candidates: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Deterministic ordering with explicit tie-breakers."""

    def sort_key(item: ScoredCandidate) -> tuple:
        return (
            -item.components.final_score,
            -item.components.skill_match,
            -item.components.prerequisite_ready,
            -item.components.difficulty_fit,
            -item.components.novelty,
            item.components.spacing,
            item.problem_slug,
        )

    return sorted(candidates, key=sort_key)


def generate_explanation_sentences(
    target: TargetSkillSelection,
    candidate: ScoredCandidate,
    prerequisites: list[PrerequisiteInput],
) -> list[str]:
    sentences: list[str] = []

    if target.selection_reason == REASON_COLD_START:
        sentences.append(
            f"You are getting started — {target.skill_name} is a foundational skill "
            "with approachable problems."
        )
    elif target.score is not None:
        pct = int(target.score * 100)
        sentences.append(
            f"Your {target.skill_name} skill is currently one of your weaker assessed "
            f"skills ({pct}% mastery)."
        )
    else:
        sentences.append(
            f"{target.skill_name} needs more practice — this problem helps build evidence."
        )

    if prerequisites:
        ready_names = [
            p.prerequisite_name
            for p in prerequisites
            if p.status == MasteryStatus.ASSESSED
            and p.score is not None
            and p.score >= PREREQUISITE_READY_THRESHOLD
        ]
        if ready_names:
            if len(ready_names) == 1:
                sentences.append(
                    f"Your {ready_names[0]} prerequisite is strong enough for this problem."
                )
            else:
                sentences.append(
                    f"Prerequisites ({', '.join(ready_names)}) are ready for this problem."
                )
    else:
        sentences.append(f"{target.skill_name} has no direct prerequisites blocking this problem.")

    diff_label = candidate.difficulty.value.capitalize()
    if candidate.components.difficulty_fit >= 0.7:
        sentences.append(f"This {diff_label} problem matches your current difficulty level.")
    else:
        sentences.append(
            f"This {diff_label} problem is within reach for building {target.skill_name}."
        )

    if REASON_NOVEL_PROBLEM in candidate.reason_codes:
        sentences.append("You have not solved this problem before.")
    elif REASON_SPACED_REVIEW in candidate.reason_codes:
        sentences.append("Enough time has passed since your last success — good for spaced review.")
    elif candidate.components.novelty >= NOVELTY_ATTEMPTED_UNSOLVED - 0.01:
        sentences.append("You attempted this before but have not solved it yet.")

    return sentences


def build_explanation_payload(
    target: TargetSkillSelection,
    candidate: ScoredCandidate,
    prerequisites: list[PrerequisiteInput],
) -> dict:
    return {
        "target_skill": target.skill_slug,
        "reason_codes": candidate.reason_codes,
        "score_components": {
            "weakness": candidate.components.weakness,
            "skill_match": candidate.components.skill_match,
            "prerequisite_ready": candidate.components.prerequisite_ready,
            "difficulty_fit": candidate.components.difficulty_fit,
            "novelty": candidate.components.novelty,
            "spacing": candidate.components.spacing,
            "final_score": candidate.components.final_score,
        },
        "sentences": generate_explanation_sentences(target, candidate, prerequisites),
    }
