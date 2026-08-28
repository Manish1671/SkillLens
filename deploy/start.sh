#!/bin/sh
set -eu

echo "SkillLens start: checking environment"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "FATAL: DATABASE_URL is missing. Add it in Render → Environment."
  exit 1
fi

key="${JWT_SECRET_KEY:-}"
if [ "${#key}" -lt 32 ]; then
  echo "FATAL: JWT_SECRET_KEY must be at least 32 characters. Add it in Render → Environment."
  exit 1
fi

cd /app/backend
echo "Running migrations"
python -m alembic upgrade head
echo "Seeding catalog"
python -m app.seed
if [ -n "${SKILLENS_DEMO_PASSWORD:-}" ]; then
  echo "Seeding demo account"
  python -m app.seed.demo
else
  echo "SKILLENS_DEMO_PASSWORD not set; skipping demo user"
fi

echo "Starting API on 127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &

if [ -f /app/web/server.js ]; then
  cd /app/web
elif [ -f /app/web/frontend/server.js ]; then
  cd /app/web/frontend
else
  echo "FATAL: Next.js server.js not found"
  ls -la /app/web || true
  exit 1
fi

export HOSTNAME=0.0.0.0
export PORT="${PORT:-7860}"
echo "Starting web on port ${PORT}"
exec node server.js
