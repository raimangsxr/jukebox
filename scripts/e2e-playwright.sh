#!/usr/bin/env bash
# Full-stack Playwright e2e: docker backend + ng serve (e2e config) + kiosk audio flow.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

export JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true
export JUKEBOX_CORS_ALLOW_ORIGINS=http://localhost:4300,http://127.0.0.1:4300

FRONTEND_PORT=4300
FRONTEND_PID=""

cleanup() {
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Starting postgres, migrate, backend..."
docker compose up --build -d postgres migrate backend

echo "==> Waiting for backend..."
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/api/health | grep -q '"status":"ok"'; then
    break
  fi
  sleep 2
done
curl -sf http://127.0.0.1:8000/api/health | grep -q '"status":"ok"' \
  || { echo "FAIL: backend not healthy"; exit 1; }

echo "==> Starting frontend (e2e config) on :${FRONTEND_PORT}..."
(
  cd frontend
  npm run start -- --configuration e2e --host 127.0.0.1 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo "==> Waiting for frontend..."
for _ in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null; then
    break
  fi
  sleep 2
done
curl -sf "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null \
  || { echo "FAIL: frontend not ready"; exit 1; }

echo "==> Running Playwright e2e..."
(
  cd frontend
  E2E_BASE_URL="http://127.0.0.1:${FRONTEND_PORT}" \
  E2E_API_URL="http://127.0.0.1:8000/api" \
  E2E_OPERATOR_USERNAME="${JUKEBOX_OPERATOR_USERNAME}" \
  E2E_OPERATOR_PASSWORD="${JUKEBOX_OPERATOR_PASSWORD}" \
    npx playwright test e2e/kiosk-playback-audio.spec.ts e2e/autoplay-policy.spec.ts
)

echo "==> E2E passed"
