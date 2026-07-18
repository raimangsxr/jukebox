# Data Model Delta: 006-participant-oauth-submit

## Table: `participants` (extend 005)

| Column | Type | Notes |
|--------|------|-------|
| google_sub | string(255) nullable, **unique** | Stable Google subject; null for dev-auth-only rows |
| email | string(255) nullable | From Google userinfo |
| avatar_url | string(500) nullable | From Google picture |

Existing columns unchanged: `id`, `display_name`, `created_at`.

### Upsert rules

| Case | Behavior |
|------|----------|
| Callback with known `google_sub` | Update profile fields; same `id` |
| Callback with new `google_sub` | Insert row |
| Dev-auth (005) | `google_sub` null; allowed |

## Table: `queue_entries` (unchanged schema)

006 uses existing `submitted_by_participant_id` (nullable since 004).

### Participant submit side effects

| Field set on submit | Value |
|---------------------|-------|
| status | `pending_review` |
| submitted_by_participant_id | current participant `id` |
| original_query | submitted URL/id string |
| title, thumbnail_url | from oEmbed |
| vote_count | 0 |

## Submit validation (service)

| Rule | Enforcement |
|------|-------------|
| Max 2 `pending_review` per participant | Count before insert → 429 |
| Max 1 own `queued`+`playing` | Count by `submitted_by_participant_id` → 429 |
| No active duplicate `youtube_video_id` | Existing duplicate check → 409 |
| Valid YouTube parse + metadata | `youtube_meta` → 422 on failure |

## API DTOs (reference)

- `SubmitRequest`: `{ youtube_url_or_id: string }`
- `SubmissionListResponse`: `{ entries: QueueEntryRead[] }`
- `ParticipantRead` extended: optional `email`, `avatar_url` (google_sub never exposed to client)

## Alembic

- `0005_participant_google_profile.py`

## OAuth (ephemeral)

- Signed `state` query param; no DB table for v1
