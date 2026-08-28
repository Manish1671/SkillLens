from uuid import UUID

import pytest
from app.core.enums import AttemptStatus, MasteryStatus
from app.core.security import hash_password
from app.core.services import attempt_service
from app.models.assessment import EvidenceItem, Recommendation, SkillMastery
from app.models.attempt import Attempt
from app.models.placement_action import PlacementAction
from app.models.user import User
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.schemas.attempt import StartAttemptRequest, SubmitAttemptRequest
from app.seed.demo_runner import (
    DEMO_EMAIL,
    DemoSeedError,
    require_demo_password,
    seed_demo_account,
    verify_demo_invariants,
)
from app.seed.demo_script import DEMO_ATTEMPTS
from app.seed.runner import run_seed
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_demo_password_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKILLENS_DEMO_PASSWORD", raising=False)
    with pytest.raises(DemoSeedError, match="SKILLENS_DEMO_PASSWORD is not set"):
        require_demo_password()


def test_demo_seed_is_idempotent_and_uses_real_pipeline(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SKILLENS_DEMO_PASSWORD", "demo-pass-123")
    run_seed(db_session, commit=False)

    other = UserRepository().create(
        db_session,
        email="other@example.com",
        password_hash=hash_password("password123"),
        display_name="Other User",
    )
    problem = ProblemRepository().find_published_by_slug(db_session, "valid-parentheses")
    assert problem is not None
    other_start = attempt_service.start_attempt(
        db_session,
        other,
        StartAttemptRequest(problem_id=problem.id, client_attempt_id="other-1"),
    )
    attempt_service.submit_attempt(
        db_session,
        other,
        UUID(other_start.id),
        SubmitAttemptRequest(is_correct=True, time_spent_seconds=90),
    )

    first = seed_demo_account(db_session, password="demo-pass-123", commit=False)
    verify_demo_invariants(db_session, first)
    demo_id = db_session.scalar(select(User.id).where(User.email == DEMO_EMAIL))
    first_evidence_ids = set(
        db_session.scalars(select(EvidenceItem.id).where(EvidenceItem.user_id == demo_id))
    )

    second = seed_demo_account(db_session, password="demo-pass-123", commit=False)
    verify_demo_invariants(db_session, second)

    assert first["assessed_skills"] == second["assessed_skills"]
    assert first["evidence"] == second["evidence"]
    assert first["recommendations"] == second["recommendations"]
    assert first["dsa_assessed_count"] == second["dsa_assessed_count"]
    assert first["next_action_kind"] == second["next_action_kind"]
    assert first["placement_actions"] == second["placement_actions"]
    assert second["recommendation_state"] != "cold_start"
    assert "cold_start" not in second["next_reason_codes"]
    assert not second["warnings"]

    by_slug = {item.skill_slug: item for item in second["mastery"]}
    for slug in (
        "arrays",
        "hashing",
        "binary-search",
        "two-pointers",
        "linked-lists",
        "trees",
        "sliding-window",
    ):
        skill = by_slug[slug]
        assert skill.status == MasteryStatus.ASSESSED, (
            f"{slug} expected assessed, got {skill.status} "
            f"score={skill.score} evidence={skill.evidence_count}"
        )
        assert skill.score is not None
        assert float(skill.score) > 0.05
        assert skill.evidence_count > 0
        assert skill.last_attempt_at is not None

    two_pointers = float(by_slug["two-pointers"].score or 0)
    assert two_pointers >= 0.45
    window = float(by_slug["sliding-window"].score or 0)
    arrays = float(by_slug["arrays"].score or 0)
    hashing = float(by_slug["hashing"].score or 0)
    assert 0.20 <= window <= 0.60
    assert window < arrays
    assert window < hashing
    assert window < two_pointers
    assert second["weakest_slug"] == "sliding-window"
    assert second["strongest_slug"] == "arrays"
    assert second["dsa_assessed_count"] >= 6
    assert second["dsa_coverage"] >= 0.40
    assert second["dsa_score"] is not None
    assert second["dsa_status"] not in {"not_assessed", "early"}
    assert second["dsa_requirement"] in {"meets", "exceeds"}
    assert second["core_cs_status"] == "not_assessed"
    assert second["core_cs_score"] is None
    assert second["next_action_kind"] == "assess_dimension"
    assert second["next_action_dimension"] == "core_cs"
    assert second["placement_state"] == "early"
    assert second["target_name"] == "Product SDE"
    assert second["focus_slug"] == "sliding-window"
    assert second["recommendation_state"] != "all_candidates_blocked"

    for slug in ("prefix-sum", "graphs", "dynamic-programming"):
        skill = by_slug.get(slug)
        if skill is not None:
            assert skill.status != MasteryStatus.ASSESSED

    demo_user = UserRepository().find_by_email(db_session, DEMO_EMAIL)
    assert demo_user is not None
    assert demo_user.display_name == "Alex"

    demo_attempt_count = db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.user_id == demo_user.id)
    )
    assert demo_attempt_count == len(DEMO_ATTEMPTS)
    client_ids = list(
        db_session.scalars(select(Attempt.client_attempt_id).where(Attempt.user_id == demo_user.id))
    )
    assert len(client_ids) == len(set(client_ids))
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Attempt)
            .where(Attempt.user_id == demo_user.id, Attempt.status == AttemptStatus.IN_PROGRESS)
        )
        == 0
    )

    other_attempts = db_session.scalar(
        select(func.count()).select_from(Attempt).where(Attempt.user_id == other.id)
    )
    assert other_attempts == 1

    demo_evidence = list(
        db_session.scalars(select(EvidenceItem).where(EvidenceItem.user_id == demo_user.id))
    )
    assert demo_evidence
    assert all(item.user_id == demo_user.id for item in demo_evidence)
    types = {item.evidence_type for item in demo_evidence}
    assert "solved_without_hints" in types
    assert "solved_with_hints" in types
    assert "hint_reliance" in types
    assert "failed_attempt" in types
    assert "repeated_failure" in types
    assert "difficulty_mismatch" in types

    evidence_keys = {(item.attempt_id, item.skill_id, item.evidence_type) for item in demo_evidence}
    assert len(evidence_keys) == len(demo_evidence)

    actions = list(
        db_session.scalars(select(PlacementAction).where(PlacementAction.user_id == demo_user.id))
    )
    assert actions
    ranks = [row.rank for row in actions]
    assert len(ranks) == len(set(ranks))
    action_keys = {
        (row.action_kind, row.target_dimension, row.target_skill_id, row.problem_id, row.rank)
        for row in actions
    }
    assert len(action_keys) == len(actions)

    mastery_rows = list(
        db_session.scalars(select(SkillMastery).where(SkillMastery.user_id == demo_user.id))
    )
    assert mastery_rows
    assert all(row.user_id == demo_user.id for row in mastery_rows)

    recs = list(
        db_session.scalars(select(Recommendation).where(Recommendation.user_id == demo_user.id))
    )
    assert recs
    assert all(row.user_id == demo_user.id for row in recs)
    assert any(row.explanation.get("reason_codes") for row in recs)

    second_ids = set(
        db_session.scalars(select(EvidenceItem.id).where(EvidenceItem.user_id == demo_user.id))
    )
    assert first_evidence_ids.isdisjoint(second_ids)


