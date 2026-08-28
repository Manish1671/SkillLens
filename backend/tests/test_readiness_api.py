from decimal import Decimal

from app.core.enums import DimensionStatus, MasteryStatus, PlacementState, ReadinessDimension
from app.models import Skill, SkillMastery
from app.models.readiness import LearnerTarget
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_attempt_api import register_and_login


def _assess_skills(db_session: Session, user_id, slugs: list[str], score: str = "0.8000") -> None:
    skills = list(db_session.scalars(select(Skill).where(Skill.slug.in_(slugs))).all())
    for skill in skills:
        db_session.add(
            SkillMastery(
                user_id=user_id,
                skill_id=skill.id,
                score=Decimal(score),
                confidence=Decimal("0.6000"),
                evidence_count=4,
                status=MasteryStatus.ASSESSED,
            )
        )
    db_session.flush()


def test_target_profile_list(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/target-profiles")
    assert response.status_code == 200
    body = response.json()
    assert "official" in body["disclaimer"].lower()
    slugs = {item["slug"] for item in body["items"]}
    assert "product-sde" in slugs
    product = next(item for item in body["items"] if item["slug"] == "product-sde")
    assert product["name"] == "Product SDE"


def test_get_current_target_requires_auth(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/target")
    assert response.status_code == 401


def test_get_and_set_target(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "target-user@example.com")
    empty = seeded_client.get("/api/me/target")
    assert empty.status_code == 200
    assert empty.json()["profile"] is None

    created = seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    assert created.status_code == 200
    assert created.json()["profile"]["slug"] == "product-sde"
    assert created.json()["selected_at"] is not None

    fetched = seeded_client.get("/api/me/target")
    assert fetched.json()["profile"]["slug"] == "product-sde"


def test_changing_target_replaces_row(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "retarget@example.com")
    first = seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    assert first.status_code == 200
    second = seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    assert second.status_code == 200
    user = seeded_client.get("/api/auth/me").json()
    from uuid import UUID

    rows = list(
        db_session.scalars(select(LearnerTarget).where(LearnerTarget.user_id == UUID(user["id"])))
    )
    assert len(rows) == 1


def test_unknown_target_profile_404(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "missing-profile@example.com")
    response = seeded_client.put("/api/me/target", json={"profile_slug": "not-a-profile"})
    assert response.status_code == 404
    assert response.json()["code"] == "target_profile_not_found"


def test_target_isolated_per_user(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "alice-target@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "bob-target@example.com")
    bob = seeded_client.get("/api/me/target")
    assert bob.json()["profile"] is None
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    assert seeded_client.get("/api/me/target").json()["profile"]["slug"] == "product-sde"


def test_readiness_requires_authentication(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/readiness")
    assert response.status_code == 401


def test_readiness_unassessed_dimensions_are_null(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "ready-empty@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    response = seeded_client.get("/api/me/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] is None
    assert body["state"] == PlacementState.NOT_ASSESSED.value
    by_key = {item["key"]: item for item in body["dimensions"]}
    assert by_key["dsa"]["score"] is None
    assert by_key["core_cs"]["status"] == DimensionStatus.NOT_ASSESSED.value
    assert by_key["core_cs"]["score"] is None
    assert by_key["projects"]["score"] is None
    assert by_key["interview"]["score"] is None
    assert by_key["profile"]["score"] is None


def test_dsa_readiness_returned_and_insufficient_not_zero(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "dsa-ready@example.com")
    user_id = seeded_client.get("/api/auth/me").json()["id"]
    from uuid import UUID

    assessed = [
        "arrays",
        "hashing",
        "two-pointers",
        "binary-search",
        "linked-lists",
        "sliding-window",
    ]
    _assess_skills(db_session, UUID(user_id), assessed, "0.7800")
    graphs = db_session.scalar(select(Skill).where(Skill.slug == "graphs"))
    assert graphs is not None
    db_session.add(
        SkillMastery(
            user_id=UUID(user_id),
            skill_id=graphs.id,
            score=Decimal("0.0000"),
            confidence=Decimal("0.8000"),
            evidence_count=3,
            status=MasteryStatus.INSUFFICIENT,
        )
    )
    db_session.flush()
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    body = seeded_client.get("/api/me/readiness").json()
    dsa = next(item for item in body["dimensions"] if item["key"] == ReadinessDimension.DSA.value)
    assert dsa["assessed_count"] == 6
    assert dsa["score"] is not None
    assert dsa["score"] > 0.05
    assert body["score"] is None
    assert body["state"] != PlacementState.READY.value
    core = next(item for item in body["dimensions"] if item["key"] == "core_cs")
    assert core["status"] == "not_assessed"
    assert core["score"] is None


def test_gaps_requires_authentication(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/me/gaps")
    assert response.status_code == 401


def test_gaps_empty_without_target(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "gaps-empty@example.com")
    body = seeded_client.get("/api/me/gaps").json()
    assert body["items"] == []


def test_readiness_explanation_and_ranked_gaps(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "explain-ready@example.com")
    user_id = seeded_client.get("/api/auth/me").json()["id"]
    from uuid import UUID

    _assess_skills(
        db_session,
        UUID(user_id),
        ["arrays", "hashing", "two-pointers", "binary-search", "linked-lists", "trees"],
        "0.8100",
    )
    _assess_skills(
        db_session,
        UUID(user_id),
        ["sql-basics", "sql-joins", "normalization", "indexing"],
        "0.5200",
    )
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    readiness = seeded_client.get("/api/me/readiness").json()
    assert readiness["score"] is None
    assert readiness["explanation"]
    assert any("below the target bar" in line for line in readiness["explanation"])
    assert any("not assessed yet" in line for line in readiness["explanation"])
    dsa = next(item for item in readiness["dimensions"] if item["key"] == "dsa")
    core = next(item for item in readiness["dimensions"] if item["key"] == "core_cs")
    assert dsa["score"] is not None
    assert core["score"] is not None
    assert dsa["target_min_score"] is not None
    assert core["target_min_score"] is not None
    projects = next(item for item in readiness["dimensions"] if item["key"] == "projects")
    interview = next(item for item in readiness["dimensions"] if item["key"] == "interview")
    assert projects["status"] == DimensionStatus.NOT_ASSESSED.value
    assert projects["score"] is None
    assert interview["score"] is None

    gaps = seeded_client.get("/api/me/gaps").json()["items"]
    assert gaps
    assert gaps == sorted(gaps, key=lambda item: item["rank"])
    top = gaps[0]
    assert top["dimension"] == ReadinessDimension.CORE_CS.value
    assert top["is_critical"] is True
    assert top["rank"] == 1


def test_no_false_readiness_score(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "no-false-score@example.com")
    user_id = seeded_client.get("/api/auth/me").json()["id"]
    from uuid import UUID

    _assess_skills(
        db_session,
        UUID(user_id),
        ["arrays", "hashing", "two-pointers", "binary-search", "linked-lists", "trees"],
    )
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    body = seeded_client.get("/api/me/readiness").json()
    assert body["score"] is None
    assert "percent" not in body
