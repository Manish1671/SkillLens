"""Idempotent startup seed for production (Render cold starts).

`python -m app.seed` wipes the catalog. That is fine locally, but after the first
deploy it fails: learner attempts keep RESTRICT foreign keys on problems, so the
process never binds PORT and Render stays on "Application loading".
"""

from __future__ import annotations

import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.attempt import Attempt
from app.models.problem import Problem
from app.models.user import User
from app.seed.demo_runner import seed_demo_account
from app.seed.demo_script import DEMO_EMAIL, DEMO_PASSWORD_ENV
from app.seed.runner import run_seed


def catalog_is_empty(session: Session) -> bool:
    return (session.scalar(select(func.count()).select_from(Problem)) or 0) == 0


def demo_needs_seed(session: Session) -> bool:
    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        return True
    attempts = (
        session.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user.id))
        or 0
    )
    return attempts == 0


def bootstrap_data(session: Session) -> dict[str, str]:
    actions: dict[str, str] = {}
    if catalog_is_empty(session):
        run_seed(session)
        actions["catalog"] = "seeded"
    else:
        actions["catalog"] = "skipped"

    password = os.environ.get(DEMO_PASSWORD_ENV, "").strip()
    if not password:
        actions["demo"] = "skipped_no_password"
        return actions

    if demo_needs_seed(session):
        seed_demo_account(session, password=password)
        actions["demo"] = "seeded"
    else:
        actions["demo"] = "skipped"

    return actions


def main() -> None:
    session = SessionLocal()
    try:
        actions = bootstrap_data(session)
        print("Bootstrap completed:", actions)
    finally:
        session.close()


if __name__ == "__main__":
    main()
