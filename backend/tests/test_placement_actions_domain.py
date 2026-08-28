from app.core.enums import (
    MasteryStatus,
    PlacementActionKind,
    ReadinessDimension,
)
from app.domain.placement_actions import (
    PlacementActionCandidate,
    attach_problem,
    batch_fingerprint,
    effort_fit_score,
    generate_candidates,
    rank_placement_actions,
    score_and_rank,
    score_placement_action,
)
from app.domain.readiness import (
    SkillReadinessInput,
    TargetRequirementInput,
    compute_dimension_readiness,
    compute_placement_readiness,
)


def _skill(
    slug: str,
    *,
    score: float = 0.8,
    confidence: float = 0.6,
    evidence: int = 4,
    name: str | None = None,
) -> SkillReadinessInput:
    return SkillReadinessInput(
        skill_slug=slug,
        skill_name=name or slug.replace("-", " ").title(),
        status=MasteryStatus.ASSESSED,
        score=score,
        confidence=confidence,
        evidence_count=evidence,
    )


def _dsa(score: float = 0.81, assessed: int = 8) -> list[SkillReadinessInput]:
    skills: list[SkillReadinessInput] = []
    for index in range(14):
        slug = f"dsa-{index:02d}"
        if index < assessed:
            skills.append(_skill(slug, score=score if index else min(1.0, score + 0.05)))
        else:
            skills.append(
                SkillReadinessInput(
                    skill_slug=slug,
                    skill_name=slug,
                    status=MasteryStatus.INSUFFICIENT,
                    score=None,
                    confidence=0.1,
                    evidence_count=0,
                )
            )
    return skills


def _core(score: float = 0.52, count: int = 4) -> list[SkillReadinessInput]:
    names = ["SQL Basics", "SQL Joins", "Normalization", "Indexing", "Transactions"]
    slugs = ["sql-basics", "sql-joins", "normalization", "indexing", "transactions"]
    skills: list[SkillReadinessInput] = []
    for index, (slug, name) in enumerate(zip(slugs, names, strict=True)):
        if index < count:
            skill_score = score - 0.1 if slug == "transactions" and count >= 4 else score
            skills.append(_skill(slug, score=max(0.05, skill_score), name=name))
        else:
            skills.append(
                SkillReadinessInput(
                    skill_slug=slug,
                    skill_name=name,
                    status=MasteryStatus.INSUFFICIENT,
                    score=None,
                    confidence=0.1,
                    evidence_count=0,
                )
            )
    return skills


def _req(dimension: ReadinessDimension, min_score: float, weight: float, critical: bool = True):
    return TargetRequirementInput(
        dimension=dimension,
        skill_slug=None,
        skill_name=None,
        min_score=min_score,
        min_confidence=0.5,
        weight=weight,
        is_critical=critical,
    )


def _placement(
    *, dsa_score=0.81, core_score=0.52, core_count=4, dsa_w=0.4, core_w=0.35, core_critical=True
):
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa(dsa_score))
    core = compute_dimension_readiness(ReadinessDimension.CORE_CS, _core(core_score, core_count))
    return compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core],
        requirements=[
            _req(ReadinessDimension.DSA, 0.70, dsa_w, True),
            _req(ReadinessDimension.CORE_CS, 0.60, core_w, core_critical),
        ],
    )


def test_critical_gap_outranks_noncritical_gap() -> None:
    placement = _placement(
        dsa_score=0.50, core_score=0.52, dsa_w=0.2, core_w=0.5, core_critical=True
    )
    ranked = score_and_rank(generate_candidates(placement, target_name="Product SDE"))
    assert ranked[0].candidate.target_dimension == ReadinessDimension.CORE_CS
    assert ranked[0].candidate.is_critical


def test_insufficient_critical_dimension_produces_assess_action() -> None:
    dsa = compute_dimension_readiness(ReadinessDimension.DSA, _dsa(0.81))
    core = compute_dimension_readiness(ReadinessDimension.CORE_CS, [])
    placement = compute_placement_readiness(
        has_target=True,
        dimensions=[dsa, core],
        requirements=[
            _req(ReadinessDimension.DSA, 0.70, 0.4),
            _req(ReadinessDimension.CORE_CS, 0.60, 0.35),
        ],
    )
    candidates = generate_candidates(placement, target_name="Product SDE")
    kinds = {item.action_kind for item in candidates}
    assert PlacementActionKind.ASSESS_DIMENSION in kinds
    assess = next(
        item for item in candidates if item.action_kind == PlacementActionKind.ASSESS_DIMENSION
    )
    assert assess.target_dimension == ReadinessDimension.CORE_CS
    ranked = score_and_rank(candidates)
    assert ranked[0].candidate.action_kind == PlacementActionKind.ASSESS_DIMENSION


def test_dsa_gap_produces_dsa_problem_candidate() -> None:
    placement = _placement(dsa_score=0.50, core_score=0.72, core_count=4)
    candidates = generate_candidates(placement, target_name="Intern SDE")
    dsa = next(item for item in candidates if item.action_kind == PlacementActionKind.DSA_PROBLEM)
    assert dsa.target_dimension == ReadinessDimension.DSA
    assert "Intern SDE" not in dsa.stable_key


