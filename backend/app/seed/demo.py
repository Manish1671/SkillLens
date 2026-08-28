"""Seed a deterministic SkillLens demo learner through production services."""

import sys

from app.core.database import SessionLocal
from app.seed.demo_runner import (
    DemoSeedError,
    format_summary,
    seed_demo_account,
    verify_demo_invariants,
)


def main() -> None:
    session = SessionLocal()
    try:
        summary = seed_demo_account(session)
        verify_demo_invariants(session, summary)
        print(format_summary(summary))
    except DemoSeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        session.rollback()
        raise SystemExit(1) from exc
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
