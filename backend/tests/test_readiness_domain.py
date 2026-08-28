from app.core.enums import (
    DimensionStatus,
    GapRequirementStatus,
    GapSeverity,
    MasteryStatus,
    PlacementState,
    ReadinessDimension,
)
from app.domain.readiness import (
    SkillReadinessInput,
    TargetRequirementInput,
    compute_dimension_readiness,
    compute_placement_readiness,
    explain_placement,
    rank_gaps,
)


def _skill(
    slug: str,
    *,
    status: MasteryStatus = MasteryStatus.ASSESSED,
    score: float | None = 0.8,
    confidence: float = 0.6,
    evidence: int = 4,
    name: str | None = None,
) -> SkillReadinessInput:
    return SkillReadinessInput(
        skill_slug=slug,
        skill_name=name or slug.replace("-", " ").title(),
        status=status,
        score=score,
        confidence=confidence,
        evidence_count=evidence,
    )


def _dsa_scope(assessed: int = 6, total: int = 14, score: float = 0.8) -> list[SkillReadinessInput]:
    skills: list[SkillReadinessInput] = []
    for index in range(total):
        slug = f"skill-{index:02d}"
        if index < assessed:
            skills.append(_skill(slug, score=score, evidence=3 + index))
        else:
            skills.append(
                _skill(
                    slug,
                    status=MasteryStatus.INSUFFICIENT,
                    score=0.0,
                    confidence=0.1,
                    evidence=1,
                )
            )
    return skills


def _req(
    dimension: ReadinessDimension,
    *,
    min_score: float,
    weight: float,
    critical: bool,
    skill_slug: str | None = None,
    skill_name: str | None = None,
    min_confidence: float = 0.5,
) -> TargetRequirementInput:
    return TargetRequirementInput(
        dimension=dimension,
        skill_slug=skill_slug,
        skill_name=skill_name,
        min_score=min_score,
        min_confidence=min_confidence,
        weight=weight,
        is_critical=critical,
    )


def test_no_target_is_not_assessed() -> None:
    result = compute_placement_readiness(has_target=False, dimensions=[], requirements=[])
    assert result.state == PlacementState.NOT_ASSESSED
    assert result.confidence is None


def test_target_without_evidence_is_not_assessed() -> None:
    empty = compute_dimension_readiness(ReadinessDimension.DSA, [])
    core = compute_dimension_readiness(ReadinessDimension.CORE_CS, [])
    result = compute_placement_readiness(
        has_target=True,
        dimensions=[empty, core],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.7, weight=0.4, critical=True),
            _req(ReadinessDimension.CORE_CS, min_score=0.6, weight=0.35, critical=True),
        ],
    )
    assert result.state == PlacementState.NOT_ASSESSED


def test_insufficient_skill_is_not_treated_as_zero() -> None:
    skills = [
        _skill("arrays", score=0.9, evidence=5),
        _skill("hashing", score=0.85, evidence=4),
        _skill("graphs", status=MasteryStatus.INSUFFICIENT, score=0.0, confidence=0.2, evidence=1),
        _skill("trees", score=0.7, evidence=3),
        _skill("dp", score=0.65, evidence=3),
        _skill("stack", score=0.72, evidence=3),
        _skill("queue", score=0.71, evidence=3),
        *[
            _skill(f"other-{i}", status=MasteryStatus.INSUFFICIENT, score=None, evidence=0)
            for i in range(7)
        ],
    ]
    result = compute_dimension_readiness(ReadinessDimension.DSA, skills)
    assert result.score is not None
    assert result.score > 0.6
    assert result.assessed_count == 6


def test_coverage_threshold_hides_score() -> None:
    skills = _dsa_scope(assessed=2, total=14)
    result = compute_dimension_readiness(ReadinessDimension.DSA, skills)
    assert result.score is None
    assert result.status == DimensionStatus.EARLY
    assert result.assessed_count == 2


def test_enough_coverage_produces_dimension_score() -> None:
    result = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=6))
    assert result.score is not None
    assert result.score > 0
    assert result.status != DimensionStatus.NOT_ASSESSED
    assert result.status != DimensionStatus.EARLY


def test_assessed_only_aggregation_ignores_insufficient_high_placeholder() -> None:
    skills = [
        _skill("a", score=1.0, evidence=10),
        _skill("b", score=1.0, evidence=10),
        _skill("c", score=1.0, evidence=10),
        _skill("d", score=1.0, evidence=10),
        _skill("e", score=1.0, evidence=10),
        _skill("f", score=1.0, evidence=10),
        _skill("fake", status=MasteryStatus.INSUFFICIENT, score=0.01, evidence=99),
        *[
            _skill(f"rest-{i}", status=MasteryStatus.INSUFFICIENT, score=None, evidence=0)
            for i in range(7)
        ],
    ]
    result = compute_dimension_readiness(ReadinessDimension.DSA, skills)
    assert result.score is not None
    assert result.score >= 0.95


def test_confidence_responds_to_coverage() -> None:
    high = compute_dimension_readiness(
        ReadinessDimension.DSA,
        _dsa_scope(assessed=12, total=14, score=0.8),
    )
    low = compute_dimension_readiness(
        ReadinessDimension.DSA,
        _dsa_scope(assessed=6, total=14, score=0.8),
    )
    assert high.confidence is not None
    assert low.confidence is not None
    assert high.confidence > low.confidence


