# Implementation Plan: Indicador de conexión, admin móvil y normas de participación

**Branch**: `016-participant-limits-ux` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

## Summary

Fix stuck live-connection badges on kiosk/admin/participate with a shared SSE+fallback manager; make admin moderation mobile-friendly via responsive cards; add participant rules screen after login with three ENV-configurable limits exposed via `ParticipantStateResponse`.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / Angular 22 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy, RxJS, TailwindCSS  
**Storage**: PostgreSQL (unchanged); sessionStorage for rules acceptance  
**Testing**: pytest (backend), vitest (frontend)  
**Target Platform**: Web SPA + kiosk display  
**Constraints**: Spanish UI; single-replica SSE; no new DB migrations  
**Scale/Scope**: 3 surfaces (display, admin, participate), 3 ENV vars, 1 new Angular component

## Constitution Check

*GATE: Pass — incremental UX + config; contracts updated before/with implementation; tests extended; no constitution violations.*

## Project Structure

### Documentation

```text
specs/changes/016-participant-limits-ux/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── tasks.md
├── analyze.md
├── contracts/contract-deltas.md
└── checklists/requirements.md
```

### Source Code

```text
backend/app/config.py
backend/app/schemas.py
backend/app/services/search_rate_limiter.py
backend/app/services/vote_service.py
backend/app/services/state_service.py
frontend/src/app/services/live-connection.ts
frontend/src/app/services/display-state.service.ts
frontend/src/app/services/participant-state.service.ts
frontend/src/app/components/live-status.component.ts
frontend/src/app/admin/admin.component.*
frontend/src/app/participate/participate.component.*
frontend/src/app/display/display.component.*
deploy/k8s/configmap.yaml
deploy/k8s/backend.yaml
```

## Phase 0 — Research

See [research.md](./research.md). All decisions resolved.

## Phase 1 — Design

See [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [quickstart.md](./quickstart.md).

## Phase 2 — Implementation tasks

See [tasks.md](./tasks.md).

## Risks

| Risk | Mitigation |
|------|------------|
| 10-min vote window changes live event feel | ENV override; defaults match prior caps (2 votes) |
| sessionStorage cleared mid-event | Re-show rules; acceptable per spec |
| SSE EventSource `onopen` not fired in some proxies | Fallback polling keeps data fresh |