def test_demo_profile_is_available_via_api(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from collections.abc import Generator as Gen

    from app.core.database import get_db
    from app.main import app

    monkeypatch.setenv("SKILLENS_DEMO_PASSWORD", "demo-pass-123")
    run_seed(db_session, commit=False)
    seed_demo_account(db_session, password="demo-pass-123", commit=False)

    def override_get_db() -> Gen[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/auth/login",
                json={"email": DEMO_EMAIL, "password": "demo-pass-123"},
            )
            assert login.status_code == 200
            mastery = client.get("/api/me/mastery")
            assert mastery.status_code == 200
            items = mastery.json()["items"]
            assert items
            nxt = client.get("/api/me/recommendations/next")
            assert nxt.status_code == 200
            body = nxt.json()
            assert body["recommendation"] is not None
            assert body["state"] != "cold_start"
            assert "cold_start" not in body["recommendation"]["explanation"]["reason_codes"]
            assert body["target_skill"]["skill_slug"] == "sliding-window"
            assert body["target_skill"]["status"] == "assessed"
            assert body["target_skill"]["score"] is not None
            assert float(body["target_skill"]["score"]) > 0.05
            history = client.get("/api/me/history")
            assert history.status_code == 200
            history_body = history.json()
            assert len(history_body["items"]) <= 20
            if len(DEMO_ATTEMPTS) > 20:
                assert history_body["has_more"] is True
            full_history = client.get("/api/me/history", params={"limit": len(DEMO_ATTEMPTS)})
            assert full_history.status_code == 200
            assert len(full_history.json()["items"]) == len(DEMO_ATTEMPTS)
            detail = client.get("/api/me/skills/sliding-window")
            assert detail.status_code == 200
            assert detail.json()["evidence_timeline"]
            readiness = client.get("/api/me/readiness")
            assert readiness.status_code == 200
            ready = readiness.json()
            assert ready["target"]["name"] == "Product SDE"
            assert ready["state"] == "early"
            dims = {item["key"]: item for item in ready["dimensions"]}
            assert dims["dsa"]["score"] is not None
            assert dims["dsa"]["assessed_count"] >= 6
            assert dims["dsa"]["coverage"] >= 0.40
            assert dims["core_cs"]["status"] == "not_assessed"
            assert dims["core_cs"]["score"] is None
            assert dims["projects"]["status"] == "not_assessed"
            gaps = client.get("/api/me/gaps")
            assert gaps.status_code == 200
            actions = client.get("/api/me/actions")
            assert actions.status_code == 200
            assert actions.json()["items"]
            kinds = [item["action_kind"] for item in actions.json()["items"]]
            ranks = [item["rank"] for item in actions.json()["items"]]
            assert len(ranks) == len(set(ranks))
            assert "assess_dimension" in kinds
            nxt_action = client.get("/api/me/actions/next")
            assert nxt_action.status_code == 200
            action = nxt_action.json()["action"]
            assert action is not None
            assert action["action_kind"] == "assess_dimension"
            assert action["target_dimension"] == "core_cs"
            why_text = " ".join(action["why"]).lower()
            codes = " ".join(action["reason_codes"]).lower()
            assert "core cs" in why_text or "insufficient_evidence" in codes
    finally:
        app.dependency_overrides.clear()
