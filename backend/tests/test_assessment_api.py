from unittest.mock import patch
from uuid import UUID

import pytest
from app.models.assessment import EvidenceItem, SkillAssessmentSnapshot
from app.repositories.assessment_repository import SnapshotRepository
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
    start = client.post("/api/attempts", json=start_payload(str(problem.id), client_id))
    return start.json()["id"]


def test_successful_submission_creates_evidence(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "ev@example.com", "ev-1")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=200),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assessment"] is not None
    assert len(body["assessment"]["evidence_items"]) > 0


def test_successful_submission_updates_mastery(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "mast@example.com", "mast-1")
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=200),
    )
    mastery = seeded_client.get("/api/me/mastery")
    assert mastery.status_code == 200
    assert len(mastery.json()["items"]) > 0


def test_successful_submission_creates_snapshots(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "snap@example.com", "snap-1")
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=150),
    )
    count = db_session.scalar(select(func.count()).select_from(SkillAssessmentSnapshot))
    assert int(count or 0) > 0


def test_failed_submission_negative_evidence(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "fail@example.com", "fail-1")
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=False, time_spent_seconds=90),
    )
    items = db_session.scalars(select(EvidenceItem)).all()
    assert any(item.polarity.value == "negative" for item in items)


def test_double_submission_no_duplicate_evidence(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "dup@example.com", "dup-1")
    payload = submit_payload(is_correct=True, time_spent_seconds=100)
    seeded_client.post(f"/api/attempts/{attempt_id}/submit", json=payload)
    count_after_first = db_session.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(EvidenceItem.attempt_id == UUID(attempt_id))
    )
    seeded_client.post(f"/api/attempts/{attempt_id}/submit", json=payload)
    count_after_second = db_session.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(EvidenceItem.attempt_id == UUID(attempt_id))
    )
    assert int(count_after_second or 0) == int(count_after_first or 0)


def test_skill_detail_returns_evidence(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "detail@example.com", "det-1")
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=120),
    )
    detail = seeded_client.get("/api/me/skills/hashing")
    assert detail.status_code == 200
    assert len(detail.json()["evidence_timeline"]) > 0
    assert len(detail.json()["snapshots"]) > 0


def test_user_isolation_mastery(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "iso@example.com", "iso-1")
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=100),
    )
    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "other@example.com")
    mastery = seeded_client.get("/api/me/mastery")
    assert mastery.status_code == 200
    assert len(mastery.json()["items"]) == 0


def test_transaction_rollback_on_snapshot_failure(seeded_client: TestClient, db_session) -> None:
    attempt_id = start_and_get_id(seeded_client, db_session, "rollback@example.com", "rb-1")
    with patch.object(SnapshotRepository, "create", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            seeded_client.post(
                f"/api/attempts/{attempt_id}/submit",
                json=submit_payload(is_correct=True, time_spent_seconds=100),
            )
    attempt = seeded_client.get(f"/api/attempts/{attempt_id}")
    assert attempt.json()["attempt"]["status"] == "in_progress"
    evidence_count = db_session.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(EvidenceItem.attempt_id == UUID(attempt_id))
    )
    assert int(evidence_count or 0) == 0


def test_me_mastery_endpoint_requires_auth(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/mastery")
    assert response.status_code == 401


def test_insufficient_skill_no_fake_score(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "cold@example.com")
    mastery = seeded_client.get("/api/me/mastery")
    for item in mastery.json()["items"]:
        if item["status"] == "insufficient":
            assert item["score"] is None
