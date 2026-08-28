# All-in-one image: Next.js (public) + FastAPI on localhost:8000.
# Postgres is provided by DATABASE_URL (Neon / any hosted Postgres).

FROM node:20-bookworm-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG API_URL=http://127.0.0.1:8000
ENV API_URL=$API_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=frontend-build /usr/local/bin/node /usr/local/bin/node

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend-build /frontend/public /app/web/public
COPY --from=frontend-build /frontend/.next/standalone /app/web/
COPY --from=frontend-build /frontend/.next/static /app/web/.next/static
COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh /app/backend/scripts/start.sh

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=7860 \
    APP_ENV=production

EXPOSE 7860
WORKDIR /app/backend
CMD ["/app/start.sh"]
