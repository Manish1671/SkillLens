from decimal import Decimal
from uuid import uuid4

from app.core.enums import AttemptStatus, Difficulty
from app.models.attempt import Attempt
from app.models.problem import Problem
from app.repositories.problem_repository import ProblemRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.user_repository import UserRepository
from fastapi.testclient import TestClient

PUBLISHED_SLUGS_SORTED = [
    "classic-binary-search",
    "climbing-stairs",
    "coin-change-min",
    "contains-duplicate",
    "count-islands",
    "house-robber",
    "longest-unique-substring",
    "max-profit-single-trade",
    "max-subarray-sum",
    "max-tree-depth",
    "merge-intervals",
    "min-subarray-sum-target",
    "pair-sum-lookup",
    "product-except-self",
    "queue-with-stacks",
    "reverse-linked-list",
    "search-rotated-array",
    "sorted-pair-sum",
    "three-sum-zero",
    "valid-parentheses",
]


def register_and_login(client: TestClient, email: str, password: str = "password123") -> None:
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "display_name": "Catalog User"},
    )
    client.post("/api/auth/login", json={"email": email, "password": password})


def test_topics_endpoint(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/topics")
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) == 7
    assert topics[0]["slug"] == "arrays-and-hashing"
    assert topics[0]["name"] == "Arrays & Hashing"
    assert any(topic["slug"] == "core-cs-dbms" for topic in topics)


