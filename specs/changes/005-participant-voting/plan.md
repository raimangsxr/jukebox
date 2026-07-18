# Implementation Plan: Participant Voting

**Branch**: `002-participant-voting` (git) | **Change id**: `005-participant-voting` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/005-participant-voting/spec.md`

## Summary

Enable attendees to vote on `queued` songs from `/participar`: 2 votes per rolling 5-minute window, reorder by `vote_count DESC` / `created_at ASC`, live updates via existing SSE hub. Introduce `participants` and `votes` tables, participant session cookie (`jukebox_participant_session`), dev bootstrap gated by `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH`, and extend SSE/state read paths to accept participant auth alongside operator session. Google OAuth deferred to 006.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, itsdangerous (signed participant cookie); Angular standalone, RxJS, TailwindCSS, native `EventSource`

**Storage**: PostgreSQL — new `participants`, `votes`; reuse `queue_entries.vote_count`, `jukebox_runtime.revision`

**Testing**: pytest (`test_votes.py`, `test_participant_auth.py`, update `test_sse.py`, `test_auth_policy.py`); `npm run build`; manual quickstart

**Target Platform**: Docker Compose / K8s (003); kiosk display unchanged; mobile `/participar`

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Vote API &lt; 300 ms p95 local; SSE delivery within 5s of vote (SC-003); participant state snapshot &lt; 200 ms p95

**Constraints**: Participant endpoints require `jukebox_participant_session` (not operator); operator moderation APIs unchanged; Spanish UI; dev participant auth default false; vote only `queued` entries

**Scale/Scope**: Single event; ~5 new API routes; 1 service + 2 routers; wire `ParticipateComponent` + `ParticipantStateService`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` into `backend-api` + `app-core` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted; consolidation required before code |
| V. Tests for changed behavior | Pass | Vote limits, reorder, invalid targets, SSE revision, participant auth |
| VI. Sibling conventions | Pass | `/api/*` prefix; separate participant session cookie; SSE reuse from 004 |

**Post-design re-check**: All gates pass. No constitution violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/changes/005-participant-voting/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── context-pack.md      # Agent context
├── contracts/contract-deltas.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py               # + allow_dev_participant_auth
│   ├── main.py                 # mount participant + votes routers
│   ├── models.py               # + Participant, Vote
│   ├── schemas.py              # participant + vote DTOs
│   ├── security.py             # + get_current_participant, stream auth union
│   ├── services/
│   │   ├── vote_service.py     # cast vote, window count, reorder side effects
│   │   └── participant_session.py  # signed jukebox_participant_session cookie
│   └── routers/
│       ├── participant.py      # dev-auth, me, GET /participant/state
│       └── votes.py            # POST /votes
├── alembic/versions/
│   └── 0004_participants_and_votes.py
└── tests/
    ├── test_votes.py
    ├── test_participant_auth.py
    ├── test_sse.py             # participant SSE auth
    └── test_auth_policy.py     # public route list update

frontend/src/app/
├── participate/
│   └── participate.component.* # vote UI, votes remaining, sign-in prompt
└── services/
    ├── participant.service.ts      # dev-auth, me, cast vote
    └── participant-state.service.ts # GET /participant/state + SSE
```

**Structure Decision**: Monorepo `backend/` + `frontend/` per 001; extend 004 SSE/state paths rather than duplicate streams.

## Phase 0 — Research

See [research.md](./research.md). All technical choices resolved (participant cookie, rolling window, vote API, SSE dual-auth, dev bootstrap).

**Note**: Starlette `SessionMiddleware` is operator-only (`jukebox_session`). Participant identity uses a separate signed cookie via `participant_session.py` (itsdangerous + `settings.session_secret` / env `JUKEBOX_SESSION_SECRET`), not a second SessionMiddleware.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **Migration `0004`**: `participants`, `votes`; index `(participant_id, created_at)`
2. **`participant_session.py`**: set/clear/read signed `jukebox_participant_session` cookie
3. **`security.py`**: `get_current_participant`; `get_stream_subscriber` accepts operator **or** participant session
4. **`vote_service.py`**: validate window (2 / 5 min), target `queued`, insert vote, increment `vote_count`, `_recompute_positions`, `bump_revision`
5. **`routers/participant.py`**: `POST /api/participant/dev-auth` (gated), `GET /api/participant/me`, `GET /api/participant/state`
6. **`routers/votes.py`**: `POST /api/votes` body `{ queue_entry_id }`
7. **`routers/state.py`**: swap `CurrentUser` on stream to dual-auth dependency; `GET /api/state` remains operator-only (kiosk)
8. **Tests**: vote limits with frozen time; reorder; 409 invalid target; SSE revision bump; 401 without participant cookie

### Frontend design

1. **`ParticipantService`**: dev-auth (dev only), `me()`, `castVote(entryId)`, expose `participant$`
2. **`ParticipantStateService`**: bootstrap `GET /api/participant/state`, `EventSource` `/api/events/stream` with credentials, merge queue/revision from SSE while preserving `votes_remaining` from snapshot/vote responses
3. **`ParticipateComponent`**: unauthenticated → Spanish sign-in prompt (OAuth in 006); authenticated → scrollable `queued` list with vote buttons + count badge + "X de 2 votos disponibles" header (FR-008); Spanish errors for limit/invalid
4. **authInterceptor**: 401 on `/participar` does not redirect to `/login` (public route); show sign-in prompt instead

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts

Merge contract deltas; register 005 in `specs/manifest.yml` (status `in_progress` → `implemented` when done).

### Phase B — Backend core

Models, migration, participant session, vote service, routers, pytest.

### Phase C — Frontend participate

ParticipantService, ParticipantStateService, ParticipateComponent vote UI.

### Phase D — SSE integration

Vote in one tab → kiosk strip and `/participar` update without reload.

### Phase E — Validation

pytest, build, quickstart manual paths, 004 regression (operator moderation unchanged).

## Risks

| Risk | Mitigation |
|------|------------|
| Dual SSE auth complexity | Single `get_stream_subscriber` dependency; tests for both cookie types |
| Clock skew on vote window | Use DB `now()` consistently; pytest `freezegun` or monkeypatch |
| Participant cookie vs operator cookie confusion | Distinct cookie names; separate dependencies; auth policy tests |
| `/participar` 401 triggers login redirect | Exempt `/participar` in interceptor or scope 401 handling |

## Complexity Tracking

> No violations.
