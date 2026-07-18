# Data Model Delta: 004-kiosk-display-queue

## New enum: `queue_entry_status`

| Value | Meaning |
|-------|---------|
| `pending_review` | Awaiting moderator decision |
| `rejected` | Moderator rejected |
| `queued` | Approved, waiting to play |
| `playing` | Currently on kiosk player |
| `played` | Finished playback |

## New table: `queue_entries`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid string PK | `str(uuid4())` |
| youtube_video_id | string(11) | required, indexed |
| title | string(500) | from oEmbed or fallback |
| thumbnail_url | string(500) nullable | |
| duration_sec | int nullable | reserved; null in 004 |
| submitted_by_participant_id | uuid nullable | no FK until change 006 |
| vote_count | int | default 0, denormalized |
| position | int nullable | 1..N among `queued`; null when not queued |
| status | enum | `queue_entry_status` |
| rejection_reason | string(200) nullable | set on reject |
| original_query | string(500) | URL or id submitted |
| created_at | timestamptz | server default |
| approved_at | timestamptz nullable | set on transition to `queued` |

### Indexes

- `(status, vote_count DESC, created_at ASC)` for queue strip queries
- `(youtube_video_id, status)` for active duplicate checks (partial unique enforcement in service layer for active statuses)

## New table: `jukebox_runtime` (singleton id=1)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | always `1` |
| now_playing_entry_id | uuid nullable FK → queue_entries.id | SET NULL on delete |
| revision | int | default 0; increment on any display-relevant change |
| updated_at | timestamptz | |

Bootstrap: `ensure_jukebox_runtime()` creates row `id=1` on app startup (idempotent).

## Existing: `event_config` (unchanged schema)

Used fields: `name`, `subtitle`, `queue_visible_count`, `app_height_px`, `theme`.

## State machine

```text
pending_review --approve--> queued --advance/skip--> playing --advance/end--> played
       |                         ^
       reject                    | (reorder among queued via vote_count)
       v                         |
   rejected                  (vote_count changes in 005)
```

### Transition rules (service layer)

| Action | From | To | Side effects |
|--------|------|-----|--------------|
| Approve | `pending_review` | `queued` | Set `approved_at`; assign `position`; bump `revision`; enforce max 100 `queued` |
| Reject | `pending_review` | `rejected` | Optional `rejection_reason`; bump `revision` |
| Skip / advance (`POST /api/queue/skip`) | `playing` | `played` (+ next) | Mark current `played`; promote next `queued` to `playing` if any; bump `revision` |
| Skip / advance (idle start) | — | `playing` | When no `playing` but `queued` exists: promote top `queued` to `playing`; bump `revision` |
| Skip / advance (no-op) | — | — | 409 when no `playing` and no `queued` |

### Invariants

- At most one `playing` entry per event.
- No duplicate `youtube_video_id` across `pending_review`, `queued`, `playing`.
- Max 100 rows with `status = queued`.
- Display strip reads top `queue_visible_count` rows where `status = queued` (not including `playing`).

## Alembic

- `0003_queue_and_runtime.py` — creates enum, `queue_entries`, `jukebox_runtime`

## API DTOs (reference for contract)

- `QueueEntryRead` — id, youtube_video_id, title, thumbnail_url, vote_count, position, status, created_at
- `StateResponse` — revision, event_config subset, now_playing (nullable QueueEntryRead), queue (list QueueEntryRead)
- `PendingListResponse` — entries with status `pending_review`
- `RejectBody` — optional `reason` (max 200)
