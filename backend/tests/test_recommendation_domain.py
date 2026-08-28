from datetime import UTC, datetime, timedelta

from app.core.enums import Difficulty, MasteryStatus
from app.domain.recommendation import (
    REASON_COLD_START,
    REASON_PREREQUISITE_BLOCKED,
    REASON_PREREQUISITE_READY,
    REASON_WEAK_SKILL,
    CandidateProblemInput,
    PrerequisiteInput,
    SkillMasteryInput,
    TargetSkillSelection,
    build_explanation_payload,
    difficulty_fit_score,
    evaluate_prerequisite_readiness,
    generate_explanation_sentences,
    novelty_score,
    rank_candidates,
    score_candidate,
    select_target_skill,
    spacing_score,
)


def _skill(
    slug: str,
    *,
    score: float | None = None,
    status: MasteryStatus = MasteryStatus.INSUFFICIENT,
    is_foundational: bool = False,
    sort_order: int = 10,
    problem_count: int = 3,
) -> SkillMasteryInput:
    return SkillMasteryInput(
        skill_id=f"id-{slug}",
        skill_slug=slug,
        skill_name=slug.replace("-", " ").title(),
        is_foundational=is_foundational,
        sort_order=sort_order,
        score=score,
        confidence=0.5,
        status=status,
        problem_count=problem_count,
    )


def _target(slug: str = "hashing", **kwargs) -> TargetSkillSelection:
    skill = _skill(slug, **kwargs)
    return TargetSkillSelection(
        skill_id=skill.skill_id,
        skill_slug=skill.skill_slug,
        skill_name=skill.skill_name,
        score=skill.score,
        confidence=skill.confidence,
        status=skill.status,
        selection_reason=kwargs.get("selection_reason", REASON_WEAK_SKILL),
    )


