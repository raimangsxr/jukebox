# Implementation Plan: Participant Google OAuth and Song Submit

**Branch**: `003-participant-oauth-submit` (git) | **Change id**: `006-participant-oauth-submit` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/006-participant-oauth-submit/spec.md`

## Summary

Add Google OAuth on `/participar` (backend authorization code flow), enrich `participants` with Google profile fields, and let authenticated participants submit YouTube links to `pending_review` with baseline per-participant limits. Expose **Mis canciones** with Spanish status labels; keep 005 voting/SSE and 004 moderation unchanged. Dev participant bootstrap remains gated for tests.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, httpx (Google token + userinfo), itsdangerous (OAuth state + participant cookie); Angular standalone, RxJS, TailwindCSS

**Storage**: PostgreSQL — extend `participants` (migration `0005`); reuse `queue_entries.submitted_by_participant_id`

**Testing**: pytest (`test_oauth_google.py`, `test_participant_submit.py`, 005 vote regression); `npm run build`; manual quickstart with Google console or dev-auth fallback

**Target Platform**: Docker Compose / K8s (003); mobile `/participar` via QR from kiosk

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: OAuth round-trip &lt; 30s user-perceived (SC-001); submit + list update &lt; 3s (SC-002)

**Constraints**: Google OAuth only on `/participar`; separate cookies from operator; submit limits per 001; Spanish UI; dev-auth not primary production UX

**Scale/Scope**: ~4 new API routes; 1 migration; 2 services; extend participate UI (submit + Mis canciones + Google button)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted |
| V. Tests for changed behavior | Pass | OAuth mock tests, submit limits, vote regression |
| VI. Sibling conventions | Pass | `/api/*`, backend OAuth callback, separate participant cookie |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/changes/006-participant-oauth-submit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── contracts/contract-deltas.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                    # + JUKEBOX_GOOGLE_*, return URL
│   ├── models.py                    # Participant +google_sub, email, avatar_url
│   ├── schemas.py                   # SubmitRequest, SubmissionListResponse
│   ├── services/
│   │   ├── google_oauth_service.py  # login URL, callback, upsert participant
│   │   └── queue_service.py         # + submit_as_participant
│   └── routers/
│       ├── auth_google.py           # GET login, GET callback
│       ├── participant.py           # + GET /submissions
│       └── queue.py                 # + POST /submit (participant)
├── alembic/versions/
│   └── 0005_participant_google_profile.py
└── tests/
    ├── test_oauth_google.py
    └── test_participant_submit.py

frontend/src/app/
├── participate/
│   └── participate.component.*      # Google login, submit form, Mis canciones
└── services/
    └── participant.service.ts       # OAuth redirect, submit, submissions
```

**Structure Decision**: Extend 005 participant stack; new `auth_google` router separate from operator `auth` router.

## Phase 0 — Research

See [research.md](./research.md). Resolved: backend auth code flow, state signing, submit endpoint shape, limits, submissions API, migration 0005.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **Migration `0005`**: `participants.google_sub` (unique nullable), `email`, `avatar_url`
2. **`google_oauth_service.py`**: build authorize URL; verify state; exchange code; fetch userinfo; upsert by `google_sub`; set participant cookie
3. **`auth_google.py`**: public routes; redirect to `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL`
4. **`queue_service.submit_as_participant`**: limits + duplicate + metadata; `bump_revision`
5. **`POST /api/queue/submit`**: participant auth
6. **`GET /api/participant/submissions`**: own entries list
7. **Tests**: mock Google HTTP; submit limit matrix; OAuth upsert reuse

### Frontend design

1. Replace placeholder copy with **Iniciar sesión con Google** (full redirect)
2. Submit URL input + **Enviar canción**; Spanish errors for 429/409/422
3. **Mis canciones** with status badges; refresh on SSE revision
4. Hide dev-auth unless `environment.allowDevParticipantAuth` or `?dev=1`; disable vote/submit when unauthenticated
5. Parse `oauth_error` query param on return; map API submit `detail` codes to Spanish in component/service

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts + manifest

Register 006; merge contract deltas.

### Phase B — OAuth backend

Migration, google_oauth_service, auth_google router, tests.

### Phase C — Submit backend

submit_as_participant, routes, submission list, tests.

### Phase D — Frontend participate

Google button, submit form, Mis canciones, submission refresh.

### Phase E — Integration + regression

OAuth E2E (manual), vote regression, quickstart, manifest closure.

## Risks

| Risk | Mitigation |
|------|------------|
| Google redirect URI mismatch | Document in quickstart + compose env |
| Local dev without Google credentials | Keep dev-auth path for pytest/QA |
| oEmbed failure on private videos | 422 with Spanish message; no orphan rows |
| Concurrent submits hitting limits | DB transaction + count checks in service |

## Complexity Tracking

> No violations.
