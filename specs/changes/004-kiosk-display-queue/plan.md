# Implementation Plan: Kiosk Display, Queue and Moderation

**Branch**: `004-kiosk-display-queue` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/004-kiosk-display-queue/spec.md`

## Summary

Replace kiosk display placeholders with a functional three-region layout (90% top: YouTube player 2/3 + QR 1/3; ~10% bottom: queue strip with vote counts). Add backend persistence (`queue_entries`, `jukebox_runtime`), moderation APIs, `GET /api/state` + SSE stream, and admin moderation UI. Preserve 002 embed-token and display-error behavior. Participant submit/vote deferred to 005–006.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, httpx (oEmbed fetch); Angular standalone, RxJS, TailwindCSS, YouTube IFrame API, QR library (`qrcode` or `angularx-qrcode`)

**Storage**: PostgreSQL — new `queue_entries`, `jukebox_runtime`; `event_config` read-only in 004

**Testing**: pytest (`test_queue.py`, `test_state.py`, `test_sse.py`, update `test_auth_policy.py`); `npm run build`; manual quickstart

**Target Platform**: Docker Compose / K8s (003); kiosk iframe via embed token session

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: State snapshot &lt; 200 ms p95 local; SSE delivery within 2s of moderation action; display strip renders ≤ `queue_visible_count` (default 8) entries

**Constraints**: All queue/SSE/state endpoints require `jukebox_session`; Spanish UI; max 100 `queued`; duplicate active `youtube_video_id` blocked; dev-submit gated by env flag

**Scale/Scope**: Single event; ~10 new API routes; 3 display child components + 2 services; admin moderation section

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` into `backend-api` + `app-core` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted; consolidation required before code |
| V. Tests for changed behavior | Pass | Queue transitions, limits, SSE, auth policy, build |
| VI. Sibling conventions | Pass | `/api/state` + SSE like bull; embed session for kiosk; layout uses `app_height_px` / future `bull:config` |

**Post-design re-check**: All gates pass. No constitution violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/changes/004-kiosk-display-queue/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/contract-deltas.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                 # mount queue + state routers
│   ├── models.py               # + QueueEntry, JukeboxRuntime, status enum
│   ├── schemas.py              # state, queue DTOs
│   ├── bootstrap.py            # + ensure_jukebox_runtime
│   ├── services/
│   │   ├── queue_service.py    # approve, reject, skip, ordering
│   │   ├── state_service.py    # build_state, bump_revision
│   │   └── youtube_meta.py     # oEmbed fetch, id parse
│   └── routers/
│       ├── state.py            # GET /state, GET /events/stream
│       └── queue.py            # pending, approve, reject, skip, dev-submit
├── alembic/versions/
│   └── 0003_queue_and_runtime.py
└── tests/
    ├── test_queue.py
    ├── test_state.py
    ├── test_sse.py
    └── test_auth_policy.py     # update public route list

frontend/src/app/
├── display/
│   ├── display.component.*
│   ├── youtube-player.component.*
│   ├── qr-panel.component.*
│   └── queue-strip.component.*
├── services/
│   ├── display-state.service.ts
│   └── queue-admin.service.ts
└── admin/
    └── admin.component.*       # + moderation section
```

**Structure Decision**: Monorepo `backend/` + `frontend/` per 001; display split into focused child components per contract deltas.

## Phase 0 — Research

See [research.md](./research.md). All technical choices resolved (layout %, SSE+snapshot, oEmbed, dev-submit, IFrame API, QR lib).

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |

### Backend design

1. **Migration `0003`**: `queue_entry_status` enum, `queue_entries`, `jukebox_runtime`
2. **`queue_service.py`**: state transitions, duplicate check, 100-cap, position recompute; `skip` advances `playing` or starts first `queued` when idle
3. **`state_service.py`**: `build_state_response()`, `bump_revision()`; includes `event_config` subset + ordered queue strip
4. **`youtube_meta.py`**: parse URL/ID (v1 rules from 001), oEmbed title/thumbnail
5. **`routers/state.py`**: `GET /api/state`; `GET /api/events/stream` with revision-filtered broadcast (in-memory subscriber set per process)
6. **`routers/queue.py`**: pending list, approve, reject, skip, conditional dev-submit
7. **Tests**: fixtures for pending/queued/playing; SSE revision increment; auth policy update

### Frontend design

1. **`DisplayStateService`**: initial `GET /api/state`, `EventSource` to `/api/events/stream` with credentials, reconnect backoff
2. **`DisplayComponent`**: flex column layout 90/10; error panel unchanged from 002
3. **`YoutubePlayerComponent`**: load IFrame API; idle when no `now_playing`; on `ENDED` call skip/advance endpoint (or delegate to service)
4. **`QrPanelComponent`**: generate QR for `/participar`; show `name` + instructions
5. **`QueueStripComponent`**: compact horizontal list, title truncate + vote badge
6. **`QueueAdminService` + admin UI**: pending table, approve/reject, **Iniciar reproducción** / **Saltar canción** controls, preview links
7. **CSS**: `--jukebox-app-height` from state; queue strip `flex: 0 0 10%`; QR panel in US1 layout (same phase as player + queue strip)

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts

Merge contract deltas; update `specs/manifest.yml` (004 active → implemented when done).

### Phase B — Backend core

Models, migration, queue + state services, routers, pytest.

### Phase C — Frontend display

DisplayStateService, layout shell, YouTube + QR + queue strip components.

### Phase D — Frontend admin

Moderation section wired to queue APIs.

### Phase E — SSE integration

End-to-end: approve in admin → kiosk updates without reload.

### Phase F — Validation

pytest, build, quickstart manual paths, 002 display-error regression.

## Risks

| Risk | Mitigation |
|------|------------|
| SSE behind nginx buffering | `X-Accel-Buffering: no`; heartbeat comments |
| YouTube autoplay blocked in dev browser | Document kiosk vs desktop; mute policy in player opts |
| EventSource 401 handling | Snapshot fails → `session_expired`; match 002 interceptor |
| oEmbed rate limits | Cache title/thumbnail on row; fallback title |
| No participant submit for demos | `dev-submit` env flag + pytest fixtures |

## Complexity Tracking

> No violations.
