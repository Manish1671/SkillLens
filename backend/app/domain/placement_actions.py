"""Pure cross-domain placement action ranking — no framework or database imports."""

from dataclasses import dataclass, replace

from app.core.enums import (
    GapRequirementStatus,
    PlacementActionKind,
    ReadinessDimension,
)
from app.domain.readiness import (
    DIMENSION_DISPLAY_NAMES,
    DimensionReadinessResult,
    GapResult,
    PlacementReadinessResult,
)

# Scoring weights (must sum conceptually to a 0–1-ish composite; not probabilities)
WEIGHT_GAP_MAGNITUDE = 0.28
WEIGHT_TARGET_IMPORTANCE = 0.18
WEIGHT_CRITICALITY = 0.22
WEIGHT_UNCERTAINTY = 0.10
WEIGHT_EXPECTED_LIFT = 0.10
WEIGHT_PREREQUISITE = 0.07
WEIGHT_EFFORT_FIT = 0.05

CRITICAL_SCORE = 1.0
NONCRITICAL_SCORE = 0.20
LOW_CONFIDENCE = 0.40

DEFAULT_ASSESS_MINUTES = 20
DEFAULT_QUIZ_MINUTES = 10
DEFAULT_DSA_MINUTES = 20
EFFORT_FIT_LOW = 5
EFFORT_FIT_HIGH = 25
EFFORT_FIT_STRETCH = 40

REASON_CRITICAL_DIMENSION_GAP = "critical_dimension_gap"
REASON_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
REASON_CS_WEAK_SKILL = "cs_weak_skill"
REASON_DSA_GAP = "dsa_gap"
REASON_EFFORT_FIT = "effort_fit"
REASON_ASSESS_REQUIRED = "assess_required_dimension"
REASON_HIGHER_PRIORITY_THAN_DSA = "higher_priority_than_dsa_polish"
REASON_TARGET_WEIGHT = "target_weight"

ACTIONABLE_DIMENSIONS = (ReadinessDimension.DSA, ReadinessDimension.CORE_CS)


@dataclass(frozen=True)
class PlacementActionCandidate:
    action_kind: PlacementActionKind
    title: str
    description: str
    target_dimension: ReadinessDimension
    target_skill_slug: str | None
    target_skill_name: str | None
    estimated_effort_minutes: int
    gap_magnitude: float
    requirement_weight: float
    is_critical: bool
    gap_status: GapRequirementStatus
    confidence: float | None
    expected_lift: float
    prerequisite_ready: float
    effort_fit: float
    stable_key: str
    target_name: str
    current: float | None
    required: float
    problem_id: str | None = None
    problem_slug: str | None = None
    problem_title: str | None = None


@dataclass(frozen=True)
class ScoredPlacementAction:
    candidate: PlacementActionCandidate
    score: float
    reason_codes: tuple[str, ...]
    explanation: tuple[str, ...]
    rank: int = 0


def effort_fit_score(minutes: int) -> float:
    if EFFORT_FIT_LOW <= minutes <= EFFORT_FIT_HIGH:
        return 1.0
    if minutes <= EFFORT_FIT_STRETCH:
        return 0.7
    return 0.4


def gap_magnitude(gap: GapResult) -> float:
    if gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
        return 1.0
    if gap.status == GapRequirementStatus.BELOW and gap.current is not None:
        required = max(gap.required, 0.01)
        return round(min(1.0, max(0.0, (required - gap.current) / required)), 4)
    return 0.05


def expected_lift_signal(gap: GapResult) -> float:
    if gap.is_critical and gap.status == GapRequirementStatus.BELOW:
        return 1.0
    if gap.is_critical and gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
        return 0.85
    if gap.status == GapRequirementStatus.BELOW:
        return 0.45
    return 0.15


def uncertainty_signal(status: GapRequirementStatus, confidence: float | None) -> float:
    if status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
        return 1.0
    if confidence is None:
        return 0.5
    return round(min(1.0, max(0.0, 1.0 - confidence)), 4)


def batch_fingerprint(actions: list[ScoredPlacementAction]) -> str:
    return "|".join(item.candidate.stable_key for item in actions)


def attach_problem(
    candidate: PlacementActionCandidate,
    *,
    problem_id: str,
    problem_slug: str,
    problem_title: str,
    estimated_effort_minutes: int,
) -> PlacementActionCandidate:
    minutes = estimated_effort_minutes
    title = problem_title
    if candidate.action_kind == PlacementActionKind.CS_QUIZ and candidate.target_skill_name:
        title = f"Improve {candidate.target_skill_name}"
    return replace(
        candidate,
        problem_id=problem_id,
        problem_slug=problem_slug,
        problem_title=problem_title,
        estimated_effort_minutes=minutes,
        effort_fit=effort_fit_score(minutes),
        title=title,
        stable_key=(
            f"{candidate.action_kind.value}:{candidate.target_dimension.value}:"
            f"{candidate.target_skill_slug or '-'}:{problem_slug}"
        ),
    )


