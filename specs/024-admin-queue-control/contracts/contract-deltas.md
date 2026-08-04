# Contract Deltas: 024-admin-queue-control

**Status**: pending merge at implement.

Modifies: `backend-api`, `app-core`. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### Active queue (operator)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/queue/active` | operator session | 200 `ActiveQueueListResponse` |
| DELETE | `/api/queue/active` | operator session | 200 `StateResponse` |
| DELETE | `/api/queue/active/{id}` | operator session | 200 `StateResponse` |
| POST | `/api/queue/{id}/play-now` | operator session | 200 `StateResponse` |
| PATCH | `/api/queue/{id}/vote-count` | operator session | 200 `StateResponse` |

Participant session → 401 `not authenticated` on all routes above.

Existing `POST /api/queue/skip` unchanged (UI relocates to Cola de reproducción panel).

### `ActiveQueueListResponse` (**new**)

| Field | Type |
|-------|------|
| `now_playing` | `ActiveQueueEntryRead` \| null |
| `queued` | `ActiveQueueEntryRead[]` |

### `ActiveQueueEntryRead` (**new**)

`QueueEntryRead` fields plus:

| Field | Type |
|-------|------|
| `submitted_by_display_name` | string \| null |
| `source` | `QueueEntrySourceLiteral` |

### `VoteCountUpdateRequest` (**new**)

| Field | Type |
|-------|------|
| `vote_count` | int (≥ 0) |

### `DELETE /api/queue/active`

Permanently deletes all `queue_entries` with `status` `queued` or `playing`; clears `now_playing`; does **not** auto-inject filler; `bump_revision` + SSE `state`.

### `DELETE /api/queue/active/{id}`

Permanently deletes one active entry. If deleted entry was `playing` and other `queued` exist → promote next (same as skip tail). If `playing` with no `queued` → idle. Votes CASCADE.

### `POST /api/queue/{id}/play-now`

Target must be `queued`. Promotes to `playing`. If another was `playing` → mark `played` with `finished_at` (historial), not delete. 409 if target already `playing` or not active.

### `PATCH /api/queue/{id}/vote-count`

Sets `vote_count`; reorders `queued`; does not interrupt current `playing`; no participant vote-limit enforcement.

### Errors (representative)

| Case | Status | `detail` |
|------|--------|----------|
| Not operator | 401 | `not authenticated` |
| Entry not found | 404 | `queue entry not found` |
| Invalid status for action | 409 | `invalid status` / `entry not active` |
| Negative vote_count | 422 | validation error |
| Active queue empty on vaciar | 200 | empty `StateResponse` (idempotent) |

---

## app-core

### Admin `/admin` — Cola de reproducción panel (**new**)

- Collapsible **Cola de reproducción**, **collapsed by default**, positioned **immediately after Moderación**, **before Historial**.
- Header badge: count of active entries (`now_playing` + `queued` length), live via SSE.
- On expand: `GET /api/queue/active`; refresh on operator SSE `state` while expanded.

**Moved from Moderación** (FR-016–FR-018):
- Playback status label (`playbackStatusLabel`)
- Audio hint (`playbackAudioHint`)
- Buttons **Iniciar reproducción** / **Saltar canción** → `POST /api/queue/skip` (existing)

**Moderación** retains: queue mode (Moderado/Libre), pending review table, approve/reject. **No** playback controls or status block.

### Panel actions

| UI action | API |
|-----------|-----|
| Vaciar cola | `DELETE /api/queue/active` + confirm dialog |
| Forzar reproducir | `POST /api/queue/{id}/play-now` |
| Modificar votos | `PATCH /api/queue/{id}/vote-count` |
| Eliminar de la cola | `DELETE /api/queue/active/{id}` + confirm dialog |
| Iniciar / Saltar | `POST /api/queue/skip` |

List row fields: title, thumbnail, votes, position, status, priority, duration, source, submitter name, created_at, **Previsualizar** link (Spanish labels).

### Participant `/participar`

- Entries hard-deleted from cola appear removed from **Mis canciones** on next SSE `state` / refresh (no contract change to participant routes).

---

## ops-platform

No changes.