def test_low_confidence_skills_prevent_high_dimension_confidence() -> None:
    skills = _dsa_scope(assessed=6)
    skills[0] = _skill("skill-00", score=0.85, confidence=0.15, evidence=8)
    result = compute_dimension_readiness(ReadinessDimension.DSA, skills)
    assert result.confidence is not None
    assert result.confidence <= 0.55


def test_critical_skill_bottleneck_caps_dimension() -> None:
    skills = _dsa_scope(assessed=6, score=0.9)
    skills[0] = _skill("sliding-window", score=0.32, evidence=8)
    uncapped = compute_dimension_readiness(ReadinessDimension.DSA, skills)
    capped = compute_dimension_readiness(
        ReadinessDimension.DSA,
        skills,
        critical_floors={"sliding-window": 0.70},
    )
    assert uncapped.score is not None
    assert capped.score is not None
    assert capped.score < uncapped.score
    assert capped.bottleneck_applied
    assert capped.score == 0.32


def test_target_requirement_met_and_below_and_insufficient() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=6, score=0.82))
    core = compute_dimension_readiness(ReadinessDimension.CORE_CS, [])
    projects = compute_dimension_readiness(ReadinessDimension.PROJECTS, [])
    result = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core, projects],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.70, weight=0.4, critical=True),
            _req(ReadinessDimension.CORE_CS, min_score=0.60, weight=0.35, critical=True),
            _req(ReadinessDimension.PROJECTS, min_score=0.55, weight=0.15, critical=False),
        ],
    )
    by_dim = {gap.dimension: gap for gap in result.gaps if gap.skill_slug is None}
    assert by_dim[ReadinessDimension.DSA].status == GapRequirementStatus.EXCEEDS
    assert by_dim[ReadinessDimension.CORE_CS].status == GapRequirementStatus.INSUFFICIENT_EVIDENCE
    assert by_dim[ReadinessDimension.PROJECTS].status == GapRequirementStatus.INSUFFICIENT_EVIDENCE


def test_critical_gap_outranks_noncritical_gap() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=6, score=0.50))
    core = compute_dimension_readiness(
        ReadinessDimension.CORE_CS,
        [_skill("sql", score=0.20, evidence=4) for _ in range(4)]
        + [_skill("x", status=MasteryStatus.INSUFFICIENT, score=None, evidence=0)],
    )
    result = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.70, weight=0.1, critical=True),
            _req(ReadinessDimension.CORE_CS, min_score=0.90, weight=0.9, critical=False),
        ],
    )
    assert result.blockers[0].dimension == ReadinessDimension.DSA
    assert result.blockers[0].is_critical
    assert result.blockers[0].severity == GapSeverity.CRITICAL_BLOCKER


def test_larger_weighted_gap_outranks_smaller_weighted_gap() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=6, score=0.50))
    core_skills = [_skill(f"cs-{i}", score=0.40, evidence=4) for i in range(4)]
    core = compute_dimension_readiness(ReadinessDimension.CORE_CS, core_skills)
    gaps = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.70, weight=0.2, critical=False),
            _req(ReadinessDimension.CORE_CS, min_score=0.70, weight=0.8, critical=False),
        ],
    ).blockers
    ranked = rank_gaps(list(gaps))
    assert ranked[0].dimension == ReadinessDimension.CORE_CS


def test_dsa_strong_but_core_cs_absent_is_not_ready() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=8, score=0.85))
    core = compute_dimension_readiness(ReadinessDimension.CORE_CS, [])
    result = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.70, weight=0.4, critical=True),
            _req(ReadinessDimension.CORE_CS, min_score=0.60, weight=0.35, critical=True),
        ],
    )
    assert result.state != PlacementState.READY
    assert result.state == PlacementState.EARLY


def test_dsa_strong_and_core_cs_ready_can_advance() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=8, score=0.85))
    core = compute_dimension_readiness(
        ReadinessDimension.CORE_CS,
        [_skill(f"sql-{i}", score=0.72, confidence=0.6, evidence=4) for i in range(4)],
    )
    result = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.70, weight=0.4, critical=True),
            _req(ReadinessDimension.CORE_CS, min_score=0.60, weight=0.35, critical=True),
        ],
    )
    assert result.state in {PlacementState.NEAR_READY, PlacementState.READY}


def test_explain_placement_is_deterministic_and_does_not_invent_scores() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa_scope(assessed=8, score=0.81))
    core = compute_dimension_readiness(
        ReadinessDimension.CORE_CS,
        [_skill(f"sql-{i}", score=0.52, confidence=0.6, evidence=4) for i in range(4)],
    )
    projects = compute_dimension_readiness(ReadinessDimension.PROJECTS, [])
    interview = compute_dimension_readiness(ReadinessDimension.INTERVIEW, [])
    profile = compute_dimension_readiness(ReadinessDimension.PROFILE, [])
    result = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core, projects, interview, profile],
        requirements=[
            _req(ReadinessDimension.DSA, min_score=0.70, weight=0.4, critical=True),
            _req(ReadinessDimension.CORE_CS, min_score=0.60, weight=0.35, critical=True),
        ],
    )
    sentences = explain_placement(
        has_target=True,
        target_name="Product SDE",
        dimensions=result.dimensions,
        gaps=result.gaps,
    )
    joined = " ".join(sentences)
    assert "above the Product SDE target" in joined
    assert "below the target bar" in joined
    assert "not assessed yet" in joined
    assert "0%" not in joined


def test_explain_placement_without_target() -> None:
    sentences = explain_placement(has_target=False, target_name=None, dimensions=(), gaps=())
    assert sentences == ("Choose a target profile to evaluate readiness.",)
