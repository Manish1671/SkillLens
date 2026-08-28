"""Pure placement readiness aggregation — no framework or database imports."""

from dataclasses import dataclass

from app.core.enums import (
    DimensionStatus,
    GapRequirementStatus,
    GapSeverity,
    MasteryStatus,
    PlacementRisk,
    PlacementState,
    ReadinessDimension,
)

# Coverage required before a dimension may show a score
COVERAGE_SCORE_THRESHOLD = 0.40
MIN_ASSESSED_FOR_SCORE = 3

# Internal dimension maturity (not compared to the target bar)
NEAR_READY_SCORE = 0.60
READY_SCORE = 0.70
READY_DIMENSION_CONFIDENCE = 0.50

# Confidence policy
HIGH_CONFIDENCE_MIN_COVERAGE = 0.70
HIGH_CONFIDENCE_CAP = 0.55
LOW_SKILL_CONFIDENCE = 0.40

# Placement state
CRITICAL_SHORTFALL_TOLERANCE = 0.05
LOW_GAP_CONFIDENCE = 0.40

DIMENSION_DISPLAY_NAMES: dict[ReadinessDimension, str] = {
    ReadinessDimension.DSA: "DSA",
    ReadinessDimension.CORE_CS: "Core CS",
    ReadinessDimension.PROJECTS: "Projects",
    ReadinessDimension.INTERVIEW: "Interview",
    ReadinessDimension.PROFILE: "Profile",
}

ALL_DIMENSIONS: tuple[ReadinessDimension, ...] = (
    ReadinessDimension.DSA,
    ReadinessDimension.CORE_CS,
    ReadinessDimension.PROJECTS,
    ReadinessDimension.INTERVIEW,
    ReadinessDimension.PROFILE,
)

TARGET_PROFILE_DISCLAIMER = (
    "SkillLens target profiles are internal readiness models, not official "
    "company hiring requirements."
)

READINESS_RISK_DISCLAIMER = "SkillLens model — not a hiring probability."


@dataclass(frozen=True)
class SkillReadinessInput:
    skill_slug: str
    skill_name: str
    status: MasteryStatus
    score: float | None
    confidence: float
    evidence_count: int


@dataclass(frozen=True)
class TargetRequirementInput:
    dimension: ReadinessDimension
    skill_slug: str | None
    skill_name: str | None
    min_score: float
    min_confidence: float
    weight: float
    is_critical: bool


@dataclass(frozen=True)
class SkillHighlight:
    skill_slug: str
    skill_name: str
    score: float


@dataclass(frozen=True)
class DimensionReadinessResult:
    key: ReadinessDimension
    display_name: str
    status: DimensionStatus
    score: float | None
    confidence: float | None
    coverage: float
    assessed_count: int
    in_scope_count: int
    bottleneck_applied: bool
    bottleneck_skill_slug: str | None
    strongest_skills: tuple[SkillHighlight, ...] = ()
    weakest_actionable_skill: SkillHighlight | None = None


@dataclass(frozen=True)
class GapResult:
    dimension: ReadinessDimension
    skill_slug: str | None
    skill_name: str | None
    current: float | None
    required: float
    delta: float | None
    status: GapRequirementStatus
    severity: GapSeverity
    is_critical: bool
    weight: float
    why: str
    rank: int = 0


