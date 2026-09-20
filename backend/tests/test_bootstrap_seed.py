from uuid import UUID

from app.core.security import hash_password
from app.core.services import attempt_service
from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.user import User
from app.repositories.problem_repository import ProblemRepository
from app.repositories.user_repository import UserRepository
from app.schemas.attempt import StartAttemptRequest, SubmitAttemptRequest
from app.seed.bootstrap import bootstrap_data
from app.seed.demo_script import DEMO_EMAIL
from app.seed.runner import run_seed
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_bootstrap_skips_catalog_when_learner_data_exists(
    db_session: Session, monkeypatch
) -> None:
    monkeypatch.setenv("SKILLENS_DEMO_PASSWORD", "demo-pass-123")
    run_seed(db_session, commit=False)

    user = UserRepository().create(
        db_session,
        email=DEMO_EMAIL,
        password_hash=hash_password("demo-pass-123"),
        display_name="Alex",
    )
    problem = ProblemRepository().find_published_by_slug(db_session, "valid-parentheses")
    assert problem is not None
    started = attempt_service.start_attempt(
        db_session,
        user,
        StartAttemptRequest(problem_id=problem.id, client_attempt_id="bootstrap-keep-1"),
    )
    attempt_service.submit_attempt(
        db_session,
        user,
        UUID(started.id),
        SubmitAttemptRequest(is_correct=True, time_spent_seconds=40),
    )

    before_problems = db_session.scalar(select(func.count()).select_from(Problem))
    before_attempts = db_session.scalar(select(func.count()).select_from(Attempt))

    actions = bootstrap_data(db_session)

    assert actions["catalog"] == "skipped"
    assert actions["demo"] == "skipped"
    assert db_session.scalar(select(func.count()).select_from(Problem)) == before_problems
    assert db_session.scalar(select(func.count()).select_from(Attempt)) == before_attempts
    assert db_session.scalar(select(User).where(User.email == DEMO_EMAIL)) is not None


def test_bootstrap_skips_demo_without_password(monkeypatch) -> None:
    monkeypatch.delenv("SKILLENS_DEMO_PASSWORD", raising=False)
    monkeypatch.setattr("app.seed.bootstrap.catalog_is_empty", lambda _session: False)
    actions = bootstrap_data(object())  # type: ignore[arg-type]
    assert actions == {"catalog": "skipped", "demo": "skipped_no_password"}
