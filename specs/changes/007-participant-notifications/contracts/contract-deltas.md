# Contract Deltas: 007-participant-notifications

**Status**: draft — merge into active contracts before implementation

## backend-api

### SSE extension (participant + operator + display)

Existing: `GET /api/events/stream` — `event: state` with `StateResponse` payload.

**Add** (same stream, same auth):

| SSE event | Payload | When |
|-----------|---------|------|
| `notification` | `NotificationEventRead` | After `song.approved` or `song.up_next` emit |

#### `NotificationEventRead`

```json
{
  "type": "song.approved",
  "queue_entry_id": "uuid",
  "participant_id": "uuid",
  "title": "Song title"
}
```

`type` enum: `song.approved` | `song.up_next`

#### Emit rules

| Backend action | Notification | Target |
|----------------|--------------|--------|
| `POST /api/queue/{id}/approve` success | `song.approved` | `submitted_by_participant_id` if set |
| `POST /api/queue/skip` advances to next track | `song.up_next` | owner of **next** entry before `playing` |
| `POST /api/queue/{id}/reject` | none | — |
| `POST /api/votes` reorder | none | — |

Clients other than `/participar` MUST ignore `notification` events. Server broadcasts on the shared stream; `/participar` MUST filter by `participant_id` before showing a toast (SC-003).

### Schemas

Add `NotificationEventRead` to `backend/app/schemas.py`.

### Services

- `notification_service.py` — `emit_song_approved`, `emit_song_up_next`
- `sse_hub.py` — `broadcast_notification`

### Tests

- `backend/tests/test_notifications.py`

### Unchanged

- REST routes (no new HTTP endpoints)
- Vote API, submit API, moderation shapes
- `state` SSE event format

## app-core

### `/participar` toast UX

| Rule | Value |
|------|-------|
| Position | Fixed bottom (safe area) |
| Queue | FIFO, one visible |
| Auto-dismiss | 8 seconds |
| Manual dismiss | Always available |
| Dedupe | `type:queue_entry_id` per page session |
| Retroactive | None (no catch-up banner) |

#### Spanish toast copy

| type | Template |
|------|----------|
| `song.approved` | «{title}» ha sido aprobada y está en cola. |
| `song.up_next` | «{title}» es la siguiente canción. |

### New / extended services

| Service | Responsibility |
|---------|----------------|
| `NotificationToastService` | FIFO queue, dedupe, timers, dismiss |
| `ParticipantStateService` | Listen for SSE `notification`; forward to toast service |
| `NotificationToastComponent` | Bottom toast UI in participate layout |

### Display (`/`)

Unchanged — ignores `notification` SSE events; continues `state` only.

### Deferred

- Web Push (v1.1)
- Reject toast
- Notification inbox/history

## ops-platform

No new env vars.