def _candidate(**kwargs) -> CandidateProblemInput:
    defaults = {
        "problem_id": "p1",
        "problem_slug": "problem-a",
        "title": "Problem A",
        "difficulty": Difficulty.EASY,
        "estimated_minutes": 20,
        "target_skill_weight": 1.0,
        "is_primary_for_target": True,
        "attempted": False,
        "solved": False,
        "in_progress": False,
        "last_success_at": None,
        "reference": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return CandidateProblemInput(**defaults)


def test_select_weakest_assessed_skill() -> None:
    skills = [
        _skill("hashing", score=0.8, status=MasteryStatus.ASSESSED),
        _skill("two-pointers", score=0.35, status=MasteryStatus.ASSESSED),
        _skill("sliding-window", score=0.5, status=MasteryStatus.ASSESSED),
    ]
    result = select_target_skill(skills)
    assert result is not None
    assert result.skill_slug == "two-pointers"
    assert result.selection_reason == REASON_WEAK_SKILL


def test_cold_start_foundational_skill() -> None:
    skills = [
        _skill("hashing", status=MasteryStatus.INSUFFICIENT, problem_count=2),
        _skill("arrays", is_foundational=True, sort_order=10, problem_count=3),
        _skill("trees", is_foundational=True, sort_order=100, problem_count=2),
    ]
    result = select_target_skill(skills)
    assert result is not None
    assert result.skill_slug == "arrays"
    assert result.selection_reason == REASON_COLD_START


def test_prerequisite_blocked() -> None:
    prereqs = [
        PrerequisiteInput(
            prerequisite_skill_id="p1",
            prerequisite_slug="two-pointers",
            prerequisite_name="Two Pointers",
            score=0.3,
            status=MasteryStatus.ASSESSED,
        )
    ]
    readiness, eligible, codes = evaluate_prerequisite_readiness(prereqs)
    assert readiness == 0.0
    assert eligible is False
    assert REASON_PREREQUISITE_BLOCKED in codes


def test_prerequisite_ready() -> None:
    prereqs = [
        PrerequisiteInput(
            prerequisite_skill_id="p1",
            prerequisite_slug="two-pointers",
            prerequisite_name="Two Pointers",
            score=0.6,
            status=MasteryStatus.ASSESSED,
        )
    ]
    readiness, eligible, codes = evaluate_prerequisite_readiness(prereqs)
    assert eligible is True
    assert readiness > 0.0
    assert REASON_PREREQUISITE_READY in codes


def test_easy_difficulty_fit_for_weak_skill() -> None:
    score = difficulty_fit_score(0.3, 0.4, MasteryStatus.ASSESSED, Difficulty.EASY)
    assert score == 1.0
    hard = difficulty_fit_score(0.3, 0.4, MasteryStatus.ASSESSED, Difficulty.HARD)
    assert hard < score


def test_medium_difficulty_fit_for_moderate_skill() -> None:
    medium = difficulty_fit_score(0.55, 0.6, MasteryStatus.ASSESSED, Difficulty.MEDIUM)
    easy = difficulty_fit_score(0.55, 0.6, MasteryStatus.ASSESSED, Difficulty.EASY)
    assert medium >= easy


def test_hard_difficulty_fit_for_strong_skill() -> None:
    hard = difficulty_fit_score(0.8, 0.7, MasteryStatus.ASSESSED, Difficulty.HARD)
    easy = difficulty_fit_score(0.8, 0.7, MasteryStatus.ASSESSED, Difficulty.EASY)
    assert hard > easy


def test_novelty_prefers_never_attempted() -> None:
    never = novelty_score(_candidate(attempted=False))
    attempted = novelty_score(_candidate(attempted=True, solved=False))
    solved = novelty_score(
        _candidate(
            attempted=True,
            solved=True,
            last_success_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    assert never > attempted > solved


def test_spaced_review_bonus() -> None:
    recent = spacing_score(
        _candidate(
            solved=True,
            last_success_at=datetime.now(UTC) - timedelta(days=3),
        )
    )
    old = spacing_score(
        _candidate(
            solved=True,
            last_success_at=datetime.now(UTC) - timedelta(days=45),
        )
    )
    assert old > recent


def test_primary_skill_weight_stronger() -> None:
    target = _target("hashing", score=0.4, status=MasteryStatus.ASSESSED)
    primary = score_candidate(
        _candidate(target_skill_weight=1.0, is_primary_for_target=True),
        target,
        1.0,
        True,
    )
    supporting = score_candidate(
        _candidate(target_skill_weight=0.4, is_primary_for_target=False),
        target,
        1.0,
        True,
    )
    assert primary is not None and supporting is not None
    assert primary.components.final_score > supporting.components.final_score


def test_deterministic_score() -> None:
    target = _target("hashing", score=0.4, status=MasteryStatus.ASSESSED)
    candidate = _candidate()
    first = score_candidate(candidate, target, 1.0, True)
    second = score_candidate(candidate, target, 1.0, True)
    assert first is not None and second is not None
    assert first.components.final_score == second.components.final_score


def test_deterministic_ordering() -> None:
    target = _target("hashing", score=0.4, status=MasteryStatus.ASSESSED)
    a = score_candidate(_candidate(problem_slug="aaa"), target, 1.0, True)
    b = score_candidate(
        _candidate(problem_slug="bbb", difficulty=Difficulty.MEDIUM), target, 1.0, True
    )
    assert a is not None and b is not None
    ranked = rank_candidates([b, a])
    ranked2 = rank_candidates([b, a])
    assert [item.problem_slug for item in ranked] == [item.problem_slug for item in ranked2]


def test_explanation_reason_codes() -> None:
    target = _target("sliding-window", score=0.35, status=MasteryStatus.ASSESSED)
    candidate = score_candidate(_candidate(), target, 1.0, True)
    assert candidate is not None
    payload = build_explanation_payload(target, candidate, [])
    assert "target_skill" in payload
    assert REASON_WEAK_SKILL in payload["reason_codes"]
    assert len(payload["sentences"]) >= 2


def test_no_eligible_in_progress_excluded() -> None:
    target = _target("hashing", score=0.4, status=MasteryStatus.ASSESSED)
    result = score_candidate(_candidate(in_progress=True), target, 1.0, True)
    assert result is None


def test_explanation_sentences_cold_start() -> None:
    target = TargetSkillSelection(
        skill_id="id-arrays",
        skill_slug="arrays",
        skill_name="Arrays",
        score=None,
        confidence=0.0,
        status=MasteryStatus.INSUFFICIENT,
        selection_reason=REASON_COLD_START,
    )
    candidate = score_candidate(_candidate(), target, 1.0, True)
    assert candidate is not None
    sentences = generate_explanation_sentences(target, candidate, [])
    assert any("foundational" in s.lower() for s in sentences)
