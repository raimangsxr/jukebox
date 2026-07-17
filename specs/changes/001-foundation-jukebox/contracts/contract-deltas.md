# Contract Deltas: 001-foundation-jukebox

**Date**: 2026-07-17  
**Status**: **consolidated** into `specs/contracts/backend-api/contract.md`, `app-core/contract.md`, `ops-platform/contract.md`

## backend-api

### Added (foundation)

- `GET /api/health` → `200 {"status":"ok"}`, public, no auth
- CSP `frame-ancestors` on all responses
- `JUKEBOX_*` settings namespace
- Bootstrap: operator user + `event_config` singleton
- Alembic `0001_initial`: `users`, `event_config`
- Tests: `test_health.py`, `test_bootstrap.py`

## app-core

### Added (foundation)

- Routes: `/`, `/participar`, `/login`, `/admin` (placeholders)
- Display placeholder: 2/3 + 1/3 + full-width panel grid
- `apiBaseUrl` environment pattern

## ops-platform

### Added (foundation)

- `docker-compose.yml` (postgres, migrate, backend, frontend dev)
- `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore` files
- `frontend/nginx.conf` SPA fallback + `/health`
- `.github/workflows/release-images.yml`
- `scripts/compose-smoke.sh`

### Deferred

- `deploy/k8s/` manifests