def generate_candidates(
    placement: PlacementReadinessResult,
    *,
    target_name: str,
    include_dsa_polish: bool = True,
) -> list[PlacementActionCandidate]:
    """Turn dimension-level DSA/Core CS gaps into action slots (no problem IDs yet)."""
    dim_map = {item.key: item for item in placement.dimensions}
    dim_gaps = [gap for gap in placement.gaps if gap.skill_slug is None]
    by_dim = {gap.dimension: gap for gap in dim_gaps}
    candidates: list[PlacementActionCandidate] = []

    for key in ACTIONABLE_DIMENSIONS:
        gap = by_dim.get(key)
        dimension = dim_map.get(key)
        if gap is None or dimension is None:
            continue
        blocking = gap.status in {
            GapRequirementStatus.BELOW,
            GapRequirementStatus.INSUFFICIENT_EVIDENCE,
        }
        polish = (
            include_dsa_polish
            and key == ReadinessDimension.DSA
            and gap.status in {GapRequirementStatus.MEETS, GapRequirementStatus.EXCEEDS}
            and dimension.score is not None
        )
        if not blocking and not polish:
            continue
        built = _candidate_for_gap(gap, dimension, target_name)
        if built is not None:
            candidates.append(built)
    return candidates


def _candidate_for_gap(
    gap: GapResult,
    dimension: DimensionReadinessResult,
    target_name: str,
) -> PlacementActionCandidate | None:
    name = DIMENSION_DISPLAY_NAMES[gap.dimension]
    if gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
        return PlacementActionCandidate(
            action_kind=PlacementActionKind.ASSESS_DIMENSION,
            title=f"Assess {name}",
            description=f"{name} is required for the selected target but is not assessed yet.",
            target_dimension=gap.dimension,
            target_skill_slug=None,
            target_skill_name=None,
            estimated_effort_minutes=DEFAULT_ASSESS_MINUTES,
            gap_magnitude=gap_magnitude(gap),
            requirement_weight=gap.weight,
            is_critical=gap.is_critical,
            gap_status=gap.status,
            confidence=dimension.confidence,
            expected_lift=expected_lift_signal(gap),
            prerequisite_ready=1.0,
            effort_fit=effort_fit_score(DEFAULT_ASSESS_MINUTES),
            stable_key=f"{PlacementActionKind.ASSESS_DIMENSION.value}:{gap.dimension.value}:-:-",
            target_name=target_name,
            current=gap.current,
            required=gap.required,
        )

    if gap.dimension == ReadinessDimension.CORE_CS:
        weakest = dimension.weakest_actionable_skill
        skill_slug = weakest.skill_slug if weakest else None
        skill_name = weakest.skill_name if weakest else None
        title = f"Improve {skill_name}" if skill_name else "Improve Core CS"
        return PlacementActionCandidate(
            action_kind=PlacementActionKind.CS_QUIZ,
            title=title,
            description="A focused Core CS quiz targeting a weak assessed skill.",
            target_dimension=gap.dimension,
            target_skill_slug=skill_slug,
            target_skill_name=skill_name,
            estimated_effort_minutes=DEFAULT_QUIZ_MINUTES,
            gap_magnitude=gap_magnitude(gap),
            requirement_weight=gap.weight,
            is_critical=gap.is_critical,
            gap_status=gap.status,
            confidence=dimension.confidence,
            expected_lift=expected_lift_signal(gap),
            prerequisite_ready=1.0,
            effort_fit=effort_fit_score(DEFAULT_QUIZ_MINUTES),
            stable_key=(
                f"{PlacementActionKind.CS_QUIZ.value}:{gap.dimension.value}:{skill_slug or '-'}:-"
            ),
            target_name=target_name,
            current=gap.current,
            required=gap.required,
        )

    weakest = dimension.weakest_actionable_skill
    skill_slug = weakest.skill_slug if weakest else None
    skill_name = weakest.skill_name if weakest else None
    return PlacementActionCandidate(
        action_kind=PlacementActionKind.DSA_PROBLEM,
        title="Next DSA problem",
        description="Practice a coding problem chosen by the DSA recommendation engine.",
        target_dimension=gap.dimension,
        target_skill_slug=skill_slug,
        target_skill_name=skill_name,
        estimated_effort_minutes=DEFAULT_DSA_MINUTES,
        gap_magnitude=gap_magnitude(gap),
        requirement_weight=gap.weight,
        is_critical=gap.is_critical,
        gap_status=gap.status,
        confidence=dimension.confidence,
        expected_lift=expected_lift_signal(gap),
        prerequisite_ready=1.0,
        effort_fit=effort_fit_score(DEFAULT_DSA_MINUTES),
        stable_key=(
            f"{PlacementActionKind.DSA_PROBLEM.value}:"
            f"{gap.dimension.value}:{skill_slug or '-'}:-"
        ),
        target_name=target_name,
        current=gap.current,
        required=gap.required,
    )


