#!/bin/sh
set -eu

python -m alembic upgrade head
python -m app.seed
if [ -n "${SKILLENS_DEMO_PASSWORD:-}" ]; then
  python -m app.seed.demo
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
