#!/usr/bin/env bash
# Smoke test for docker compose stack (change 001 quickstart Phase 2).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "==> Building and starting postgres, migrate, backend..."
docker compose up --build -d postgres migrate backend

cleanup() {
  docker compose down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Waiting for backend health..."
for _ in $(seq 1 60); do
  if curl -sf http://localhost:8000/api/health | grep -q '"status":"ok"'; then
    echo "OK: GET /api/health"
    break
  fi
  sleep 2
done

curl -sf http://localhost:8000/api/health | grep -q '"status":"ok"' \
  || { echo "FAIL: backend health check"; exit 1; }

csp="$(curl -sI http://localhost:8000/api/health | grep -i content-security-policy || true)"
echo "$csp" | grep -qi "frame-ancestors" \
  || { echo "FAIL: missing CSP frame-ancestors header"; exit 1; }
echo "OK: CSP frame-ancestors header present"

echo "==> Compose smoke passed"