def test_core_cs_gap_produces_cs_quiz_candidate() -> None:
    placement = _placement(dsa_score=0.81, core_score=0.52)
    candidates = generate_candidates(placement, target_name="Product SDE")
    quiz = next(item for item in candidates if item.action_kind == PlacementActionKind.CS_QUIZ)
    assert quiz.target_skill_slug is not None
    assert quiz.target_dimension == ReadinessDimension.CORE_CS


def test_target_weight_affects_ranking() -> None:
    heavy = _placement(dsa_score=0.50, core_score=0.50, dsa_w=0.2, core_w=0.7)
    light = _placement(dsa_score=0.50, core_score=0.50, dsa_w=0.7, core_w=0.2)
    heavy_ranked = score_and_rank(
        generate_candidates(heavy, target_name="A", include_dsa_polish=False)
    )
    light_ranked = score_and_rank(
        generate_candidates(light, target_name="A", include_dsa_polish=False)
    )
    assert heavy_ranked[0].candidate.target_dimension == ReadinessDimension.CORE_CS
    assert light_ranked[0].candidate.target_dimension == ReadinessDimension.DSA


def test_effort_fit_affects_ranking() -> None:
    placement = _placement(dsa_score=0.81, core_score=0.52)
    base = generate_candidates(placement, target_name="T")
    quiz = next(item for item in base if item.action_kind == PlacementActionKind.CS_QUIZ)
    tight = attach_problem(
        quiz,
        problem_id="1",
        problem_slug="short-quiz",
        problem_title="Short",
        estimated_effort_minutes=10,
    )
    long = attach_problem(
        quiz,
        problem_id="2",
        problem_slug="long-quiz",
        problem_title="Long",
        estimated_effort_minutes=90,
    )
    ranked = score_and_rank([tight, long])
    assert ranked[0].candidate.problem_slug == "short-quiz"
    assert effort_fit_score(10) > effort_fit_score(90)


def test_prerequisite_readiness_affects_ranking() -> None:
    placement = _placement(dsa_score=0.81, core_score=0.52)
    quiz = next(
        item
        for item in generate_candidates(placement, target_name="T")
        if item.action_kind == PlacementActionKind.CS_QUIZ
    )
    ready = PlacementActionCandidate(
        **{**quiz.__dict__, "prerequisite_ready": 1.0, "stable_key": "a:ready"}
    )
    blocked = PlacementActionCandidate(
        **{**quiz.__dict__, "prerequisite_ready": 0.0, "stable_key": "b:blocked"}
    )
    ranked = score_and_rank([blocked, ready])
    assert ranked[0].candidate.stable_key == "a:ready"


def test_deterministic_ranking_and_tie_breaking() -> None:
    placement = _placement()
    first = score_and_rank(generate_candidates(placement, target_name="Product SDE"))
    second = score_and_rank(generate_candidates(placement, target_name="Product SDE"))
    assert [item.candidate.stable_key for item in first] == [
        item.candidate.stable_key for item in second
    ]
    assert batch_fingerprint(first) == batch_fingerprint(second)
    twin_a = PlacementActionCandidate(
        **{**first[0].candidate.__dict__, "stable_key": "aaa", "prerequisite_ready": 1.0}
    )
    twin_b = PlacementActionCandidate(
        **{**first[0].candidate.__dict__, "stable_key": "zzz", "prerequisite_ready": 1.0}
    )
    tied = rank_placement_actions([score_placement_action(twin_b), score_placement_action(twin_a)])
    assert tied[0].candidate.stable_key == "aaa"


def test_no_eligible_action() -> None:
    empty = compute_dimension_readiness(ReadinessDimension.PROJECTS, [])
    placement = compute_placement_readiness(
        has_target=True,
        dimensions=[empty],
        requirements=[_req(ReadinessDimension.PROJECTS, 0.5, 0.1, False)],
    )
    assert generate_candidates(placement, target_name="T") == []
    assert score_and_rank([]) == []


def test_explanation_reason_codes() -> None:
    placement = _placement(dsa_score=0.81, core_score=0.52)
    ranked = score_and_rank(generate_candidates(placement, target_name="Product SDE"))
    top = next(item for item in ranked if item.candidate.action_kind == PlacementActionKind.CS_QUIZ)
    assert "critical_dimension_gap" in top.reason_codes
    assert "cs_weak_skill" in top.reason_codes
    assert len(top.explanation) <= 3
    assert any("Product SDE" in line for line in top.explanation)
    assert "0.28" not in " ".join(top.explanation)


def test_stable_repeated_calculation() -> None:
    placement = _placement()
    keys = [
        tuple(
            item.candidate.stable_key
            for item in score_and_rank(generate_candidates(placement, target_name="T"))
        )
        for _ in range(5)
    ]
    assert len(set(keys)) == 1
