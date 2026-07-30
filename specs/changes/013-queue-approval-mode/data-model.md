# Data Model Delta: 013-queue-approval-mode

## Persistence (new migration `0009`)

### `event_config.queue_mode` (new column)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| queue_mode | VARCHAR(16) | NOT NULL, default `moderated` | `moderated` \| `free` |

**Backfill**: existing rows get `moderated` (preserves current behavior, FR-002).

**Bootstrap**: `ensure_event_config` seeds `queue_mode='moderated'` on new installs.

### Enum: `QueueMode` (application)

| Value | UI label (es) | Submit behavior |
|-------|---------------|-----------------|
| `moderated` | Moderado | `pending_review` → operator approve/reject |
| `free` | Libre | direct `queued` + `emit_song_approved` |

## Participant submission limits (behavioral, no schema change)

| Mode | Counted statuses | Cap source |
|------|------------------|------------|
| `moderated` | `pending_review` | `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` (default 2) |
| `free` | `queued` (participant's own) | same env setting, same 429 `pending submission limit reached` detail |

Playing / played entries do not count toward either cap (unchanged).

## Queue entry lifecycle (delta)

```text
[moderated submit]
  --> pending_review --approve--> queued --playing--> played
                   \--reject--> rejected

[free submit]
  --> queued (+ song.approved notification) --playing--> played
```

Pending entries created under `moderated` remain `pending_review` after switch to `free` until operator acts (FR-008, FR-010).

## API DTOs

### `EventConfigRead` (extended)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| queue_mode | string | yes | `moderated` \| `free` |
| … | | | existing summary fields unchanged |

`EventConfigSummary` — **unchanged** (no `queue_mode` on kiosk/participant state).

### `QueueModeUpdate`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| queue_mode | string | yes | enum `moderated` \| `free` |

### `POST /api/queue/submit` response (unchanged shape)

| Mode | Typical `status` in response |
|------|------------------------------|
| `moderated` | `pending_review` |
| `free` | `queued` |

## SSE

No new event type. Mode change calls `bump_revision` → existing `state` event (queue snapshot unchanged; clients reload admin mode from `GET /api/event-config` after successful PUT or on init).

Free submit bumps revision and may emit `notification` (`song.approved`) per 007 routing.

## Frontend state (admin)

| State | Source |
|-------|--------|
| `queueMode` | `EventConfigRead.queue_mode` from `GET /api/event-config` |
| `pending` | existing `GET /api/queue/pending` + SSE refresh |
| Libre info banner | `queueMode === 'free'` |

Confirmation dialog gates `PUT /api/event-config/queue-mode`.
