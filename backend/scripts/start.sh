#!/bin/sh
set -eu

python -m alembic upgrade head
python -m app.seed.bootstrap

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
