from decimal import Decimal
from uuid import UUID, uuid4

from app.core.enums import ActivityKind, Difficulty, MasteryStatus
from app.models.assessment import EvidenceItem, SkillAssessmentSnapshot, SkillMastery
from app.models.problem import Problem
from app.models.readiness import DimensionSkill
from app.models.skill import Skill
from app.repositories.problem_repository import ProblemRepository
from app.repositories.topic_repository import TopicRepository
from app.seed.core_cs_data import CORE_CS_PROBLEMS, CORE_CS_SKILL_SLUGS
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_attempt_api import (
    get_pair_sum_problem,
    register_and_login,
    start_payload,
    submit_payload,
)


def _quiz_spec(slug: str) -> dict:
    problem = next(item for item in CORE_CS_PROBLEMS if item["slug"] == slug)
    return problem["quiz_spec"]


def _correct_option(slug: str) -> str:
    return _quiz_spec(slug)["correct_option_id"]


def _wrong_option(slug: str) -> str:
    correct = _correct_option(slug)
    options = _quiz_spec(slug)["options"]
    return next(item["id"] for item in options if item["id"] != correct)


def _start_quiz(client: TestClient, db_session: Session, slug: str, client_id: str) -> str:
    problem = ProblemRepository().find_published_by_slug(db_session, slug)
    assert problem is not None
    start = client.post("/api/attempts", json=start_payload(str(problem.id), client_id))
    assert start.status_code == 201
    return start.json()["id"]


def _submit_quiz(
    client: TestClient,
    db_session: Session,
    slug: str,
    client_id: str,
    *,
    correct: bool,
) -> None:
    attempt_id = _start_quiz(client, db_session, slug, client_id)
    option = _correct_option(slug) if correct else _wrong_option(slug)
    response = client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"selected_option": option, "time_spent_seconds": 20},
    )
    assert response.status_code == 200


def test_coding_problem_defaults_to_coding(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems/pair-sum-lookup")
    assert response.status_code == 200
    assert response.json()["activity_kind"] == ActivityKind.CODING.value
    assert response.json()["options"] is None


def test_quiz_problem_uses_quiz_activity(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems/sql-inner-join-drop")
    assert response.status_code == 200
    body = response.json()
    assert body["activity_kind"] == ActivityKind.QUIZ.value
    assert [option["id"] for option in body["options"]] == ["a", "b", "c", "d"]
    assert all("label" in option for option in body["options"])


def test_answer_key_not_exposed_in_catalog(seeded_client: TestClient) -> None:
    listing = seeded_client.get("/api/problems", params={"activity_kind": "quiz", "limit": 50})
    detail = seeded_client.get("/api/problems/sql-inner-join-drop")
    for payload in (listing.json(), detail.json()):
        raw = str(payload)
        assert "correct_option" not in raw
        assert "correct_option_id" not in raw
        assert "quiz_spec" not in raw
        assert "answer_key" not in raw


def test_quiz_list_filter_and_topic_filter(seeded_client: TestClient) -> None:
    quizzes = seeded_client.get("/api/problems", params={"activity_kind": "quiz", "limit": 50})
    assert quizzes.status_code == 200
    items = quizzes.json()["items"]
    assert len(items) == len(CORE_CS_PROBLEMS)
    assert all(item["activity_kind"] == "quiz" for item in items)

    by_topic = seeded_client.get(
        "/api/problems",
        params={"topic": "core-cs-dbms", "activity_kind": "quiz", "limit": 50},
    )
    assert {item["slug"] for item in by_topic.json()["items"]} == {item["slug"] for item in items}

    coding = seeded_client.get("/api/problems")
    assert all(item["activity_kind"] == "coding" for item in coding.json()["items"])
    assert len(coding.json()["items"]) == 20


def test_quiz_correct_evaluated_server_side(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "quiz-correct@example.com")
    slug = "sql-inner-join-drop"
    attempt_id = _start_quiz(seeded_client, db_session, slug, "quiz-correct-1")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={
            "selected_option": _correct_option(slug),
            "is_correct": False,
            "time_spent_seconds": 40,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["assessment"] is not None
    assert len(body["assessment"]["evidence_items"]) > 0
    assert any(item["skill_slug"] == "sql-joins" for item in body["assessment"]["evidence_items"])


def test_quiz_incorrect_evaluated_server_side(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "quiz-wrong@example.com")
    slug = "sql-inner-join-drop"
    attempt_id = _start_quiz(seeded_client, db_session, slug, "quiz-wrong-1")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"selected_option": _wrong_option(slug), "time_spent_seconds": 40},
    )
    assert response.status_code == 200
    assert response.json()["is_correct"] is False


def test_invalid_quiz_option_rejected(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "quiz-invalid@example.com")
    attempt_id = _start_quiz(seeded_client, db_session, "sql-select-projection", "quiz-invalid-1")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"selected_option": "z", "time_spent_seconds": 10},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_quiz_option"


