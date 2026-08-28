import threading
from uuid import UUID, uuid4

from app.core.enums import AttemptEventType, Difficulty, MistakeType
from app.domain.attempt_sm import MAX_TIME_SPENT_SECONDS
from app.models.attempt import AttemptEvent
from app.models.problem import Problem
from app.repositories.attempt_repository import AttemptRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.user_repository import UserRepository
from app.schemas.attempt import StartAttemptRequest
from app.seed.runner import run_seed
from app.services.attempt_service import AttemptService
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker


def register_and_login(client: TestClient, email: str, password: str = "password123") -> None:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Attempt User"},
    )
    client.post("/api/auth/login", json={"email": email, "password": password})


def start_payload(problem_id: str, client_attempt_id: str = "client-attempt-1") -> dict:
    return {"problem_id": problem_id, "client_attempt_id": client_attempt_id}


def submit_payload(
    is_correct: bool = True,
    time_spent_seconds: int = 120,
    mistake_type: str | None = None,
    code_text: str | None = None,
) -> dict:
    payload: dict = {
        "is_correct": is_correct,
        "time_spent_seconds": time_spent_seconds,
    }
    if mistake_type is not None:
        payload["mistake_type"] = mistake_type
    if code_text is not None:
        payload["code_text"] = code_text
    return payload


def get_pair_sum_problem(db_session) -> Problem:
    problem = ProblemRepository().find_published_by_slug(db_session, "pair-sum-lookup")
    assert problem is not None
    return problem


def test_authenticated_start(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "start@example.com")
    problem = get_pair_sum_problem(db_session)
    response = seeded_client.post("/api/attempts", json=start_payload(str(problem.id)))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["problem_id"] == str(problem.id)


def test_unauthenticated_start_rejected(seeded_client: TestClient, db_session) -> None:
    problem = get_pair_sum_problem(db_session)
    response = seeded_client.post("/api/attempts", json=start_payload(str(problem.id)))
    assert response.status_code == 401


def test_problem_not_found(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "noprob@example.com")
    response = seeded_client.post(
        "/api/attempts",
        json=start_payload(str(uuid4()), "client-missing-problem"),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "problem_not_found"


def test_unpublished_problem_rejected(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "unpub@example.com")
    topic = TopicRepository().list_all(db_session)[0]
    unpublished = Problem(
        slug="unpublished-attempt-problem",
        title="Hidden",
        prompt_md="hidden",
        difficulty=Difficulty.EASY,
        estimated_minutes=10,
        topic_id=topic.id,
        is_published=False,
    )
    db_session.add(unpublished)
    db_session.flush()

    response = seeded_client.post(
        "/api/attempts",
        json=start_payload(str(unpublished.id), "client-unpub"),
    )
    assert response.status_code == 404


def test_successful_attempt_creation(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "create@example.com")
    problem = get_pair_sum_problem(db_session)
    response = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "create-1"))
    assert response.status_code == 201
    assert response.json()["client_attempt_id"] == "create-1"


def test_duplicate_in_progress_attempt_handled(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "dupprog@example.com")
    problem = get_pair_sum_problem(db_session)
    first = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "dup-a"))
    second = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "dup-b"))
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_idempotent_client_attempt_id(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "idempotent@example.com")
    problem = get_pair_sum_problem(db_session)
    first = seeded_client.post(
        "/api/attempts", json=start_payload(str(problem.id), "same-client-id")
    )
    second = seeded_client.post(
        "/api/attempts", json=start_payload(str(problem.id), "same-client-id")
    )
    assert first.json()["id"] == second.json()["id"]


