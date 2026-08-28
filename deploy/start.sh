#!/bin/sh
set -eu

cd /app/backend
python -m alembic upgrade head
python -m app.seed
if [ -n "${SKILLENS_DEMO_PASSWORD:-}" ]; then
  python -m app.seed.demo
fi

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

cd /app/web
export HOSTNAME=0.0.0.0
export PORT="${PORT:-7860}"
exec node server.js