def test_quiz_submit_updates_mastery_and_snapshot(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "quiz-mastery@example.com")
    slug = "sql-select-projection"
    attempt_id = _start_quiz(seeded_client, db_session, slug, "quiz-mastery-1")
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"selected_option": _correct_option(slug), "time_spent_seconds": 25},
    )
    mastery = seeded_client.get("/api/me/mastery")
    assert any(item["skill_slug"] == "sql-basics" for item in mastery.json()["items"])
    snapshots = list(db_session.scalars(select(SkillAssessmentSnapshot)).all())
    assert len(snapshots) >= 1
    evidence = list(db_session.scalars(select(EvidenceItem)).all())
    assert len(evidence) >= 1


def test_quiz_hint_reveal_then_submit(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "quiz-hint@example.com")
    slug = "sql-inner-join-drop"
    problem = ProblemRepository().find_published_by_slug(db_session, slug)
    assert problem is not None
    hint_id = str(problem.hints[0].id)
    attempt_id = _start_quiz(seeded_client, db_session, slug, "quiz-hint-1")
    reveal = seeded_client.post(
        f"/api/attempts/{attempt_id}/events",
        json={"event_type": "hint_revealed", "payload": {"hint_id": hint_id}},
    )
    assert reveal.status_code == 200
    assert "INNER JOIN" in (reveal.json().get("hint_body_md") or "")
    submit = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"selected_option": _correct_option(slug), "time_spent_seconds": 50},
    )
    assert submit.status_code == 200
    types = {item["evidence_type"] for item in submit.json()["assessment"]["evidence_items"]}
    assert (
        "solved_with_hints" in types or "hint_reliance" in types or "solved_without_hints" in types
    )


def test_repeated_quiz_submit_is_safe(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "quiz-repeat@example.com")
    slug = "sql-count-nulls"
    attempt_id = _start_quiz(seeded_client, db_session, slug, "quiz-repeat-1")
    payload = {"selected_option": _correct_option(slug), "time_spent_seconds": 20}
    first = seeded_client.post(f"/api/attempts/{attempt_id}/submit", json=payload)
    second = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"selected_option": _wrong_option(slug), "time_spent_seconds": 99},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["is_correct"] is True
    assert second.json()["assessment"] is None
    evidence_count = db_session.scalar(
        select(func.count())
        .select_from(EvidenceItem)
        .where(EvidenceItem.attempt_id == UUID(attempt_id))
    )
    assert int(evidence_count or 0) == len(first.json()["assessment"]["evidence_items"])


def test_quiz_attempt_idor(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "quiz-owner@example.com")
    attempt_id = _start_quiz(seeded_client, db_session, "txn-acid", "quiz-idor-1")
    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "quiz-other@example.com")
    detail = seeded_client.get(f"/api/attempts/{attempt_id}")
    assert detail.status_code == 404


def test_unpublished_quiz_does_not_leak(seeded_client: TestClient, db_session: Session) -> None:
    topic = next(
        item for item in TopicRepository().list_all(db_session) if item.slug == "core-cs-dbms"
    )
    unpublished = Problem(
        slug="unpublished-secret-quiz",
        title="Secret Quiz",
        prompt_md="Hidden",
        difficulty=Difficulty.EASY,
        estimated_minutes=3,
        topic_id=topic.id,
        is_published=False,
        activity_kind=ActivityKind.QUIZ,
        quiz_spec={
            "options": [{"id": "a", "label": "nope"}],
            "correct_option_id": "a",
        },
    )
    db_session.add(unpublished)
    db_session.flush()
    listing = seeded_client.get("/api/problems", params={"activity_kind": "all", "limit": 100})
    slugs = {item["slug"] for item in listing.json()["items"]}
    assert "unpublished-secret-quiz" not in slugs
    assert seeded_client.get("/api/problems/unpublished-secret-quiz").status_code == 404