def test_skills_endpoint(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/skills")
    assert response.status_code == 200
    skills = response.json()
    assert len(skills) == 19
    hashing = next(skill for skill in skills if skill["slug"] == "hashing")
    assert hashing["topic_slug"] == "arrays-and-hashing"
    assert len(hashing["prerequisite_skill_ids"]) == 1


def test_skill_detail_endpoint(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/skills/hashing")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "hashing"
    assert len(body["prerequisites"]) == 1
    assert body["prerequisites"][0]["slug"] == "arrays"
    assert any(problem["slug"] == "pair-sum-lookup" for problem in body["linked_problems"])


def test_problem_listing(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 20
    assert body["has_more"] is False
    assert body["next_cursor"] is None
    slugs = [item["slug"] for item in body["items"]]
    assert slugs == PUBLISHED_SLUGS_SORTED


def test_difficulty_filter(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems", params={"difficulty": "easy"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    assert all(item["difficulty"] == "easy" for item in items)


def test_topic_filter(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems", params={"topic": "arrays-and-hashing"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    assert all(item["topic"]["slug"] == "arrays-and-hashing" for item in items)


def test_skill_filter(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems", params={"skill": "hashing"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) > 0
    assert all(any(skill["slug"] == "hashing" for skill in item["skills"]) for item in items)


def test_search(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems", params={"q": "pair-sum-lookup"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["slug"] == "pair-sum-lookup"


def test_cursor_pagination(seeded_client: TestClient) -> None:
    first_page = seeded_client.get("/api/problems", params={"limit": 5})
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["items"]) == 5
    assert first_body["has_more"] is True
    assert first_body["next_cursor"] == first_body["items"][-1]["slug"]

    second_page = seeded_client.get(
        "/api/problems",
        params={"limit": 5, "cursor": first_body["next_cursor"]},
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["items"]) == 5
    first_slugs = {item["slug"] for item in first_body["items"]}
    second_slugs = {item["slug"] for item in second_body["items"]}
    assert first_slugs.isdisjoint(second_slugs)


def test_deterministic_pagination_ordering(seeded_client: TestClient) -> None:
    collected: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        params: dict[str, str | int] = {"limit": 3}
        if cursor:
            params["cursor"] = cursor
        response = seeded_client.get("/api/problems", params=params)
        body = response.json()
        collected.extend(item["slug"] for item in body["items"])
        if not body["has_more"]:
            break
        cursor = body["next_cursor"]
    assert collected == PUBLISHED_SLUGS_SORTED


def test_problem_detail(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems/pair-sum-lookup")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "pair-sum-lookup"
    assert "target" in body["prompt_md"].lower()
    assert body["hint_count"] == 2
    assert body["topic"]["slug"] == "arrays-and-hashing"
    skill_slugs = {skill["slug"] for skill in body["skills"]}
    assert "hashing" in skill_slugs
    assert "arrays" in skill_slugs


def test_unpublished_problem_not_exposed(seeded_client: TestClient, db_session) -> None:
    topic = TopicRepository().list_all(db_session)[0]
    unpublished = Problem(
        slug="unpublished-secret-problem",
        title="Secret Problem",
        prompt_md="Hidden prompt",
        difficulty=Difficulty.EASY,
        estimated_minutes=10,
        topic_id=topic.id,
        is_published=False,
        solution_outline_md="SECRET SOLUTION OUTLINE",
    )
    db_session.add(unpublished)
    db_session.flush()

    list_response = seeded_client.get("/api/problems")
    list_slugs = {item["slug"] for item in list_response.json()["items"]}
    assert "unpublished-secret-problem" not in list_slugs

    detail_response = seeded_client.get("/api/problems/unpublished-secret-problem")
    assert detail_response.status_code == 404
    assert detail_response.json()["code"] == "problem_not_found"


def test_solution_outline_not_exposed(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems/pair-sum-lookup")
    body = response.json()
    assert "solution_outline_md" not in body
    assert "solution" not in body


def test_hint_bodies_not_exposed(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems/pair-sum-lookup")
    body = response.json()
    assert "hints" not in body
    assert "body_md" not in body
    assert body["hint_count"] == 2


def test_linked_skills_returned_correctly(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems/pair-sum-lookup")
    skills = response.json()["skills"]
    hashing = next(skill for skill in skills if skill["slug"] == "hashing")
    arrays = next(skill for skill in skills if skill["slug"] == "arrays")
    assert hashing["is_primary"] is True
    assert Decimal(str(hashing["weight"])) == Decimal("1.0")
    assert arrays["is_primary"] is False


def test_nonexistent_slug_returns_404(seeded_client: TestClient) -> None:
    problem_response = seeded_client.get("/api/problems/does-not-exist")
    assert problem_response.status_code == 404
    assert problem_response.json()["code"] == "problem_not_found"

    skill_response = seeded_client.get("/api/skills/does-not-exist")
    assert skill_response.status_code == 404
    assert skill_response.json()["code"] == "skill_not_found"


def test_foreign_learner_data_never_exposed(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "solver@example.com")
    problem = ProblemRepository().find_published_by_slug(db_session, "pair-sum-lookup")
    user = UserRepository().find_by_email(db_session, "solver@example.com")
    assert problem is not None
    assert user is not None

    db_session.add(
        Attempt(
            user_id=user.id,
            problem_id=problem.id,
            status=AttemptStatus.SUBMITTED,
            is_correct=True,
            client_attempt_id=str(uuid4()),
        )
    )
    db_session.flush()

    authed_response = seeded_client.get("/api/problems/pair-sum-lookup")
    assert authed_response.json()["learner_state"]["solved"] is True

    seeded_client.post("/api/auth/logout")
    register_and_login(seeded_client, "other@example.com")

    other_response = seeded_client.get("/api/problems/pair-sum-lookup")
    learner_state = other_response.json()["learner_state"]
    assert learner_state is None or learner_state["solved"] is False


def test_learner_state_when_authenticated(seeded_client: TestClient, db_session) -> None:
    register_and_login(seeded_client, "learner@example.com")
    problem = ProblemRepository().find_published_by_slug(db_session, "contains-duplicate")
    user = UserRepository().find_by_email(db_session, "learner@example.com")
    assert problem is not None
    assert user is not None

    db_session.add(
        Attempt(
            user_id=user.id,
            problem_id=problem.id,
            status=AttemptStatus.IN_PROGRESS,
            client_attempt_id=str(uuid4()),
        )
    )
    db_session.flush()

    response = seeded_client.get("/api/problems/contains-duplicate")
    state = response.json()["learner_state"]
    assert state["attempted"] is True
    assert state["in_progress"] is True
    assert state["solved"] is False


def test_unauthenticated_problem_list_has_no_learner_state(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/problems", params={"limit": 3})
    for item in response.json()["items"]:
        assert item["learner_state"] is None