def test_concurrent_duplicate_start(test_engine) -> None:
    with test_engine.connect() as connection:
        connection.execute(text("DELETE FROM attempt_events"))
        connection.execute(text("DELETE FROM attempts"))
        connection.commit()

    session = Session(bind=test_engine)
    problem = ProblemRepository().find_published_by_slug(session, "pair-sum-lookup")
    if problem is None:
        run_seed(session, commit=True)
        problem = ProblemRepository().find_published_by_slug(session, "pair-sum-lookup")
    assert problem is not None
    problem_id = problem.id
    user_repo = UserRepository()
    existing = user_repo.find_by_email(session, "concurrent@example.com")
    if existing is None:
        user_repo.create(
            session,
            email="concurrent@example.com",
            password_hash="hash",
            display_name="Concurrent",
        )
        session.commit()
    session.close()

    service = AttemptService(AttemptRepository(), ProblemRepository())
    results: list[str] = []

    def worker(client_id: str) -> None:
        worker_session = sessionmaker(bind=test_engine)()
        try:
            worker_user = user_repo.find_by_email(worker_session, "concurrent@example.com")
            assert worker_user is not None
            attempt = service.start_attempt(
                worker_session,
                worker_user,
                StartAttemptRequest(problem_id=problem_id, client_attempt_id=client_id),
            )
            results.append(attempt.id)
        finally:
            worker_session.close()

    threads = [
        threading.Thread(target=worker, args=("concurrent-a",)),
        threading.Thread(target=worker, args=("concurrent-b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 2
    assert results[0] == results[1]

    with test_engine.connect() as connection:
        connection.execute(text("DELETE FROM attempt_events"))
        connection.execute(text("DELETE FROM attempts"))
        connection.execute(text("DELETE FROM users WHERE email = 'concurrent@example.com'"))
        connection.commit()


def test_started_event_exists(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "started@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "started-1"))
    attempt_id = start.json()["id"]
    detail = seeded_client.get(f"/api/attempts/{attempt_id}")
    event_types = [event["event_type"] for event in detail.json()["events"]]
    assert "started" in event_types


def test_valid_hint_reveal(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "hint@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "hint-1"))
    attempt_id = start.json()["id"]
    hint_id = problem.hints[0].id

    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/events",
        json={
            "event_type": "hint_revealed",
            "payload": {"hint_id": str(hint_id)},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event_type"] == "hint_revealed"
    assert body["hint_body_md"] is not None
    assert len(body["hint_body_md"]) > 0


def test_hint_cannot_be_revealed_twice(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "hintdup@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "hintdup-1"))
    attempt_id = start.json()["id"]
    hint_id = problem.hints[0].id
    payload = {"event_type": "hint_revealed", "payload": {"hint_id": str(hint_id)}}
    seeded_client.post(f"/api/attempts/{attempt_id}/events", json=payload)
    second = seeded_client.post(f"/api/attempts/{attempt_id}/events", json=payload)
    assert second.status_code == 409
    assert second.json()["code"] == "hint_already_revealed"


def test_hint_cannot_be_revealed_on_another_users_attempt(
    seeded_client: TestClient, db_session
) -> None:
    problem = get_pair_sum_problem(db_session)
    register_and_login(seeded_client, "hintowner@example.com")
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "hintowner-1"))
    attempt_id = start.json()["id"]
    hint_id = problem.hints[0].id

    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "hintother@example.com")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/events",
        json={"event_type": "hint_revealed", "payload": {"hint_id": str(hint_id)}},
    )
    assert response.status_code == 404


def test_hint_from_another_problem_rejected(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "hintwrong@example.com")
    problem_a = get_pair_sum_problem(db_session)
    problem_b = ProblemRepository().find_published_by_slug(db_session, "contains-duplicate")
    assert problem_b is not None
    start = seeded_client.post(
        "/api/attempts", json=start_payload(str(problem_a.id), "hintwrong-1")
    )
    attempt_id = start.json()["id"]
    wrong_hint_id = problem_b.hints[0].id

    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/events",
        json={"event_type": "hint_revealed", "payload": {"hint_id": str(wrong_hint_id)}},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "hint_not_found"


def test_self_report_event(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "selfreport@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "self-1"))
    attempt_id = start.json()["id"]
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/events",
        json={
            "event_type": "self_report",
            "payload": {"believes_correct": False, "confidence": "low"},
        },
    )
    assert response.status_code == 200
    assert response.json()["event_type"] == "self_report"


def test_successful_submit(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "submit@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "submit-1"))
    attempt_id = start.json()["id"]
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=300),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["is_correct"] is True
    assert body["time_spent_seconds"] == 300


def test_submitted_attempt_cannot_submit_again(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "resubmit@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "resubmit-1"))
    attempt_id = start.json()["id"]
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=100),
    )
    second = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=False, time_spent_seconds=200),
    )
    assert second.status_code == 200
    assert second.json()["is_correct"] is True
    assert second.json()["time_spent_seconds"] == 100


def test_submitted_attempt_cannot_abandon(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "subabandon@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "subab-1"))
    attempt_id = start.json()["id"]
    seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=60),
    )
    response = seeded_client.post(f"/api/attempts/{attempt_id}/abandon")
    assert response.status_code == 409
    assert response.json()["code"] == "attempt_already_submitted"


