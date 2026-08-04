# Contract Deltas: 017-admin-queue-history-filler

**Status**: merged into active contracts (017 implemented).

Modifies: `backend-api`, `app-core`. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### Queue entry schema (extended)

**`queue_entries` columns** (migration `0010`):

| Column | Type | Default |
|--------|------|---------|
| priority | VARCHAR(16) NOT NULL | `normal` |
| source | VARCHAR(24) NOT NULL | `participant` |
| finished_at | TIMESTAMPTZ NULL | — |

**`QueueEntryRead`** (all endpoints returning queue entries): add `priority: "normal" | "low"`.

Values: `normal` = participant-requested or re-queued with historical participant; `low` = filler / operator-only.

### Queue ordering (changed)

Active `queued` ordering is now:

1. `vote_count` descending
2. `priority` ascending (`normal` before `low`)
3. `created_at` ascending

Applies to `_top_queued`, `_recompute_positions`, `get_queue_strip`, `get_all_queued`, vote reorder.

Filler entries in `queued` remain **votable** (`POST /api/votes` unchanged semantics).

### Duplicate video rule (extended)

Applies to participant submit, requeue, reserve add, operator direct enqueue, and reserve→queue transfer.

Reject with **409** `video already in queue` when the same `youtube_video_id` exists in any of:

- `queue_entries` with status `pending_review`, `queued`, or `playing`
- `filler_reserve_entries`

### History (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/queue/history` | operator session | 200 `HistoryListResponse` |
| POST | `/api/queue/history/{id}/requeue` | operator session | 201 `QueueEntryRead` |

**`GET /api/queue/history` query params**:

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| status | `played` \| `rejected` | both | filter |
| page | int ≥ 1 | 1 | |
| page_size | int | 25 | max 100 |

Ordered by `finished_at DESC`.

**`POST /api/queue/history/{id}/requeue`**:

- Source row must be `played` or `rejected`.
- Creates **new** `queue_entry` in `queued` (never `pending_review`), even in `queue_mode=moderated`.
- Priority: `normal` if historical row had `submitted_by_participant_id`; else `low`.
- `source` = `operator_requeue`.
- Duplicate rule: 409 if same `youtube_video_id` in `pending_review`, `queued`, `playing`, or `filler_reserve_entries`.

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated | 401 | `not authenticated` |
| History row not found | 404 | `queue entry not found` |
| Not terminal status | 409 | `invalid status transition` |
| Duplicate video | 409 | `video already in queue` |
| Queue full | 409 | `queue is full` |

On success: `bump_revision`, SSE `state`; may auto-start playback per 014 rules.

Participant session on history routes → **401** `not authenticated`.

### Operator direct enqueue (new, FR-011)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/queue/operator-submit` | operator session | 201 `QueueEntryRead` |

Body: `OperatorQueueSubmitRequest` — `{ "youtube_url_or_id": string, "search_query"?: string }` (same YouTube validation as participant submit).

Creates `queue_entry` directly in `queued` with `priority=low`, `source=operator_direct`. Does **not** pass through reserve. Duplicate and queue-full rules apply.

Participant session → **401**.

On success: `bump_revision`, SSE `state`; may auto-start playback per 014 rules.

### Filler reserve (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/filler-reserve` | operator session | 200 `FillerReserveListResponse` |
| POST | `/api/filler-reserve` | operator session | 201 `FillerReserveEntryRead` |
| DELETE | `/api/filler-reserve/{id}` | operator session | 204 |
| PUT | `/api/filler-reserve/reorder` | operator session | 200 `FillerReserveListResponse` |
| POST | `/api/filler-reserve/{id}/enqueue` | operator session | 201 `QueueEntryRead` |
| POST | `/api/filler-reserve/enqueue-batch` | operator session | 201 `QueueEntryRead[]` |

**`POST /api/filler-reserve`** body: `FillerReserveAddRequest` — same YouTube validation as submit.

- Max 50 reserve items → 409 `filler reserve is full`
- Duplicate `youtube_video_id` in reserve or active queue → 409 `video already in queue`
- New item appended at end (`position = max + 1`)

**`PUT /api/filler-reserve/reorder`** body: `{ "ordered_ids": string[] }` — must include all current IDs exactly once; reassigns `position` 1..n.

**`POST .../enqueue`** / **`enqueue-batch`**: consume item(s) from reserve, create `queued` entries (`priority=low`, `source=operator_filler`); respect `MAX_QUEUED_ENTRIES` (100).

Participant session on all `/api/filler-reserve/*` routes → **401**.

### Auto-inject behavior (new)

When `event_config.filler_auto_inject_enabled` is `true` and there is no `playing` entry and no `queued` entries:

1. Take reserve item at `position = 1`
2. Delete from reserve
3. Enqueue as `queued`, `priority=low`, `source=auto_inject`
4. Apply existing auto-start-on-enqueue (014)

Triggered after playback advance leaves queue empty and when idle start would otherwise 409 `nothing to advance`.

When `filler_auto_inject_enabled` is `false`: no automatic transfer; reserve unchanged until manual enqueue.

### Event configuration — filler toggle (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| PUT | `/api/event-config/filler-auto-inject` | operator session | 200 `EventConfigRead` |

Body: `{ "filler_auto_inject_enabled": boolean }`.

**`EventConfigRead`**: add `filler_auto_inject_enabled: boolean` (default `true` on migration).

`EventConfigSummary` — **unchanged**.

### YouTube search (changed)

| Method | Path | Auth | Change |
|--------|------|------|--------|
| GET | `/api/youtube/search` | operator **or** participant | operator may search without participant rate limit |

Participant path unchanged (rate limit per participant id).

### Terminal status timestamps (changed)

`reject_entry` and `skip_or_advance` (when marking `played`) MUST set `finished_at = now()` on the affected row.

### Tests (constitution V)

- `backend/tests/test_queue_history.py` (new) — include participant 401 on history; requeue duplicate when video in reserve; assert `revision` increases after requeue (FR-015)
- `backend/tests/test_filler_reserve.py` (new) — include participant 401 on reserve; operator direct submit; `source` audit matrix (FR-017); assert `revision` after inject/enqueue (FR-015)
- Extend `test_queue.py`, `test_votes.py`, `test_state.py` for priority ordering
- Frontend: admin service/component tests optional

---

## app-core

### Admin `/admin` — new sections

**Historial** (operator only):

- Paginated list of `played` and `rejected` entries
- Filter by status; columns: title, thumbnail, `youtube_video_id`, status, `finished_at`, `source`, rejection reason, participant name
- **Re-encolar** per row with confirm; error toast on 409

**Reserva de relleno** (operator only):

- List ordered reserve items with low-priority indicator
- Add via URL input + YouTube search (reuse search UI pattern from participate)
- **Añadir directo a cola** (bypass reserve) via `POST /api/queue/operator-submit`
- Delete item; drag-and-drop or move controls → `PUT /api/filler-reserve/reorder`
- **Añadir a cola** from reserve (single / multi-select)
- Toggle **Inyección automática** → `PUT /api/event-config/filler-auto-inject`

Spanish labels throughout.

### Participar `/participar`

- No historial UI
- No reserve UI
- Filler songs in public queue: **no visual distinction** (deferred UX; same row as user songs)
- Voting enabled on filler `queued` entries

### Display `/` (kiosk)

- No UI change; filler appears in queue strip via SSE `state`
- Order reflects new priority tie-break

---

## ops-platform

No topology changes. Optional doc note: reserve max 50 and queue max 100 are service constants.
