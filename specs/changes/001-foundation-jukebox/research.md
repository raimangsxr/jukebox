# Research: 001-foundation-jukebox

**Date**: 2026-07-17

## Decision: Monorepo layout

**Decision**: Mirror `amrn-bull` / `amrn-escalabirras-dual`: `backend/`, `frontend/`, `specs/`, root `docker-compose.yml`, split images in production.

**Rationale**: Shared ops patterns across AMRN event apps; kiosk-screen already integrates bull/escalabirras iframes.

**Alternatives considered**: Single image (rejected — bull moved to split images in CHG-008); Nx monorepo (rejected — siblings use simple two-folder layout).

## Decision: Env prefix and API surface

**Decision**: Flat `JUKEBOX_` env prefix; all HTTP under `/api/*`.

**Rationale**: Consistency with `BULL_` and escalabirras conventions; ingress routes `/api` to backend.

## Decision: Auth model (product — documented, not implemented in 001)

**Decision**: Dual auth — operator password session + participant Google OAuth + embed tokens for display.

**Rationale**: User requirement; matches bull operator model while adding public OAuth only on `/participar`.

## Decision: Realtime transport

**Decision**: `GET /api/state` + SSE `GET /api/events/stream` (display); dedicated participant stream TBD in change 004+.

**Rationale**: Proven in amrn-bull CHG-010; kiosk-screen orchestration already SSE-native.

## Decision: Iframe protocol

**Decision**: Reuse `bull:resize`, `bull:ping`, `bull:config` without rename; `embed_app_family: amrn_jukebox` in kiosk-screen.

**Rationale**: CHG-042 already implements parent side; zero protocol churn.

## Decision: Test database

**Decision**: SQLite in-memory for pytest; PostgreSQL in compose.

**Rationale**: Same as bull `conftest.py`; fast CI without Docker.

## Open questions (deferred)

| Topic | Target change |
|-------|----------------|
| YouTube Data API key management | 00X-youtube-integration |
| Web Push VAPID secrets | 00X-notifications-push |
| `deploy/k8s/` manifests | 00X-production-k8s |
| kiosk-screen `amrn_jukebox` family | sibling repo CHG |