def test_abandoned_attempt_cannot_submit(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "absubmit@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "absub-1"))
    attempt_id = start.json()["id"]
    seeded_client.post(f"/api/attempts/{attempt_id}/abandon")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(is_correct=True, time_spent_seconds=60),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "attempt_abandoned"


def test_successful_abandon(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "abandon@example.com")
    problem = ProblemRepository().find_published_by_slug(db_session, "contains-duplicate")
    assert problem is not None
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "abandon-1"))
    attempt_id = start.json()["id"]
    response = seeded_client.post(f"/api/attempts/{attempt_id}/abandon")
    assert response.status_code == 200
    assert response.json()["status"] == "abandoned"


def test_invalid_transition_rejected(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "invalid@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "invalid-1"))
    attempt_id = start.json()["id"]
    seeded_client.post(f"/api/attempts/{attempt_id}/abandon")
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/events",
        json={"event_type": "self_report", "payload": {"note": "late"}},
    )
    assert response.status_code == 409


def test_negative_time_rejected(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "negtime@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "neg-1"))
    attempt_id = start.json()["id"]
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"is_correct": True, "time_spent_seconds": -1},
    )
    assert response.status_code == 422


def test_excessive_time_rejected(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "bigtime@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "big-1"))
    attempt_id = start.json()["id"]
    response = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={"is_correct": True, "time_spent_seconds": MAX_TIME_SPENT_SECONDS + 1},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_time_spent"


def test_mistake_enum_validated(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "mistake@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "mist-1"))
    attempt_id = start.json()["id"]
    bad = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json={
            "is_correct": False,
            "time_spent_seconds": 60,
            "mistake_type": "not_a_real_mistake",
        },
    )
    assert bad.status_code == 422

    good = seeded_client.post(
        f"/api/attempts/{attempt_id}/submit",
        json=submit_payload(
            is_correct=False,
            time_spent_seconds=60,
            mistake_type=MistakeType.LOGIC_ERROR.value,
        ),
    )
    assert good.status_code == 200
    assert good.json()["mistake_type"] == MistakeType.LOGIC_ERROR.value


def test_attempt_history_is_user_scoped(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "historya@example.com")
    problem = get_pair_sum_problem(db_session)
    seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "hist-a"))
    list_a = seeded_client.get("/api/attempts")
    assert list_a.status_code == 200
    assert len(list_a.json()["items"]) >= 1

    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "historyb@example.com")
    list_b = seeded_client.get("/api/attempts")
    assert list_b.status_code == 200
    assert len(list_b.json()["items"]) == 0


def test_attempt_detail_is_user_scoped(seeded_client: TestClient, db_session) -> None:
    problem = get_pair_sum_problem(db_session)
    register_and_login(seeded_client, "detailowner@example.com")
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "det-1"))
    attempt_id = start.json()["id"]

    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "detailother@example.com")
    response = seeded_client.get(f"/api/attempts/{attempt_id}")
    assert response.status_code == 404


def test_event_history_returned_correctly(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "events@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "events-1"))
    attempt_id = start.json()["id"]
    detail = seeded_client.get(f"/api/attempts/{attempt_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["problem"]["slug"] == "pair-sum-lookup"
    assert len(body["available_hints"]) == len(problem.hints)
    assert any(event["event_type"] == "started" for event in body["events"])


def test_duplicate_submit_does_not_create_duplicate_submitted_event(
    seeded_client: TestClient, db_session
) -> None:
    register_and_login(seeded_client, "dupsubmit@example.com")
    problem = get_pair_sum_problem(db_session)
    start = seeded_client.post("/api/attempts", json=start_payload(str(problem.id), "dupsub-1"))
    attempt_id = start.json()["id"]
    payload = submit_payload(is_correct=True, time_spent_seconds=90)
    seeded_client.post(f"/api/attempts/{attempt_id}/submit", json=payload)
    seeded_client.post(f"/api/attempts/{attempt_id}/submit", json=payload)

    count = db_session.scalar(
        select(func.count())
        .select_from(AttemptEvent)
        .where(
            AttemptEvent.attempt_id == UUID(attempt_id),
            AttemptEvent.event_type == AttemptEventType.SUBMITTED,
        )
    )
    assert int(count or 0) == 1


def test_attempt_not_found(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "notfound@example.com")
    response = seeded_client.get(f"/api/attempts/{uuid4()}")
    assert response.status_code == 404


def test_malformed_attempt_uuid(seeded_client: TestClient) -> None:
    register_and_login(seeded_client, "baduuid@example.com")
    response = seeded_client.get("/api/attempts/not-a-uuid")
    assert response.status_code == 422
