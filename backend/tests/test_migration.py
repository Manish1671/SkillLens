import os
import subprocess
import sys

from sqlalchemy import inspect
from tests.conftest import BACKEND_ROOT, get_test_database_url, run_alembic_upgrade


def test_migration_upgrade_head_from_empty_database(fresh_database) -> None:
    inspector = inspect(fresh_database)
    tables = set(inspector.get_table_names())
    expected_tables = {
        "users",
        "topics",
        "skills",
        "skill_dependencies",
        "problems",
        "problem_skills",
        "hints",
        "attempts",
        "attempt_events",
        "evidence_items",
        "skill_masteries",
        "skill_assessment_snapshots",
        "recommendations",
        "alembic_version",
        "target_profiles",
        "target_requirements",
        "learner_targets",
        "dimension_skills",
    }
    assert expected_tables.issubset(tables)


def test_alembic_downgrade_and_upgrade_cycle(fresh_database) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = get_test_database_url()
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_ROOT,
        check=True,
        env=env,
    )
    run_alembic_upgrade(get_test_database_url())
    inspector = inspect(fresh_database)
    assert "users" in inspector.get_table_names()