def score_placement_action(candidate: PlacementActionCandidate) -> ScoredPlacementAction:
    criticality = CRITICAL_SCORE if candidate.is_critical else NONCRITICAL_SCORE
    uncertainty = uncertainty_signal(candidate.gap_status, candidate.confidence)
    score = round(
        WEIGHT_GAP_MAGNITUDE * candidate.gap_magnitude
        + WEIGHT_TARGET_IMPORTANCE * candidate.requirement_weight
        + WEIGHT_CRITICALITY * criticality
        + WEIGHT_UNCERTAINTY * uncertainty
        + WEIGHT_EXPECTED_LIFT * candidate.expected_lift
        + WEIGHT_PREREQUISITE * candidate.prerequisite_ready
        + WEIGHT_EFFORT_FIT * candidate.effort_fit,
        4,
    )
    codes, sentences = explain_action(candidate)
    return ScoredPlacementAction(
        candidate=candidate,
        score=score,
        reason_codes=codes,
        explanation=sentences,
    )


def ranking_key(item: ScoredPlacementAction) -> tuple:
    candidate = item.candidate
    critical_below = (
        0 if candidate.is_critical and candidate.gap_status == GapRequirementStatus.BELOW else 1
    )
    critical_insufficient = (
        0
        if candidate.is_critical
        and candidate.gap_status == GapRequirementStatus.INSUFFICIENT_EVIDENCE
        else 1
    )
    weighted_shortfall = candidate.gap_magnitude * candidate.requirement_weight
    if candidate.is_critical:
        weighted_shortfall *= 1.2
    low_confidence = (
        0 if candidate.confidence is None or candidate.confidence < LOW_CONFIDENCE else 1
    )
    return (
        critical_below,
        critical_insufficient,
        -round(weighted_shortfall, 6),
        -candidate.requirement_weight,
        low_confidence,
        -candidate.prerequisite_ready,
        -candidate.effort_fit,
        candidate.stable_key,
    )


def rank_placement_actions(
    actions: list[ScoredPlacementAction],
) -> list[ScoredPlacementAction]:
    ordered = sorted(actions, key=ranking_key)
    ranked: list[ScoredPlacementAction] = []
    for index, item in enumerate(ordered, start=1):
        ranked.append(
            ScoredPlacementAction(
                candidate=item.candidate,
                score=item.score,
                reason_codes=item.reason_codes,
                explanation=item.explanation,
                rank=index,
            )
        )
    return ranked


def score_and_rank(candidates: list[PlacementActionCandidate]) -> list[ScoredPlacementAction]:
    return rank_placement_actions([score_placement_action(item) for item in candidates])


def explain_action(candidate: PlacementActionCandidate) -> tuple[tuple[str, ...], tuple[str, ...]]:
    name = DIMENSION_DISPLAY_NAMES[candidate.target_dimension]
    target = candidate.target_name
    codes: list[str] = []
    sentences: list[str] = []

    if candidate.gap_status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
        codes.append(REASON_INSUFFICIENT_EVIDENCE)
        codes.append(REASON_ASSESS_REQUIRED)
        sentences.append(
            f"{name} is required for the selected {target} target but there is not enough "
            "evidence to determine your current readiness."
        )
        sentences.append(f"An assessment is the highest-leverage next step for {name}.")
    elif candidate.gap_status == GapRequirementStatus.BELOW:
        if candidate.is_critical:
            codes.append(REASON_CRITICAL_DIMENSION_GAP)
        points = None
        if candidate.current is not None:
            points = round((candidate.required - candidate.current) * 100)
        if points is not None and points > 0:
            sentences.append(
                f"{name} is currently {points} points below your {target} target"
                + (" and is a critical requirement." if candidate.is_critical else ".")
            )
        else:
            sentences.append(f"{name} is below the {target} target bar.")
        if candidate.action_kind == PlacementActionKind.CS_QUIZ:
            codes.append(REASON_CS_WEAK_SKILL)
            if candidate.target_skill_name:
                sentences.append(
                    f"Your weakest assessed Core CS skill is {candidate.target_skill_name}."
                )
            sentences.append("This quiz is a focused way to improve that gap.")
        else:
            codes.append(REASON_DSA_GAP)
            if candidate.target_skill_name:
                sentences.append(f"Practice is aimed at {candidate.target_skill_name}.")
            sentences.append("The DSA recommendation engine selected the coding problem.")
        if candidate.action_kind != PlacementActionKind.DSA_PROBLEM and candidate.is_critical:
            codes.append(REASON_HIGHER_PRIORITY_THAN_DSA)
            if len(sentences) < 3:
                sentences.append(
                    "This outranks additional DSA practice because it closes a critical target gap."
                )
    else:
        codes.append(REASON_DSA_GAP)
        sentences.append(f"{name} already meets the {target} target.")
        sentences.append("A DSA problem remains available as continued practice, not a blocker.")

    if candidate.effort_fit >= 0.99:
        codes.append(REASON_EFFORT_FIT)
    if candidate.requirement_weight >= 0.3:
        codes.append(REASON_TARGET_WEIGHT)

    return tuple(codes), tuple(sentences[:3])
