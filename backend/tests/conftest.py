import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from app.core.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ADMIN_DATABASE_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql+psycopg://skilllens:skilllens@localhost:5432/skilllens",
)


def get_test_database_url() -> str:
    return os.getenv("TEST_DATABASE_URL", settings.test_database_url)


def ensure_test_database_exists() -> None:
    test_url = get_test_database_url()
    db_name = test_url.rsplit("/", 1)[-1]
    admin_engine = create_engine(
        ADMIN_DATABASE_URL,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 5},
    )
    with admin_engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not exists:
            connection.execute(text(f"CREATE DATABASE {db_name}"))


def run_alembic_upgrade(database_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        check=True,
        env=env,
    )


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    ensure_test_database_exists()
    test_url = get_test_database_url()
    run_alembic_upgrade(test_url)
    engine = create_engine(test_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator:
    from collections.abc import Generator as Gen

    from app.core.database import get_db
    from app.main import app
    from fastapi.testclient import TestClient

    def override_get_db() -> Gen[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(db_session: Session) -> Generator:
    from collections.abc import Generator as Gen

    from app.core.database import get_db
    from app.main import app
    from app.seed.runner import run_seed
    from fastapi.testclient import TestClient

    run_seed(db_session, commit=False)

    def override_get_db() -> Gen[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fresh_database(test_engine: Engine) -> Generator[Engine, None, None]:
    with test_engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.commit()

    test_url = get_test_database_url()
    run_alembic_upgrade(test_url)
    yield test_engine
    run_alembic_upgrade(test_url)
