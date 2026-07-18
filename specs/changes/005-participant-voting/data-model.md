# Data Model Delta: 005-participant-voting

## New table: `participants`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid string PK | `str(uuid4())` |
| display_name | string(120) | placeholder until 006 Google profile |
| created_at | timestamptz | server default |

### Planned in 006 (not 005 migration)

| Column | Type | Notes |
|--------|------|-------|
| google_sub | string unique | |
| email | string | |
| avatar_url | string nullable | |

## New table: `votes`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid string PK | |
| queue_entry_id | uuid FK → queue_entries.id | CASCADE delete |
| participant_id | uuid FK → participants.id | CASCADE delete |
| created_at | timestamptz | server default |

### Indexes

- `(participant_id, created_at DESC)` — rolling window count
- `(queue_entry_id)` — analytics / future undo

## Existing: `queue_entries`

- `vote_count` incremented on each valid vote (denormalized)
- `position` recomputed among `queued` after vote (reuse 004 `queue_service._recompute_positions`)

## Session payload

- Signed cookie `jukebox_participant_session` → `participants.id` (uuid string)
- Operator `jukebox_session` / `user_id` unchanged

## Vote rules (service layer)

| Rule | Enforcement |
|------|-------------|
| Max 2 votes per 5 min | `COUNT(votes) WHERE participant_id AND created_at >= now()-5min` |
| Target status `queued` | 409 if not `queued` |
| Same entry twice | Allowed (two vote rows, +2 count) |
| Reorder | `vote_count DESC`, `created_at ASC` among `queued` |
| SSE | `bump_revision` after successful vote |

## Alembic

- `0004_participants_and_votes.py`

## API DTOs (reference for contract)

- `ParticipantRead` — id, display_name
- `ParticipantStateResponse` — revision, now_playing, queue (all `queued`), votes_remaining (0–2), event_config subset
- `VoteCreateRequest` — queue_entry_id
- `VoteResponse` — vote id, votes_remaining, optional embedded state snapshot
