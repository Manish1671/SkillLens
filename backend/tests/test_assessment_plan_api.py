from uuid import UUID

from app.core.enums import ActivityKind, PlacementActionKind
from app.models.assessment import EvidenceItem, SkillMastery
from app.models.attempt import Attempt
from app.models.problem import Problem
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_attempt_api import register_and_login, start_payload, submit_payload
from tests.test_core_cs_api import _correct_option
from tests.test_placement_actions_api import CORE_STRONG, DSA_STRONG, _assess


def _set_target(client: TestClient) -> None:
    response = client.put("/api/me/target", json={"profile_slug": "product-sde"})
    assert response.status_code == 200


def test_plan_requires_authentication(seeded_client: TestClient) -> None:
    assert seeded_client.get("/api/me/assessment/plan").status_code == 401


def test_plan_no_target(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "plan-notarget@example.com")
    body = seeded_client.get("/api/me/assessment/plan").json()
    assert body["state"] == "no_target"
    assert body["items"] == []
    assert body["assessment_id"] is None
    assert "target" in body["message"].lower()


def test_plan_respects_target_and_is_deterministic(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "plan-det@example.com")
    _set_target(seeded_client)
    first = seeded_client.get("/api/me/assessment/plan").json()
    second = seeded_client.get("/api/me/assessment/plan").json()
    assert first["state"] == "ok"
    assert first["target"]["slug"] == "product-sde"
    assert 10 <= first["total_items"] <= 12
    assert first["assessment_id"] == second["assessment_id"]
    assert [item["problem_slug"] for item in first["items"]] == [
        item["problem_slug"] for item in second["items"]
    ]
    kinds = {item["activity_kind"] for item in first["items"]}
    assert ActivityKind.CODING.value in kinds
    assert ActivityKind.QUIZ.value in kinds


def test_plan_contains_published_problems_only(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "plan-pub@example.com")
    _set_target(seeded_client)
    body = seeded_client.get("/api/me/assessment/plan").json()
    slugs = [item["problem_slug"] for item in body["items"]]
    rows = list(db_session.scalars(select(Problem).where(Problem.slug.in_(slugs))).all())
    assert len(rows) == len(slugs)
    assert all(row.is_published for row in rows)


def test_plan_hides_quiz_answer_keys(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "plan-keys@example.com")
    _set_target(seeded_client)
    raw = seeded_client.get("/api/me/assessment/plan").text.lower()
    assert "correct_option" not in raw
    assert "quiz_spec" not in raw
    assert "solution_outline" not in raw


def test_scenario_a_new_user_mixed_plan(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "plan-a@example.com")
    _set_target(seeded_client)
    body = seeded_client.get("/api/me/assessment/plan").json()
    dsa = [item for item in body["items"] if item["dimension"] == "dsa"]
    cs = [item for item in body["items"] if item["dimension"] == "core_cs"]
    assert 6 <= len(dsa) <= 8
    assert 4 <= len(cs) <= 5
    assert all(item["activity_kind"] == "coding" for item in dsa)
    assert all(item["activity_kind"] == "quiz" for item in cs)


