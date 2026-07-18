# Contract Deltas: 004-kiosk-display-queue

**Status**: implemented — merged into active contracts

## backend-api

### New endpoints

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/state` | session | 200 `StateResponse` |
| GET | `/api/events/stream` | session | 200 `text/event-stream` (SSE) |
| GET | `/api/queue/pending` | session | 200 `PendingListResponse` |
| POST | `/api/queue/{id}/approve` | session | 200 `QueueEntryRead` |
| POST | `/api/queue/{id}/reject` | session | 200 `QueueEntryRead` |
| POST | `/api/queue/skip` | session | 200 `StateResponse` |
| POST | `/api/queue/dev-submit` | session | 201 `QueueEntryRead` |

`POST /api/queue/dev-submit` body: `{ "youtube_url_or_id": string }`. **Development/tests only** — registered when `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true` (default false in production). Creates `pending_review` entry.

### SSE event format

```
event: state
data: {"revision":42,"now_playing":{...},"queue":[...],"event_config":{...}}

```

- Initial connect: optional immediate `state` event with current snapshot
- Subsequent events only when `revision` changes
- Heartbeat comment line every 30s (`: ping\n\n`) to defeat proxies

### Error shapes (new)

| Case | Status | Body |
|------|--------|------|
| Queue entry not found | 404 | `{"detail":"queue entry not found"}` |
| Invalid status transition | 409 | `{"detail":"invalid status transition"}` |
| Duplicate active video | 409 | `{"detail":"video already in queue"}` |
| Queue full (100 queued) | 409 | `{"detail":"queue is full"}` |
| Nothing to advance (no playing, no queued) | 409 | `{"detail":"nothing to advance"}` |
| Invalid YouTube id/url | 422 | `{"detail":"invalid youtube reference"}` |

### Skip / advance semantics (`POST /api/queue/skip`)

| Server state | Behavior | Status |
|--------------|----------|--------|
| `playing` exists | Current → `played`; promote next `queued` → `playing` (or idle if queue empty) | 200 `StateResponse` |
| No `playing`, `queued` exists | Promote top `queued` → `playing` (start playback) | 200 `StateResponse` |
| No `playing`, no `queued` | No-op | 409 `nothing to advance` |

### Public vs protected (after 004)

| Public | Protected |
|--------|-----------|
| `GET /api/health` | `GET /api/auth/me` |
| `POST /api/auth/login` | `GET/POST/DELETE /api/tokens` |
| `POST /api/auth/token` | `GET /api/state` |
| | `GET /api/events/stream` |
| | `GET /api/queue/pending` |
| | `POST /api/queue/{id}/approve` |
| | `POST /api/queue/{id}/reject` |
| | `POST /api/queue/skip` |
| | `POST /api/queue/dev-submit` (when enabled) |

Update `backend/tests/test_auth_policy.py` with canonical public list for 004.

### New persistence

- Tables `queue_entries`, `jukebox_runtime` (see `data-model.md`)
- Alembic `0003_queue_and_runtime.py`

### State service

- `bump_revision(db)` on approve, reject, skip, vote change (future)
- `build_state_response(db)` shared by REST and SSE

## app-core

### Display layout (replaces 001 placeholder grid)

| Region | Size | Content |
|--------|------|---------|
| Top row | ~90% height | Grid 2fr / 1fr |
| Player panel | 2/3 top width | `YoutubePlayerComponent` |
| QR panel | 1/3 top width | `QrPanelComponent` |
| Queue strip | ~10% height, full width | `QueueStripComponent` |

CSS variable `--jukebox-app-height` from `event_config.app_height_px` (default 720). Error panel from 002 unchanged — replaces entire layout when `displayError` set.

### New components

| Component | Route | Responsibility |
|-----------|-------|----------------|
| `YoutubePlayerComponent` | `/` child | IFrame API, idle state, plays `now_playing.youtube_video_id` |
| `QrPanelComponent` | `/` child | QR to `/participar`, event title/instructions |
| `QueueStripComponent` | `/` child | Horizontal/list compact rows: title + vote count |
| `DisplayComponent` | `/` | Layout shell, error state, wires `DisplayStateService` |

### New services

| Service | Responsibility |
|---------|----------------|
| `DisplayStateService` | `GET /api/state` bootstrap, SSE `EventSource` with credentials, exposes `state$` |
| `QueueAdminService` | pending list, approve, reject, skip for `/admin` |

### Admin UI (004)

- **Moderación** section: pending table, approve/reject, playback controls
- Playback controls: **Iniciar reproducción** when idle + `queued` exists; **Saltar canción** when `playing`; disabled when idle + empty queue
- YouTube preview: `<a target="_blank" rel="noopener">` to `https://www.youtube.com/watch?v={id}`
- Spanish feedback for 409 errors (cola llena, duplicado, etc.)
- Tokens + logout from 002 remain

### Display behavior

- On init (authenticated, no `displayError`): load state, open SSE
- On SSE `state` event: update player id, queue strip, event title for QR
- SSE disconnect: exponential backoff reconnect
- 401 on state/SSE: existing `session_expired` UX (no `/login` redirect)

### Dependencies (frontend packages)

- `qrcode` or `angularx-qrcode` for QR generation
- YouTube IFrame API loaded via script tag in `angular.json` or dynamic loader

### Styling notes

- Queue strip: single-line or truncated titles, vote badge, horizontal scroll if overflow
- No placeholder strings (`Reproductor YouTube (2/3)`, etc.)

### Product baseline update

Supersedes 001 display layout: panel C is no longer full-width below; queue is ~10% height strip (FR-013).

### Deferred (constitution VI — kiosk iframe protocol)

- `bull:config`, `bull:resize`, `bull:ping` postMessage handlers — dedicated kiosk-screen change
- 004 sets `--jukebox-app-height` from `event_config.app_height_px` only

## ops-platform

No changes (003 delivered).
