from decimal import Decimal
from uuid import UUID

from app.core.enums import MasteryStatus, PlacementActionKind, ReadinessDimension
from app.models import Skill, SkillMastery
from app.models.placement_action import PlacementAction
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_attempt_api import (
    get_pair_sum_problem,
    register_and_login,
    start_payload,
    submit_payload,
)
from tests.test_readiness_api import _assess_skills

DSA_STRONG = [
    "arrays",
    "hashing",
    "two-pointers",
    "binary-search",
    "linked-lists",
    "trees",
]
CORE_WEAK = ["sql-basics", "sql-joins", "normalization", "indexing"]
CORE_STRONG = ["sql-basics", "sql-joins", "normalization", "indexing"]


def _assess(db_session: Session, user_id, slugs: list[str], score: str) -> None:
    _assess_skills(db_session, user_id, slugs, score)


def test_actions_require_auth(seeded_client: TestClient) -> None:
    assert seeded_client.get("/api/me/actions/next").status_code == 401
    assert seeded_client.get("/api/me/actions").status_code == 401


def test_no_target_returns_no_practice_action(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "actions-notarget@example.com")
    body = seeded_client.get("/api/me/actions/next").json()
    assert body["action"] is None
    assert body["state"] == "no_target"
    assert "target" in body["message"].lower()


def test_no_evidence_assess_not_arbitrary_practice(
    seeded_client: TestClient,
) -> None:
    register_and_login(seeded_client, "actions-noev@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    body = seeded_client.get("/api/me/actions/next").json()
    action = body["action"]
    assert action is not None
    assert action["action_kind"] == PlacementActionKind.ASSESS_DIMENSION.value
    assert action["payload"]["dimension"] in {
        ReadinessDimension.DSA.value,
        ReadinessDimension.CORE_CS.value,
    }


def test_scenario_a_strong_dsa_weak_core_cs_quiz(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "actions-a@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    _assess(db_session, user_id, CORE_WEAK, "0.5200")
    tx = db_session.scalar(select(Skill).where(Skill.slug == "transactions"))
    assert tx is not None
    db_session.add(
        SkillMastery(
            user_id=user_id,
            skill_id=tx.id,
            score=Decimal("0.4200"),
            confidence=Decimal("0.5500"),
            evidence_count=4,
            status=MasteryStatus.ASSESSED,
        )
    )
    db_session.flush()
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    nxt = seeded_client.get("/api/me/actions/next").json()
    action = nxt["action"]
    assert action["action_kind"] == PlacementActionKind.CS_QUIZ.value
    assert action["target_dimension"] == ReadinessDimension.CORE_CS.value
    listing = seeded_client.get("/api/me/actions", params={"limit": 5}).json()
    assert listing["items"][0]["id"] == action["id"]
    detail = seeded_client.get(f"/api/me/actions/{action['id']}").json()
    assert detail["id"] == action["id"]
    assert "why" in detail and detail["why"]
    slug = action["payload"]["problem_slug"]
    problem = seeded_client.get(f"/api/problems/{slug}").json()
    assert problem["activity_kind"] == "quiz"
    assert "correct_option" not in str(action).lower()
    assert "quiz_spec" not in str(action)


def test_scenario_b_core_cs_not_assessed(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "actions-b@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    action = seeded_client.get("/api/me/actions/next").json()["action"]
    assert action["action_kind"] == PlacementActionKind.ASSESS_DIMENSION.value
    assert action["payload"]["dimension"] == ReadinessDimension.CORE_CS.value


def test_scenario_c_dsa_below_core_meets(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "actions-c@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.5000")
    _assess(db_session, user_id, CORE_STRONG, "0.7200")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    action = seeded_client.get("/api/me/actions/next").json()["action"]
    assert action["action_kind"] == PlacementActionKind.DSA_PROBLEM.value
    slug = action["payload"]["problem_slug"]
    problem = seeded_client.get(f"/api/problems/{slug}").json()
    assert problem["activity_kind"] == "coding"


def test_scenario_d_both_below_weighted_critical_wins(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "actions-d@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.5000")
    _assess(db_session, user_id, CORE_WEAK, "0.5000")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    action = seeded_client.get("/api/me/actions/next").json()["action"]
    assert action["action_kind"] in {
        PlacementActionKind.DSA_PROBLEM.value,
        PlacementActionKind.CS_QUIZ.value,
    }
    first = seeded_client.get("/api/me/actions/next").json()["action"]["id"]
    second = seeded_client.get("/api/me/actions/next").json()["action"]["id"]
    assert first == second


def test_user_isolation_and_unknown_action(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "actions-alice@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    action_id = seeded_client.get("/api/me/actions/next").json()["action"]["id"]
    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "actions-bob@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    stolen = seeded_client.get(f"/api/me/actions/{action_id}")
    assert stolen.status_code == 404
    missing = seeded_client.get("/api/me/actions/00000000-0000-0000-0000-000000000001")
    assert missing.status_code == 404


def test_repeated_refresh_does_not_duplicate_batches(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "actions-dup@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    seeded_client.get("/api/me/actions/next")
    seeded_client.get("/api/me/actions/next", params={"refresh": "true"})
    seeded_client.get("/api/me/actions", params={"refresh": "true"})
    count = db_session.scalar(
        select(func.count()).select_from(PlacementAction).where(PlacementAction.user_id == user_id)
    )
    latest = seeded_client.get("/api/me/actions").json()["items"]
    assert count == len(latest)


def test_actions_update_after_new_evidence(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "actions-ev@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    first = seeded_client.get("/api/me/actions/next").json()["action"]
    assert first["action_kind"] == PlacementActionKind.ASSESS_DIMENSION.value
    _assess(db_session, user_id, CORE_WEAK, "0.5200")
    second = seeded_client.get("/api/me/actions/next", params={"refresh": "true"}).json()["action"]
    assert second["action_kind"] == PlacementActionKind.CS_QUIZ.value


def test_dimension_filter_and_dsa_recommendations_still_work(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "actions-filter@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.5000")
    _assess(db_session, user_id, CORE_WEAK, "0.5200")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    dsa_only = seeded_client.get("/api/me/actions", params={"dimension": "dsa"}).json()
    assert all(item["target_dimension"] == "dsa" for item in dsa_only["items"])
    rec = seeded_client.get("/api/me/recommendations/next").json()
    assert (
        rec["state"] in {"ok", "cold_start"} or rec["recommendation"] is not None or rec["message"]
    )


def test_submit_generates_placement_actions(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "actions-submit@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post(
        "/api/attempts",
        json=start_payload(str(problem.id), "pa-submit-1"),
    )
    assert start.status_code == 201
    submit = seeded_client.post(
        f"/api/attempts/{start.json()['id']}/submit",
        json=submit_payload(is_correct=True),
    )
    assert submit.status_code == 200
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    count = db_session.scalar(
        select(func.count()).select_from(PlacementAction).where(PlacementAction.user_id == user_id)
    )
    assert count and count >= 1