def test_scenario_b_strong_dsa_weak_core_cs_focus(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "plan-b@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    _set_target(seeded_client)
    body = seeded_client.get("/api/me/assessment/plan").json()
    dsa = [item for item in body["items"] if item["dimension"] == "dsa"]
    cs = [item for item in body["items"] if item["dimension"] == "core_cs"]
    assert len(cs) >= len(dsa) or len(cs) == 5
    assert len(cs) == 5


def test_scenario_c_strong_core_cs_weak_dsa_focus(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "plan-c@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, CORE_STRONG, "0.8000")
    tx = db_session.scalar(select(Problem).where(Problem.slug == "txn-acid"))
    assert tx is not None
    _assess(db_session, user_id, ["transactions"], "0.8000")
    _set_target(seeded_client)
    body = seeded_client.get("/api/me/assessment/plan").json()
    dsa = [item for item in body["items"] if item["dimension"] == "dsa"]
    cs = [item for item in body["items"] if item["dimension"] == "core_cs"]
    assert len(dsa) > len(cs)


def test_user_specific_evidence_affects_planning(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "plan-u1@example.com")
    _set_target(seeded_client)
    cold = seeded_client.get("/api/me/assessment/plan").json()
    register_and_login(seeded_client, "plan-u2@example.com")
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    _assess(db_session, user_id, DSA_STRONG, "0.8100")
    _set_target(seeded_client)
    hot = seeded_client.get("/api/me/assessment/plan").json()
    assert [item["problem_slug"] for item in cold["items"]] != [
        item["problem_slug"] for item in hot["items"]
    ]
    hot_cs = sum(1 for item in hot["items"] if item["dimension"] == "core_cs")
    cold_cs = sum(1 for item in cold["items"] if item["dimension"] == "core_cs")
    assert hot_cs >= cold_cs


def _submit_item(client: TestClient, db_session: Session, item: dict, client_id: str) -> None:
    problem = db_session.scalar(select(Problem).where(Problem.slug == item["problem_slug"]))
    assert problem is not None
    start = client.post("/api/attempts", json=start_payload(str(problem.id), client_id))
    assert start.status_code == 201
    attempt_id = start.json()["id"]
    if item["activity_kind"] == "quiz":
        option = _correct_option(item["problem_slug"])
        response = client.post(
            f"/api/attempts/{attempt_id}/submit",
            json={"selected_option": option, "time_spent_seconds": 15},
        )
    else:
        response = client.post(
            f"/api/attempts/{attempt_id}/submit",
            json=submit_payload(True, time_spent_seconds=20),
        )
    assert response.status_code == 200


def test_scenario_d_complete_assessment_writes_readiness(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "plan-d@example.com")
    _set_target(seeded_client)
    plan = seeded_client.get("/api/me/assessment/plan").json()
    for item in plan["items"]:
        _submit_item(
            seeded_client,
            db_session,
            item,
            f"plan-d-{item['position']}",
        )
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    mastery_count = db_session.scalar(
        select(func.count()).select_from(SkillMastery).where(SkillMastery.user_id == user_id)
    )
    assert int(mastery_count or 0) >= 6
    evidence_count = db_session.scalar(
        select(func.count()).select_from(EvidenceItem).where(EvidenceItem.user_id == user_id)
    )
    assert int(evidence_count or 0) >= 6
    readiness = seeded_client.get("/api/me/readiness").json()
    assert readiness["target"]["slug"] == "product-sde"
    assert "state" in readiness
    assert len(readiness["dimensions"]) >= 2
    gaps = seeded_client.get("/api/me/gaps").json()
    assert isinstance(gaps["items"], list)
    action = seeded_client.get("/api/me/actions/next").json()
    assert action["action"] is not None
    assert action["action"]["action_kind"] in {kind.value for kind in PlacementActionKind}


def test_scenario_e_refresh_does_not_duplicate_attempts(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "plan-e@example.com")
    _set_target(seeded_client)
    plan = seeded_client.get("/api/me/assessment/plan").json()
    item = plan["items"][0]
    problem = db_session.scalar(select(Problem).where(Problem.slug == item["problem_slug"]))
    assert problem is not None
    payload = start_payload(str(problem.id), "ap-resume-pos1")
    first = seeded_client.post("/api/attempts", json=payload)
    second = seeded_client.post("/api/attempts", json=payload)
    assert first.status_code == 201
    assert second.status_code in {200, 201}
    assert first.json()["id"] == second.json()["id"]
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    count = db_session.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.user_id == user_id, Attempt.problem_id == problem.id)
    )
    assert int(count or 0) == 1


def test_existing_dsa_recommendation_still_works(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "plan-rec@example.com")
    rec = seeded_client.get("/api/me/recommendations/next").json()
    assert (
        rec["state"] in {"ok", "cold_start", "no_eligible_problem"}
        or rec.get("recommendation") is not None
        or rec.get("message") is not None
    )
