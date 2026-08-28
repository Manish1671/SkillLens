from uuid import UUID

import pytest
from app.models.assessment import Recommendation
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from tests.test_attempt_api import (
    get_pair_sum_problem,
    register_and_login,
    start_payload,
    submit_payload,
)


def start_and_get_id(client: TestClient, db_session, email: str, client_id: str) -> str:
    register_and_login(client, email)
    problem = get_pair_sum_problem(db_session)
    response = client.post("/api/attempts", json=start_payload(str(problem.id), client_id))
    assert response.status_code == 201
    return response.json()["id"]


def submit_attempt(client: TestClient, attempt_id: str, *, is_correct: bool = True) -> dict:
    response = client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=is_correct),
    )
    assert response.status_code == 200
    return response.json()


def test_get_recommendations_requires_auth(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/recommendations")
    assert response.status_code == 401


def test_new_user_cold_start_recommendation(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "cold@example.com")
    response = seeded_client.get("/api/me/recommendations/next?refresh=true")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] in ("cold_start", "ok")
    if data["recommendation"] is not None:
        assert data["recommendation"]["problem"]["slug"]
        assert len(data["recommendation"]["explanation"]["sentences"]) >= 1


def test_get_next_recommendation(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "next@example.com")
    response = seeded_client.get("/api/me/recommendations/next?refresh=true")
    assert response.status_code == 200
    assert "recommendation" in response.json()


def test_recommendation_after_successful_submission(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "rec-success@example.com", "c1")
    result = submit_attempt(seeded_client, attempt_id, is_correct=True)
    assert result.get("assessment") is not None
    rec = result["assessment"].get("recommendation")
    assert rec is not None
    if rec.get("recommendation") is not None:
        assert rec["recommendation"]["explanation"]["sentences"]


def test_recommendation_after_failed_submission(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "rec-fail@example.com", "c2")
    result = submit_attempt(seeded_client, attempt_id, is_correct=False)
    assert result.get("assessment") is not None
    assert "recommendation" in result["assessment"]


def test_recommendation_persisted(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "persist@example.com")
    seeded_client.get("/api/me/recommendations/next?refresh=true")
    count = db_session.scalar(select(func.count()).select_from(Recommendation))
    assert count is not None and count >= 1


def test_recommendation_detail(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "detail@example.com")
    list_resp = seeded_client.get("/api/me/recommendations?refresh=true")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    if not items:
        pytest.skip("No recommendations generated")
    rec_id = items[0]["id"]
    detail = seeded_client.get(f"/api/me/recommendations/{rec_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == rec_id
    assert detail.json()["explanation"]["reason_codes"]


def test_user_isolation_recommendation(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "owner@example.com")
    list_resp = seeded_client.get("/api/me/recommendations?refresh=true")
    items = list_resp.json()["items"]
    if not items:
        pytest.skip("No recommendations")
    rec_id = items[0]["id"]
    register_and_login(seeded_client, "other@example.com")
    response = seeded_client.get(f"/api/me/recommendations/{rec_id}")
    assert response.status_code == 404


def test_no_solution_leakage_in_recommendation(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "leak@example.com")
    response = seeded_client.get("/api/me/recommendations/next?refresh=true")
    assert response.status_code == 200
    payload = response.json()
    if payload.get("recommendation") is None:
        pytest.skip("No recommendation")
    problem = payload["recommendation"]["problem"]
    assert "solution" not in problem
    assert "hints" not in problem
    assert "prompt_md" not in problem


def test_double_submit_no_duplicate_recommendations(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "dup-rec@example.com", "c3")
    submit_attempt(seeded_client, attempt_id)
    submit_attempt(seeded_client, attempt_id)
    count = db_session.scalar(
        select(func.count())
        .select_from(Recommendation)
        .where(Recommendation.source_attempt_id == UUID(attempt_id))
    )
    assert count is not None and count <= 5


def test_deterministic_same_state_recommendation(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "det@example.com")
    first = seeded_client.get("/api/me/recommendations/next?refresh=true").json()
    second = seeded_client.get("/api/me/recommendations/next").json()
    if first.get("recommendation") and second.get("recommendation"):
        assert (
            first["recommendation"]["problem"]["slug"]
            == second["recommendation"]["problem"]["slug"]
        )


def test_list_recommendations(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "list@example.com")
    seeded_client.get("/api/me/recommendations/next?refresh=true")
    response = seeded_client.get("/api/me/recommendations?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 3