@dataclass(frozen=True)
class PlacementReadinessResult:
    state: PlacementState
    confidence: float | None
    risk: PlacementRisk
    dimensions: tuple[DimensionReadinessResult, ...]
    blockers: tuple[GapResult, ...]
    gaps: tuple[GapResult, ...] = ()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round4(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _is_assessed(skill: SkillReadinessInput) -> bool:
    return skill.status == MasteryStatus.ASSESSED and skill.score is not None


def coverage_ratio(assessed_count: int, in_scope_count: int) -> float:
    if in_scope_count <= 0:
        return 0.0
    return round(assessed_count / in_scope_count, 4)


def coverage_allows_score(assessed_count: int, in_scope_count: int) -> bool:
    if in_scope_count <= 0 or assessed_count <= 0:
        return False
    if assessed_count < MIN_ASSESSED_FOR_SCORE:
        return False
    return coverage_ratio(assessed_count, in_scope_count) >= COVERAGE_SCORE_THRESHOLD


def evidence_weighted_mean(pairs: list[tuple[float, int]]) -> float | None:
    """Weight each value by evidence volume. Insufficient/empty → None."""
    total_weight = sum(max(1, weight) for _, weight in pairs)
    if not pairs or total_weight <= 0:
        return None
    weighted = sum(value * max(1, weight) for value, weight in pairs)
    return weighted / total_weight


def _dimension_confidence(
    assessed: list[SkillReadinessInput],
    coverage: float,
) -> float | None:
    if not assessed:
        return None
    weighted = evidence_weighted_mean(
        [(skill.confidence, skill.evidence_count) for skill in assessed]
    )
    if weighted is None:
        return None
    scaled = weighted * (0.35 + 0.65 * coverage)
    if coverage < HIGH_CONFIDENCE_MIN_COVERAGE:
        scaled = min(scaled, HIGH_CONFIDENCE_CAP)
    min_conf = min(skill.confidence for skill in assessed)
    if min_conf < LOW_SKILL_CONFIDENCE:
        scaled = min(scaled, HIGH_CONFIDENCE_CAP)
    return round(_clamp(scaled), 4)


def _apply_bottleneck(
    score: float,
    assessed: list[SkillReadinessInput],
    critical_floors: dict[str, float],
) -> tuple[float, bool, str | None]:
    capped = score
    applied = False
    slug: str | None = None
    for skill in assessed:
        floor = critical_floors.get(skill.skill_slug)
        if floor is None or skill.score is None:
            continue
        if skill.score < floor and skill.score < capped:
            capped = skill.score
            applied = True
            slug = skill.skill_slug
    return round(_clamp(capped), 4), applied, slug


def _dimension_status(
    *,
    assessed_count: int,
    in_scope_count: int,
    score: float | None,
    confidence: float | None,
    bottleneck_applied: bool,
) -> DimensionStatus:
    if in_scope_count <= 0 or assessed_count <= 0:
        return DimensionStatus.NOT_ASSESSED
    if not coverage_allows_score(assessed_count, in_scope_count) or score is None:
        return DimensionStatus.EARLY
    conf = confidence if confidence is not None else 0.0
    if score >= READY_SCORE and conf >= READY_DIMENSION_CONFIDENCE and not bottleneck_applied:
        return DimensionStatus.READY
    if score >= NEAR_READY_SCORE:
        return DimensionStatus.NEAR_READY
    return DimensionStatus.DEVELOPING


def compute_dimension_readiness(
    dimension: ReadinessDimension,
    in_scope: list[SkillReadinessInput],
    *,
    critical_floors: dict[str, float] | None = None,
) -> DimensionReadinessResult:
    assessed = [skill for skill in in_scope if _is_assessed(skill)]
    assessed_count = len(assessed)
    in_scope_count = len(in_scope)
    coverage = coverage_ratio(assessed_count, in_scope_count)
    floors = critical_floors or {}

    score: float | None = None
    bottleneck_applied = False
    bottleneck_slug: str | None = None
    if coverage_allows_score(assessed_count, in_scope_count):
        raw = evidence_weighted_mean(
            [(float(skill.score or 0), skill.evidence_count) for skill in assessed]
        )
        if raw is not None:
            score, bottleneck_applied, bottleneck_slug = _apply_bottleneck(raw, assessed, floors)

    confidence = _dimension_confidence(assessed, coverage)
    status = _dimension_status(
        assessed_count=assessed_count,
        in_scope_count=in_scope_count,
        score=score,
        confidence=confidence,
        bottleneck_applied=bottleneck_applied,
    )
    if status in {DimensionStatus.NOT_ASSESSED, DimensionStatus.EARLY}:
        score = None

    strongest = tuple(
        SkillHighlight(skill.skill_slug, skill.skill_name, float(skill.score or 0))
        for skill in sorted(assessed, key=lambda item: float(item.score or 0), reverse=True)[:3]
    )
    weakest = None
    if assessed:
        weak = min(assessed, key=lambda item: (float(item.score or 1.0), item.skill_slug))
        weakest = SkillHighlight(weak.skill_slug, weak.skill_name, float(weak.score or 0))

    return DimensionReadinessResult(
        key=dimension,
        display_name=DIMENSION_DISPLAY_NAMES[dimension],
        status=status,
        score=_round4(score),
        confidence=_round4(confidence) if assessed else None,
        coverage=coverage,
        assessed_count=assessed_count,
        in_scope_count=in_scope_count,
        bottleneck_applied=bottleneck_applied,
        bottleneck_skill_slug=bottleneck_slug,
        strongest_skills=strongest,
        weakest_actionable_skill=weakest,
    )


def _gap_status(
    current: float | None,
    required: float,
    evidence_ok: bool,
) -> GapRequirementStatus:
    if not evidence_ok or current is None:
        return GapRequirementStatus.INSUFFICIENT_EVIDENCE
    if current > required:
        return GapRequirementStatus.EXCEEDS
    if current >= required:
        return GapRequirementStatus.MEETS
    return GapRequirementStatus.BELOW


def _gap_severity(
    status: GapRequirementStatus,
    is_critical: bool,
    confidence: float | None,
    min_confidence: float,
) -> GapSeverity:
    if is_critical and status in {
        GapRequirementStatus.BELOW,
        GapRequirementStatus.INSUFFICIENT_EVIDENCE,
    }:
        return GapSeverity.CRITICAL_BLOCKER
    if status == GapRequirementStatus.BELOW:
        return GapSeverity.SECONDARY
    if confidence is not None and confidence < min_confidence:
        return GapSeverity.WATCH
    return GapSeverity.WATCH


def _gap_why(gap: GapResult) -> str:
    name = DIMENSION_DISPLAY_NAMES[gap.dimension]
    if gap.skill_name:
        name = f"{name} / {gap.skill_name}"
    if gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
        return f"{name} does not have enough evidence to compare against the target bar."
    if gap.status == GapRequirementStatus.BELOW:
        current = f"{(gap.current or 0) * 100:.0f}%"
        required = f"{gap.required * 100:.0f}%"
        return f"{name} is at {current} versus the {required} target bar."
    if gap.status == GapRequirementStatus.MEETS:
        return f"{name} meets the target bar."
    return f"{name} exceeds the target bar."


def compute_requirement_gap(
    requirement: TargetRequirementInput,
    dimensions: dict[ReadinessDimension, DimensionReadinessResult],
    skills_by_slug: dict[str, SkillReadinessInput],
) -> GapResult:
    dimension = dimensions[requirement.dimension]
    if requirement.skill_slug:
        skill = skills_by_slug.get(requirement.skill_slug)
        evidence_ok = skill is not None and _is_assessed(skill)
        current = float(skill.score) if evidence_ok and skill and skill.score is not None else None
        confidence = skill.confidence if evidence_ok and skill else None
    else:
        evidence_ok = dimension.score is not None
        current = dimension.score
        confidence = dimension.confidence

    status = _gap_status(current, requirement.min_score, evidence_ok)
    delta = round(current - requirement.min_score, 4) if current is not None else None
    severity = _gap_severity(
        status, requirement.is_critical, confidence, requirement.min_confidence
    )
    draft = GapResult(
        dimension=requirement.dimension,
        skill_slug=requirement.skill_slug,
        skill_name=requirement.skill_name,
        current=_round4(current),
        required=requirement.min_score,
        delta=delta,
        status=status,
        severity=severity,
        is_critical=requirement.is_critical,
        weight=requirement.weight,
        why="",
    )
    return GapResult(
        dimension=draft.dimension,
        skill_slug=draft.skill_slug,
        skill_name=draft.skill_name,
        current=draft.current,
        required=draft.required,
        delta=draft.delta,
        status=draft.status,
        severity=draft.severity,
        is_critical=draft.is_critical,
        weight=draft.weight,
        why=_gap_why(draft),
    )


def _weighted_shortfall(gap: GapResult) -> float:
    if gap.current is None:
        return gap.weight * gap.required
    return gap.weight * max(0.0, gap.required - gap.current)


def rank_gaps(gaps: list[GapResult]) -> list[GapResult]:
    def sort_key(gap: GapResult) -> tuple:
        if gap.is_critical and gap.status == GapRequirementStatus.BELOW:
            tier = 0
        elif gap.is_critical and gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE:
            tier = 1
        else:
            tier = 2
        low_conf = (
            0
            if gap.severity == GapSeverity.WATCH and gap.status != GapRequirementStatus.BELOW
            else 1
        )
        skill_level = 0 if gap.skill_slug else 1
        return (tier, -_weighted_shortfall(gap), low_conf, skill_level, gap.dimension.value)

    ordered = sorted(gaps, key=sort_key)
    ranked: list[GapResult] = []
    for index, gap in enumerate(ordered, start=1):
        ranked.append(
            GapResult(
                dimension=gap.dimension,
                skill_slug=gap.skill_slug,
                skill_name=gap.skill_name,
                current=gap.current,
                required=gap.required,
                delta=gap.delta,
                status=gap.status,
                severity=gap.severity,
                is_critical=gap.is_critical,
                weight=gap.weight,
                why=gap.why,
                rank=index,
            )
        )
    return ranked


def _critical_requirement_state(
    gaps: list[GapResult],
) -> tuple[list[GapResult], list[GapResult], list[GapResult]]:
    critical = [gap for gap in gaps if gap.is_critical and gap.skill_slug is None]
    insufficient = [
        gap for gap in critical if gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE
    ]
    below = [gap for gap in critical if gap.status == GapRequirementStatus.BELOW]
    met = [
        gap
        for gap in critical
        if gap.status in {GapRequirementStatus.MEETS, GapRequirementStatus.EXCEEDS}
    ]
    return insufficient, below, met


def _small_shortfall(gap: GapResult) -> bool:
    if gap.current is None:
        return False
    return (gap.required - gap.current) <= CRITICAL_SHORTFALL_TOLERANCE


def compute_placement_state(
    *,
    has_target: bool,
    dimensions: tuple[DimensionReadinessResult, ...],
    gaps: list[GapResult],
) -> PlacementState:
    if not has_target:
        return PlacementState.NOT_ASSESSED

    any_evidence = any(item.assessed_count > 0 for item in dimensions)
    if not any_evidence:
        return PlacementState.NOT_ASSESSED

    insufficient, below, met = _critical_requirement_state(gaps)
    critical_dims = [gap for gap in gaps if gap.is_critical and gap.skill_slug is None]
    assessed_critical = [
        gap for gap in critical_dims if gap.status != GapRequirementStatus.INSUFFICIENT_EVIDENCE
    ]

    if insufficient:
        return PlacementState.EARLY

    if below:
        if all(_small_shortfall(gap) for gap in below) and not insufficient:
            noncritical_only = all(
                gap.status != GapRequirementStatus.BELOW
                or not gap.is_critical
                or _small_shortfall(gap)
                for gap in gaps
                if gap.skill_slug is None
            )
            if noncritical_only:
                return PlacementState.NEAR_READY
        if assessed_critical and len(assessed_critical) >= max(1, len(critical_dims) - 1):
            return PlacementState.DEVELOPING
        return PlacementState.DEVELOPING

    skill_critical_open = [
        gap
        for gap in gaps
        if gap.is_critical
        and gap.skill_slug
        and gap.status in {GapRequirementStatus.BELOW, GapRequirementStatus.INSUFFICIENT_EVIDENCE}
    ]
    confidence_ok = all(
        (dimensions_by_key(dimensions)[gap.dimension].confidence or 0) >= LOW_GAP_CONFIDENCE
        or gap.status == GapRequirementStatus.INSUFFICIENT_EVIDENCE
        for gap in met
    )
    if skill_critical_open:
        return PlacementState.DEVELOPING
    if met and len(met) == len(critical_dims) and not insufficient and confidence_ok:
        return PlacementState.READY
    if met:
        return PlacementState.NEAR_READY
    return PlacementState.DEVELOPING


def dimensions_by_key(
    dimensions: tuple[DimensionReadinessResult, ...] | list[DimensionReadinessResult],
) -> dict[ReadinessDimension, DimensionReadinessResult]:
    return {item.key: item for item in dimensions}


def compute_placement_confidence(
    dimensions: tuple[DimensionReadinessResult, ...],
    gaps: list[GapResult],
) -> float | None:
    scored = [item for item in dimensions if item.confidence is not None and item.score is not None]
    if not scored:
        return None
    critical = [gap for gap in gaps if gap.is_critical and gap.skill_slug is None]
    if not critical:
        values = [(item.confidence or 0, item.assessed_count) for item in scored]
        return _round4(evidence_weighted_mean(values))
    assessed_critical = sum(
        1 for gap in critical if gap.status != GapRequirementStatus.INSUFFICIENT_EVIDENCE
    )
    coverage = assessed_critical / len(critical)
    base = evidence_weighted_mean([(item.confidence or 0, item.assessed_count) for item in scored])
    if base is None:
        return None
    return round(_clamp(base * coverage), 4)


def compute_placement_risk(state: PlacementState, gaps: list[GapResult]) -> PlacementRisk:
    if any(gap.severity == GapSeverity.CRITICAL_BLOCKER for gap in gaps):
        return PlacementRisk.HIGH
    if state in {PlacementState.NOT_ASSESSED, PlacementState.EARLY, PlacementState.DEVELOPING}:
        return PlacementRisk.MEDIUM
    return PlacementRisk.LOW


def compute_placement_readiness(
    *,
    has_target: bool,
    dimensions: list[DimensionReadinessResult],
    requirements: list[TargetRequirementInput],
    skills_by_slug: dict[str, SkillReadinessInput] | None = None,
) -> PlacementReadinessResult:
    dim_tuple = tuple(dimensions)
    dim_map = dimensions_by_key(dim_tuple)
    skill_map = skills_by_slug or {}
    gaps = [
        compute_requirement_gap(requirement, dim_map, skill_map) for requirement in requirements
    ]
    ranked = rank_gaps(gaps)
    blockers = tuple(
        gap
        for gap in ranked
        if gap.status in {GapRequirementStatus.BELOW, GapRequirementStatus.INSUFFICIENT_EVIDENCE}
        or gap.severity == GapSeverity.CRITICAL_BLOCKER
    )[:5]
    state = compute_placement_state(has_target=has_target, dimensions=dim_tuple, gaps=ranked)
    confidence = compute_placement_confidence(dim_tuple, ranked) if has_target else None
    risk = compute_placement_risk(state, ranked)
    return PlacementReadinessResult(
        state=state,
        confidence=confidence,
        risk=risk,
        dimensions=dim_tuple,
        blockers=blockers,
        gaps=tuple(ranked),
    )


def _join_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def explain_placement(
    *,
    has_target: bool,
    target_name: str | None,
    dimensions: tuple[DimensionReadinessResult, ...] | list[DimensionReadinessResult],
    gaps: tuple[GapResult, ...] | list[GapResult],
) -> tuple[str, ...]:
    """Deterministic home-page explanation. Does not invent scores."""
    if not has_target:
        return ("Choose a target profile to evaluate readiness.",)

    target = target_name or "the selected target"
    dim_map = {item.key: item for item in dimensions}
    gap_by_dim = {gap.dimension: gap for gap in gaps if gap.skill_slug is None}
    sentences: list[str] = []

    for key in (ReadinessDimension.DSA, ReadinessDimension.CORE_CS):
        dim = dim_map.get(key)
        if dim is None:
            continue
        name = dim.display_name
        gap = gap_by_dim.get(key)
        if dim.status == DimensionStatus.NOT_ASSESSED:
            sentences.append(f"{name} is not assessed yet.")
            continue
        if gap is None:
            if dim.score is None:
                sentences.append(f"{name} does not have enough evidence to show a score.")
            else:
                sentences.append(
                    f"{name} has enough evidence for an internal SkillLens assessment."
                )
            continue
        if gap.status == GapRequirementStatus.EXCEEDS:
            sentences.append(
                f"Your {name} evidence is currently sufficient and above the {target} target."
            )
        elif gap.status == GapRequirementStatus.MEETS:
            sentences.append(
                f"Your {name} evidence is currently sufficient and meets the {target} target."
            )
        elif gap.status == GapRequirementStatus.BELOW:
            sentences.append(f"{name} is assessed but remains below the target bar.")
        else:
            sentences.append(
                f"{name} does not have enough evidence to compare against the target bar."
            )

    unassessed = [
        dim_map[key].display_name
        for key in (
            ReadinessDimension.PROJECTS,
            ReadinessDimension.INTERVIEW,
            ReadinessDimension.PROFILE,
        )
        if key in dim_map and dim_map[key].status == DimensionStatus.NOT_ASSESSED
    ]
    if unassessed:
        sentences.append(f"{_join_names(unassessed)} are not assessed yet.")

    if not sentences:
        sentences.append("Readiness is computed from assessed SkillMastery rows only.")
    return tuple(sentences)
