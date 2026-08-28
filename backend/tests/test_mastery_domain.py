from datetime import UTC, datetime, timedelta

from app.core.enums import Difficulty, EvidencePolarity, MistakeType
from app.domain.evidence import (
    FAILED_ATTEMPT,
    HINT_RELIANCE,
    SOLVED_WITH_HINTS,
    SOLVED_WITHOUT_HINTS,
    ProblemSkillInput,
    RecentFailureRecord,
    SubmissionContext,
    generate_evidence_drafts,
)
from app.domain.mastery import (
    EFFECTIVE_EVIDENCE_THRESHOLD,
    EvidenceInput,
    apply_prerequisite_cap,
    compute_attempt_credit,
    compute_confidence,
    compute_mastery,
    compute_raw_score,
    recency_weight,
)


def _skill_link(skill_id: str, name: str, weight: float = 1.0) -> ProblemSkillInput:
    return ProblemSkillInput(
        skill_id=skill_id,
        skill_slug=name.lower().replace(" ", "-"),
        skill_name=name,
        weight=weight,
        is_primary=weight >= 1.0,
    )


def _submission(**kwargs) -> SubmissionContext:
    defaults = {
        "problem_id": "p1",
        "problem_slug": "prob",
        "problem_title": "Test Problem",
        "difficulty": Difficulty.MEDIUM,
        "is_correct": True,
        "hints_used_count": 0,
        "mistake_type": None,
        "time_spent_seconds": 120,
    }
    defaults.update(kwargs)
    return SubmissionContext(**defaults)


def test_no_evidence_insufficient() -> None:
    now = datetime.now(UTC)
    result = compute_mastery([], now)
    assert result.status.value == "insufficient"
    assert result.effective_evidence < EFFECTIVE_EVIDENCE_THRESHOLD


def test_successful_no_hint_evidence() -> None:
    drafts = generate_evidence_drafts(
        _submission(is_correct=True, hints_used_count=0),
        [_skill_link("s1", "Hashing")],
        [],
    )
    assert any(d.evidence_type == SOLVED_WITHOUT_HINTS for d in drafts)
    assert all(
        d.polarity == EvidencePolarity.POSITIVE
        for d in drafts
        if d.evidence_type == SOLVED_WITHOUT_HINTS
    )


def test_successful_hinted_evidence() -> None:
    drafts = generate_evidence_drafts(
        _submission(is_correct=True, hints_used_count=1),
        [_skill_link("s1", "Hashing")],
        [],
    )
    assert any(d.evidence_type == SOLVED_WITH_HINTS for d in drafts)


def test_hint_reliance_evidence() -> None:
    drafts = generate_evidence_drafts(
        _submission(is_correct=True, hints_used_count=2),
        [_skill_link("s1", "Hashing")],
        [],
    )
    assert any(d.evidence_type == HINT_RELIANCE for d in drafts)


def test_failed_attempt_evidence() -> None:
    drafts = generate_evidence_drafts(
        _submission(is_correct=False, mistake_type=MistakeType.LOGIC_ERROR),
        [_skill_link("s1", "Hashing")],
        [],
    )
    assert any(d.evidence_type == FAILED_ATTEMPT for d in drafts)


def test_repeated_failure_evidence() -> None:
    recent = [
        RecentFailureRecord(skill_id="s1", problem_id="p1", evidence_type=FAILED_ATTEMPT),
    ]
    drafts = generate_evidence_drafts(
        _submission(is_correct=False),
        [_skill_link("s1", "Hashing")],
        recent,
    )
    assert any(d.evidence_type == "repeated_failure" for d in drafts)


def test_hard_success_stronger_credit_than_easy() -> None:
    easy = compute_attempt_credit(True, "easy", 1.0, 0, 100)
    hard = compute_attempt_credit(True, "hard", 1.0, 0, 100)
    assert hard > easy


def test_easy_failure_stronger_negative_than_hard() -> None:
    easy = compute_attempt_credit(False, "easy", 1.0, 0, 100)
    hard = compute_attempt_credit(False, "hard", 1.0, 0, 100)
    assert easy < hard


def test_hints_reduce_positive_credit() -> None:
    no_hint = compute_attempt_credit(True, "medium", 1.0, 0, 100)
    with_hints = compute_attempt_credit(True, "medium", 1.0, 2, 100)
    assert with_hints < no_hint


def test_recency_weighting() -> None:
    now = datetime.now(UTC)
    recent = recency_weight(now - timedelta(days=1), now)
    old = recency_weight(now - timedelta(days=42), now)
    assert recent > old


def test_bounded_score() -> None:
    now = datetime.now(UTC)
    items = [
        EvidenceInput(EvidencePolarity.POSITIVE, 1.0, now, SOLVED_WITHOUT_HINTS),
    ]
    score = compute_raw_score(items, now)
    assert 0.0 <= score <= 1.0


def test_prerequisite_cap() -> None:
    capped, blocked = apply_prerequisite_cap(0.8, [0.32])
    assert blocked
    assert capped == 0.32


def test_supporting_skill_weaker_than_primary() -> None:
    primary = generate_evidence_drafts(
        _submission(is_correct=True),
        [_skill_link("s1", "Hashing", 1.0)],
        [],
    )
    supporting = generate_evidence_drafts(
        _submission(is_correct=True),
        [_skill_link("s2", "Arrays", 0.4)],
        [],
    )
    assert primary[0].strength > supporting[0].strength


def test_deterministic_repeated_calculation() -> None:
    now = datetime.now(UTC)
    items = [
        EvidenceInput(
            EvidencePolarity.POSITIVE, 0.7, now - timedelta(days=2), SOLVED_WITHOUT_HINTS
        ),
        EvidenceInput(EvidencePolarity.NEGATIVE, 0.6, now - timedelta(days=5), FAILED_ATTEMPT),
    ]
    first = compute_mastery(items, now, [])
    second = compute_mastery(items, now, [])
    assert first.score == second.score
    assert first.confidence == second.confidence


def test_confidence_increases_with_evidence() -> None:
    now = datetime.now(UTC)
    few = [EvidenceInput(EvidencePolarity.POSITIVE, 0.7, now, SOLVED_WITHOUT_HINTS)]
    many = [
        EvidenceInput(EvidencePolarity.POSITIVE, 0.7, now - timedelta(days=i), SOLVED_WITHOUT_HINTS)
        for i in range(5)
    ]
    assert compute_confidence(many, now) > compute_confidence(few, now)


def test_confidence_decreases_with_inconsistency() -> None:
    now = datetime.now(UTC)
    consistent = [
        EvidenceInput(
            EvidencePolarity.POSITIVE, 0.7, now - timedelta(days=1), SOLVED_WITHOUT_HINTS
        ),
        EvidenceInput(
            EvidencePolarity.POSITIVE, 0.7, now - timedelta(days=2), SOLVED_WITHOUT_HINTS
        ),
    ]
    mixed = [
        EvidenceInput(
            EvidencePolarity.POSITIVE, 0.7, now - timedelta(days=1), SOLVED_WITHOUT_HINTS
        ),
        EvidenceInput(EvidencePolarity.NEGATIVE, 0.6, now - timedelta(days=2), FAILED_ATTEMPT),
    ]
    assert compute_confidence(consistent, now) > compute_confidence(mixed, now)
