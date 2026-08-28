import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from app.core.config import settings
from app.core.security import TOKEN_TYPE_ACCESS, create_token_with_expiry
from app.core.startup import validate_production_settings
from app.main import unhandled_exception_handler
from fastapi.testclient import TestClient
from tests.test_attempt_api import register_and_login, start_payload


def test_expired_access_token_rejected(seeded_client: TestClient, db_session) -> None:
    from app.repositories.problem_repository import ProblemRepository

    register_and_login(seeded_client, "expired@example.com")
    user_resp = seeded_client.get("/api/auth/me")
    assert user_resp.status_code == 200
    user_id = user_resp.json()["id"]

    expired = create_token_with_expiry(
        user_id,
        TOKEN_TYPE_ACCESS,
        datetime.now(UTC) - timedelta(minutes=1),
    )
    seeded_client.cookies.set(settings.access_cookie_name, expired)
    problem = ProblemRepository().find_published_by_slug(db_session, "pair-sum-lookup")
    assert problem is not None
    response = seeded_client.get("/api/me/mastery")
    assert response.status_code == 401
    assert response.json()["code"] in ("unauthorized", "invalid_token")


def test_malformed_attempt_id_returns_422(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "malformed@example.com")
    response = seeded_client.get("/api/attempts/not-a-uuid")
    assert response.status_code == 422


def test_unauthorized_mastery_access(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/mastery")
    assert response.status_code == 401


def test_unauthorized_recommendations_access(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/recommendations/next")
    assert response.status_code == 401


def test_idor_attempt_access(seeded_client: TestClient, db_session) -> None:
    from app.repositories.problem_repository import ProblemRepository

    register_and_login(seeded_client, "owner@example.com")
    problem = ProblemRepository().find_published_by_slug(db_session, "pair-sum-lookup")
    assert problem is not None
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "sec-1"))
    attempt_id = start.json()["id"]

    register_and_login(seeded_client, "intruder@example.com")
    response = seeded_client.get(f"/api/attempts/{attempt_id}")
    assert response.status_code == 404


def test_idor_recommendation_detail(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "rec-owner@example.com")
    list_resp = seeded_client.get("/api/me/recommendations?refresh=true")
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("No recommendations generated")
    rec_id = items[0]["id"]

    register_and_login(seeded_client, "rec-intruder@example.com")
    response = seeded_client.get(f"/api/me/recommendations/{rec_id}")
    assert response.status_code == 404


def test_invalid_submit_payload(seeded_client: TestClient, db_session) -> None:
    from app.repositories.problem_repository import ProblemRepository

    register_and_login(seeded_client, "invalid-payload@example.com")
    problem = ProblemRepository().find_published_by_slug(db_session, "pair-sum-lookup")
    assert problem is not None
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "inv-1"))
    attempt_id = start.json()["id"]
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"is_correct": True, "time_spent_seconds": -1},
    )
    assert response.status_code == 422


def test_production_rejects_insecure_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "app_env", "production")
    monkeypatch.setattr(config.settings, "jwt_secret_key", "dev-only-change-in-production")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_production_settings()


def test_internal_error_does_not_leak_details() -> None:
    request = MagicMock()
    response = asyncio.run(
        unhandled_exception_handler(request, RuntimeError("secret database connection failed"))
    )
    assert response.status_code == 500
    body = response.body.decode()
    assert "internal_error" in body
    assert "database" not in body.lower()
    assert "secret" not in body.lower()


def test_normalize_database_url_accepts_hosted_postgres() -> None:
    from app.core.config import normalize_database_url

    assert (
        normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    )
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    already = "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url(already) == already
