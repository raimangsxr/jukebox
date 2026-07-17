# Data Model: amrn-jukebox (product baseline)

**Change 001 implements**: `users`, `event_config` only.  
**Future changes** add entities below.

## Implemented in 001

### `users` (operator)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | |
| username | string(64) unique | operator login |
| password_hash | string | bcrypt |
| created_at | timestamptz | |

### `event_config` (singleton id=1)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | always `1` |
| name | string(200) | event title |
| subtitle | string(200) | |
| app_height_px | int | default 720 |
| theme | string(8) | `dark` \| `light` |
| queue_visible_count | int | default 8 |
| updated_at | timestamptz | |

## Planned (002+)

### `participants` (Google OAuth)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| google_sub | string unique | stable Google id |
| email | string | |
| display_name | string | |
| avatar_url | string nullable | |
| created_at | timestamptz | |

### `api_tokens` (embed)

Same shape as amrn-bull `api_tokens` (operator-scoped iframe tokens).

### `queue_entries`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| youtube_video_id | string(11) | |
| title | string | |
| thumbnail_url | string | |
| duration_sec | int nullable | |
| submitted_by_participant_id | uuid FK | |
| vote_count | int | denormalized |
| position | int | among `queued` |
| status | enum | pending_review, rejected, queued, playing, played |
| rejection_reason | string(200) nullable | |
| original_query | string | link or text submitted |
| created_at | timestamptz | |
| approved_at | timestamptz nullable | |

### `votes`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| queue_entry_id | uuid FK | |
| participant_id | uuid FK | |
| created_at | timestamptz | |

### `participant_vote_windows`

Rolling 2 votes / 5 min — implement as derived from `votes` or dedicated window row (TBD in voting change).

### `jukebox_runtime` (singleton)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | `1` |
| revision | int | SSE versioning |
| now_playing_entry_id | uuid nullable FK | |

## State machine: `queue_entry.status`

```text
pending_review --approve--> queued --advance--> playing --end--> played
       |                         ^
       reject                    | (reorder among queued only)
       v                         |
   rejected                  (vote_count, position)
```

## Invariants

- At most one `playing` entry per event.
- No duplicate `youtube_video_id` in active statuses.
- Max 100 `queued`; max 2 `pending_review` and 1 `queued`+`playing` per participant.