def test_coding_submit_still_uses_client_is_correct(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "coding-unchanged@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "coding-1"))
    response = seeded_client.post(
        f"/api/attempts/{start.json()['id']}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=90),
    )
    assert response.status_code == 200
    assert response.json()["is_correct"] is True


def test_core_cs_skills_mapped_only_to_core_cs(
    seeded_client: TestClient, db_session: Session
) -> None:
    rows = list(db_session.scalars(select(DimensionSkill)).all())
    skills = {skill.id: skill.slug for skill in db_session.scalars(select(Skill)).all()}
    core = {skills[row.skill_id] for row in rows if row.dimension == "core_cs"}
    dsa = {skills[row.skill_id] for row in rows if row.dimension == "dsa"}
    assert core == set(CORE_CS_SKILL_SLUGS)
    assert core.isdisjoint(dsa)
    assert "hashing" in dsa


def test_insufficient_core_cs_remains_unscored(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "core-early@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    for index, slug in enumerate(
        ["sql-select-projection", "sql-null-comparison", "sql-count-nulls"]
    ):
        _submit_quiz(seeded_client, db_session, slug, f"core-early-{index}", correct=True)
    body = seeded_client.get("/api/me/readiness").json()
    core = next(item for item in body["dimensions"] if item["key"] == "core_cs")
    assert core["assessed_count"] == 1
    assert core["score"] is None
    assert core["status"] == "early"


def test_core_cs_readiness_after_coverage(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "core-covered@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    slugs = [
        "sql-select-projection",
        "sql-null-comparison",
        "sql-count-nulls",
        "sql-inner-join-drop",
        "sql-left-join-null",
        "sql-join-fanout",
        "nf-repeating-groups",
        "nf-partial-dependency",
        "nf-transitive",
    ]
    for index, slug in enumerate(slugs):
        _submit_quiz(seeded_client, db_session, slug, f"cover-{index}", correct=True)
    body = seeded_client.get("/api/me/readiness").json()
    core = next(item for item in body["dimensions"] if item["key"] == "core_cs")
    assert core["assessed_count"] >= 3
    assert core["score"] is not None
    assert core["status"] != "not_assessed"


def test_dsa_plus_core_cs_e2e_and_core_cs_blocker(
    seeded_client: TestClient, db_session: Session
) -> None:
    register_and_login(seeded_client, "placement-mix@example.com")
    seeded_client.put("/api/me/target", json={"profile_slug": "product-sde"})
    user_id = UUID(seeded_client.get("/api/auth/me").json()["id"])
    dsa_slugs = [
        "arrays",
        "hashing",
        "two-pointers",
        "binary-search",
        "linked-lists",
        "sliding-window",
    ]
    skills = list(db_session.scalars(select(Skill).where(Skill.slug.in_(dsa_slugs))).all())
    for skill in skills:
        db_session.add(
            SkillMastery(
                user_id=user_id,
                skill_id=skill.id,
                score=Decimal("0.8200"),
                confidence=Decimal("0.7000"),
                evidence_count=4,
                status=MasteryStatus.ASSESSED,
            )
        )
    db_session.flush()

    before = seeded_client.get("/api/me/readiness").json()
    core_before = next(item for item in before["dimensions"] if item["key"] == "core_cs")
    dsa_before = next(item for item in before["dimensions"] if item["key"] == "dsa")
    assert dsa_before["score"] is not None
    assert core_before["status"] == "not_assessed"
    assert before["state"] != "ready"

    weak_quizzes = [
        "sql-select-projection",
        "sql-null-comparison",
        "sql-inner-join-drop",
        "sql-left-join-null",
        "nf-repeating-groups",
        "nf-partial-dependency",
        "idx-equality-btree",
        "idx-write-cost",
    ]
    for index, slug in enumerate(weak_quizzes):
        _submit_quiz(seeded_client, db_session, slug, f"weak-{index}", correct=False)

    after = seeded_client.get("/api/me/readiness").json()
    core_after = next(item for item in after["dimensions"] if item["key"] == "core_cs")
    dsa_after = next(item for item in after["dimensions"] if item["key"] == "dsa")
    assert dsa_after["score"] is not None
    assert core_after["status"] != "not_assessed"
    assert core_after["score"] is not None
    assert core_after["score"] < 0.60
    blockers = after["blockers"]
    assert any(
        item["dimension"] == "core_cs" and item["severity"] == "critical_blocker"
        for item in blockers
    )
    why = " ".join(item["why"] for item in blockers if item["dimension"] == "core_cs")
    assert "Core CS" in why
    assert "target" in why.lower() or "bar" in why.lower()


def test_attempt_detail_omits_answer_key(seeded_client: TestClient, db_session: Session) -> None:
    register_and_login(seeded_client, "quiz-detail@example.com")
    attempt_id = _start_quiz(seeded_client, db_session, "txn-dirty-read", str(uuid4())[:32])
    detail = seeded_client.get(f"/api/attempts/{attempt_id}")
    raw = str(detail.json())
    assert "correct_option_id" not in raw
    assert "quiz_spec" not in raw
    assert detail.json()["problem"]["activity_kind"] == "quiz"
    assert len(detail.json()["problem"]["options"]) == 4
