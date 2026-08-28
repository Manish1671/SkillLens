"""Seed catalog data into the database."""

from app.core.database import SessionLocal
from app.seed.runner import run_seed


def main() -> None:
    session = SessionLocal()
    try:
        counts = run_seed(session)
        print("Seed completed:", counts)
    finally:
        session.close()


if __name__ == "__main__":
    main()
