# backend-api Contract

Status: active. Consolidated from changes **001-foundation-jukebox**, **002-operator-auth-embed-tokens**, **004-kiosk-display-queue**, **005-participant-voting**, **006-participant-oauth-submit**, **007-participant-notifications**, **008-youtube-text-search**, **009-admin-api-key-usage**, **010-hardening-and-polish** (2026-07-22).

## Purpose

FastAPI + Alembic + PostgreSQL service for amrn-jukebox. Owns persistent event configuration, operator authentication, embed tokens, queue state, moderation, and SSE realtime. The Angular SPA is served by a separate `frontend` image in production; every backend route lives under `/api/*`.

## Stack

- Python ≥ 3.11, FastAPI, SQLAlchemy 2.x, Alembic, psycopg 3
- Settings: flat `JUKEBOX_` env prefix via pydantic-settings
- Session cookie: `jukebox_session` (operator)
- Participant cookie: `jukebox_participant_session` (signed, separate from operator)

## Auth endpoints

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/auth/login` | public | 200 `MeResponse` + Set-Cookie |
| POST | `/api/auth/logout` | session | 204 |
| GET | `/api/auth/me` | session | 200 `MeResponse` |
| POST | `/api/auth/token` | public | 200 `MeResponse` + Set-Cookie |

### Token management

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/tokens` | session | 200 `TokenListResponse` |
| POST | `/api/tokens` | session | 201 `TokenCreateResponse` (plaintext once) |
| DELETE | `/api/tokens/{id}` | session | 204 |

## State and SSE (004)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/state` | session | 200 `StateResponse` |
| GET | `/api/events/stream` | operator **or** participant session | 200 `text/event-stream` |

SSE `event: state` payload matches `StateResponse`. Heartbeat comment every 30s. Response header `X-Accel-Buffering: no`.

**Also on the same stream** (`event: notification`, payload `NotificationEventRead`; `event: api_key_usage`, payload `ApiKeyUsageListResponse`; `event: playback_status`, payload `PlaybackStatusRead`):

| `type` | When |
|--------|------|
| `song.approved` | `POST /api/queue/{id}/approve` success and `submitted_by_participant_id` set |
| `song.up_next` | `POST /api/queue/skip` promotes next `queued` entry to `playing` and owner set |

```json
{
  "type": "song.approved",
  "queue_entry_id": "uuid",
  "participant_id": "uuid",
  "title": "Song title"
}
```

**SSE audience routing (010):** the server tags each subscriber at connect time with its authorizing audience (`operator` or `participant:{id}`) and routes events server-side:

- `event: state` → all authorized subscribers.
- `event: api_key_usage` → **operator** subscribers only (never participants).
- `event: playback_status` → **operator** subscribers only (never participants).
- `event: notification` → **only** the target `participant_id`'s subscriber(s).

Ambiguous subscribers default to participant scope (least privilege). This replaces the earlier broadcast-to-all + client-side filtering.

No `notification` on reject, vote reorder, or entries without `submitted_by_participant_id`.

`GET /api/participant/state` returns `ParticipantStateResponse` (all `queued` entries, `votes_remaining`, `searches_remaining`, `votes_quota_reset_at`, `searches_quota_reset_at`, `max_pending_submissions`, `max_searches_10_minutes`, `max_votes_10_minutes`). SSE does not include participant limit fields; clients call `GET /api/participant/state` via `refresh()` on every participant SSE `state` event (multi-tab sync), plus vote/search responses, poll fallback, and client countdown expiry at `00:00`.

## Google OAuth (participant, 006)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/auth/google/config` | public | `{ "enabled": boolean }` |
| GET | `/api/auth/google/login` | public | 302 redirect to Google |
| GET | `/api/auth/google/callback` | public | 302 redirect to return URL + Set-Cookie `jukebox_participant_session` |

Callback success: redirect to `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` with optional `?oauth=ok`. Failure: `?oauth_error=denied|invalid_state|exchange_failed|not_configured`.

## Participant auth and voting (005)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/participant/dev-auth` | public (if enabled) | 200 `ParticipantMeResponse` + Set-Cookie |
| GET | `/api/participant/me` | participant | 200 `ParticipantMeResponse` |
| GET | `/api/participant/state` | participant | 200 `ParticipantStateResponse` |
| GET | `/api/participant/submissions` | participant | 200 `SubmissionListResponse` |
| POST | `/api/votes` | participant | 201 `VoteResponse` |

`ParticipantRead` includes optional `email`, `avatar_url` (no `google_sub` in API).

`POST /api/participant/dev-auth` only when `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true` (default false). Body optional: `{ "display_name": string }`.

`POST /api/votes` body: `{ "queue_entry_id": uuid }`. On success: increment `vote_count`, reorder `queued`, bump `revision`, SSE broadcast.

### Vote errors (005)

| Case | Status | Body |
|------|--------|------|
| Entry not votable | 409 | `{"detail":"entry not votable"}` |
| Vote limit exceeded | 409 | `{"detail":"vote limit exceeded"}` |

Participant session MUST NOT access operator routes (e.g. `POST /api/queue/skip` → 401).

## Queue and moderation (004)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/queue/pending` | session | 200 `PendingListResponse` |
| POST | `/api/queue/{id}/approve` | session | 200 `QueueEntryRead` |
| POST | `/api/queue/{id}/reject` | session | 200 `QueueEntryRead` |
| POST | `/api/queue/skip` | session | 200 `StateResponse` |
| GET | `/api/queue/active` | operator session | 200 `ActiveQueueListResponse` |
| DELETE | `/api/queue/active` | operator session | 200 `StateResponse` |
| DELETE | `/api/queue/active/{id}` | operator session | 200 `StateResponse` |
| POST | `/api/queue/{id}/play-now` | operator session | 200 `StateResponse` |
| PATCH | `/api/queue/{id}/vote-count` | operator session | 200 `StateResponse` |
| POST | `/api/queue/dev-submit` | session (if enabled) | 201 `QueueEntryRead` |
| POST | `/api/queue/submit` | participant | 201 `QueueEntryRead` |

`POST /api/queue/submit` body: `{ "youtube_url_or_id": string, "search_query"?: string }`. Creates `pending_review` with `submitted_by_participant_id`; bumps `revision`. When `search_query` is non-empty after trim, `original_query` = `search:{search_query}`; otherwise stores URL/id string (006).

`PendingListResponse.entries[]` uses `PendingQueueEntryRead`: `QueueEntryRead` plus `submitted_by_display_name` (participant display name when linked). `QueueEntryRead.duration_sec` is populated on submit via YouTube Data API when `JUKEBOX_YOUTUBE_API_KEYS` is configured; otherwise `null`.

### Active queue control (024)

`GET /api/queue/active` returns full active list (not kiosk-limited): `now_playing` + all `queued` entries as `ActiveQueueEntryRead` (`QueueEntryRead` + `submitted_by_display_name`, `source`).

`DELETE /api/queue/active` permanently deletes all `queued` and `playing` rows; clears `now_playing`; does **not** auto-inject filler; `bump_revision` + SSE `state`. Idempotent when empty.

`DELETE /api/queue/active/{id}` permanently deletes one active entry (votes CASCADE). If `playing` and other `queued` exist → promote next (skip tail). Not in historial terminal.

`POST /api/queue/{id}/play-now` promotes `queued` entry to `playing`; if another was `playing` → mark `played` (historial), not delete. No-op if target already `playing`. 409 invalid status.

`PATCH /api/queue/{id}/vote-count` body `{ "vote_count": int ≥ 0 }`; sets denormalized count, reorders `queued`; does not interrupt current `playing`; no participant vote-limit.

Participant session → 401 on all active-queue routes above.

## YouTube search (008)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/youtube/search/config` | public | 200 `SearchConfigResponse` |
| GET | `/api/youtube/search` | participant | 200 `SearchResponse` |

Query: `q` (min length after trim per `JUKEBOX_YOUTUBE_SEARCH_MIN_QUERY_LENGTH`, default 2).

`SearchConfigResponse`: `{ "enabled": boolean }` — `true` when ≥1 API key in `JUKEBOX_YOUTUBE_API_KEYS`.

`SearchResultItem`: `youtube_video_id`, `title`, `channel_title`, `thumbnail_url`.

### Search errors (008)

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated | 401 | `not authenticated` |
| Query too short / whitespace-only | 422 | `invalid search query` |
| Rate limit (configurable / 10 min) | 429 | `search rate limit exceeded` |
| Network / upstream failure | 503 | `youtube search unavailable` |
| All keys exhausted | 503 | `youtube search unavailable` |

Multi-key pool: round-robin per request; automatic retry on per-key quota exhaustion; keys never exposed to clients.

### API key usage (009)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/youtube/api-keys/usage` | operator session | 200 `ApiKeyUsageListResponse` |

`ApiKeyUsageItem`: `index`, `label` (e.g. `Clave 1`), `masked_suffix` (last 4 chars only), `used_count`, `remaining_count`, `daily_limit` (100), `exhausted`.

`ApiKeyUsageListResponse`: `keys[]`, `daily_limit`, `quota_day` (Pacific ISO date), `next_reset_at` (next Pacific midnight ISO-8601).

Accounting: increment `used_count` by 1 before each outbound YouTube Data API request attributed to a pool key (search + `videos.list` metadata); count on attempt regardless of HTTP outcome; do not increment on validation/rate-limit before pool; on Google quota-exhausted set `used_count=100` and `exhausted=true`; Pacific quota day reset.

SSE `event: api_key_usage` on `/api/events/stream` with `ApiKeyUsageListResponse` payload after usage changes or quota-day roll. Kiosk/participant clients ignore unknown events.

### Display playback status (015)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/display/playback-status` | operator session (incl. embed token exchange) | 200 `PlaybackStatusRead` |
| POST | `/api/display/playback-status` | operator session (kiosk display) | 200 `PlaybackStatusRead` |

`PlaybackStatusRead`: `{ "audio_mode": "idle" | "sound" | "muted", "updated_at": ISO-8601 }`.

Kiosk display reports `audio_mode` from the YouTube player; server stores in-memory (single replica) and broadcasts SSE `event: playback_status` to **operator** subscribers only.

### Participant submit errors (006)

API returns stable English `detail` strings; frontend maps to Spanish.

| Case | Status | `detail` |
|------|--------|----------|
| Pending limit | 429 | `pending submission limit reached` |
| Duplicate active video | 409 | `video already in queue` |
| Invalid YouTube / metadata failure | 422 | `invalid youtube reference` |
| Not authenticated | 401 | `not authenticated` |

Participants may submit while they already have songs in `queued` or `playing`; only the pending limit and duplicate-video rules apply.

`JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` (default `2`, min `1`) controls the per-participant `pending_review` cap. `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT` (default `10`, min `1`) and `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT` (default `2`, min `1`) control fixed 10-minute vote and search windows per participant. Window starts on **first consumption at full quota**; `votes_quota_reset_at` / `searches_quota_reset_at` on `participants` anchor the countdown; participant searches persist in `participant_searches`. `GET /api/participant/state` exposes remaining counts, reset timestamps, and all three maxima for client UX.

`POST /api/queue/skip`: advance when `playing`; start when idle + `queued`; 409 `nothing to advance` when empty.

**Auto-start on enqueue** (014): when an entry is enqueued via approve or free-mode submit, if nothing is `playing` and the queue is non-empty, the top `queued` entry is promoted to `playing` automatically (same semantics as idle `POST /api/queue/skip`). If something is already `playing`, enqueue only adds to the queue.

`POST /api/queue/dev-submit` only when `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true`.

### Error shapes

| Case | Status | Body |
|------|--------|------|
| Invalid login | 401 | `{"detail":"invalid credentials"}` |
| Missing session | 401 | `{"detail":"not authenticated"}` |
| Invalid/revoked embed token | 401 | `{"detail":"invalid or revoked token"}` |
| Token not found | 404 | `{"detail":"token not found"}` |
| Queue entry not found | 404 | `{"detail":"queue entry not found"}` |
| Invalid status transition | 409 | `{"detail":"invalid status transition"}` |
| Duplicate active video | 409 | `{"detail":"video already in queue"}` |
| Queue full (100 queued) | 409 | `{"detail":"queue is full"}` |
| Nothing to advance | 409 | `{"detail":"nothing to advance"}` |
| Invalid YouTube id/url | 422 | `{"detail":"invalid youtube reference"}` |
| Malformed body | 422 | FastAPI validation error |

### Session

- `request.session["user_id"]` → `users.id`
- Dependency `get_current_user` → 401 if missing/invalid

### Public vs protected

| Public | Protected (operator) | Protected (participant) | Dual-auth |
|--------|---------------------|-------------------------|-----------|
| `GET /api/health` | `GET /api/auth/me` | `GET /api/participant/me` | `GET /api/events/stream` |
| `POST /api/auth/login` | `GET/POST/DELETE /api/tokens` | `GET /api/participant/state` | |
| `POST /api/auth/token` | `GET /api/state` | `GET /api/participant/submissions` | |
| `GET /api/auth/google/login` | `GET /api/queue/pending` | `POST /api/votes` | |
| `GET /api/auth/google/callback` | `GET /api/state` | `GET /api/participant/submissions` | |
| `POST /api/participant/dev-auth` (when enabled) | `POST /api/queue/*` | `POST /api/queue/submit` | |
| `GET /api/youtube/search/config` | `GET /api/youtube/api-keys/usage` | `GET /api/youtube/search` | |
| | `GET /api/admin/stats` | | |

`backend/tests/test_auth_policy.py` asserts the canonical public route list.

## Health

- `GET /api/health` returns `200` + `{"status": "ok"}` without authentication.

## Security headers

- Every response includes `Content-Security-Policy: frame-ancestors <JUKEBOX_FRAME_ANCESTORS>` (default `'none'`).

## Bootstrap (lifespan)

On application startup:

1. `ensure_operator` — creates operator user from `JUKEBOX_OPERATOR_USERNAME` / `JUKEBOX_OPERATOR_PASSWORD` if missing; if the user exists but the env password differs, updates the stored hash (password ≥ 12 chars). **Not** the PostgreSQL role — DB access uses `JUKEBOX_DATABASE_URL` only.
2. `ensure_event_config` — creates singleton `event_config` row (`id=1`) with defaults if missing.
3. `ensure_jukebox_runtime` — creates singleton `jukebox_runtime` row (`id=1`) if missing.

All helpers are idempotent.

## CORS

When `JUKEBOX_CORS_ALLOW_ORIGINS` is non-empty, credentials are allowed for listed origins. `allow_headers` is scoped to `Content-Type` (not `*`) alongside credentials (010).

## Persistence

### Alembic 0001

Tables: `users`, `event_config` (includes `queue_visible_count` default 8).

### Alembic 0002

Table: `api_tokens` — `id` (uuid PK), `user_id` FK → users, `label`, `token_hash` (bcrypt, unique), `created_at`, `last_used_at`, `revoked_at`.

### Alembic 0003

Tables: `queue_entries`, `jukebox_runtime` (singleton `id=1`, `now_playing_entry_id`, `revision`).

### Alembic 0004

Tables: `participants` (`id`, `display_name`, `created_at`), `votes` (`id`, `queue_entry_id` FK, `participant_id` FK, `created_at`).

### Alembic 0005

Extend `participants`: `google_sub` (unique nullable), `email`, `avatar_url`.

### Alembic 0006

Table: `youtube_api_key_daily_usage` — `key_hash`, `quota_day` (Pacific date), `used_count`, `exhausted`, `updated_at`; unique `(key_hash, quota_day)`.

### Alembic 0007 (010)

Add indexed non-secret `token_prefix` to `api_tokens`.

### Alembic 0008 (010)

Null orphan `queue_entries.submitted_by_participant_id`, then add FK → `participants.id` (`ON DELETE SET NULL`) + index. Reversible.

## Event configuration (010, 013)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/event-config` | operator session | 200 `EventConfigRead` |
| PUT | `/api/event-config` | operator session | 200 `EventConfigRead` |
| PUT | `/api/event-config/queue-mode` | operator session | 200 `EventConfigRead` |

Operates on the singleton `event_config` row (`name`, `subtitle`, `app_height_px`, `theme`, `queue_visible_count`, `queue_mode`, `updated_at`). Migration `0009` adds `queue_mode` (`moderated` \| `free`, default `moderated`).

`EventConfigRead` includes `queue_mode`. `EventConfigSummary` in `StateResponse` / `ParticipantStateResponse` does **not** include `queue_mode`.

`PUT /api/event-config` body: `{ name, subtitle, app_height_px, theme, queue_visible_count }` — does **not** accept `queue_mode`.

`PUT /api/event-config/queue-mode` body: `{ "queue_mode": "moderated" | "free" }`. On success: persist, `bump_revision`, SSE `state`. Invalid enum → `422`. Unauthenticated → `401`.

`PUT /api/event-config` (Evento form) validates: `name` non-empty (≤200), `subtitle` ≤200, `app_height_px` 240–4320, `queue_visible_count` 1–50, `theme` ∈ {`dark`}; invalid → `422`. On success persists, bumps `revision`, and broadcasts `state` over SSE. Participant/anonymous → `401`.

### Participant submit by queue mode (013)

`POST /api/queue/submit` (participant auth):

| `queue_mode` | Created status | Pending list | Notification |
|--------------|----------------|--------------|--------------|
| `moderated` | `pending_review` | yes | `song.approved` on operator approve only |
| `free` | `queued` | no | `song.approved` immediately on submit |

Duplicate video rule unchanged (`409 video already in queue`). Queue full (`409 queue is full`) applies when enqueueing in free mode. Moderation approve/reject unchanged for legacy `pending_review` rows after mode switch.

## Admin statistics (023)

### `GET /api/admin/stats`

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/admin/stats` | operator | 200 `AdminStatsResponse` |

Participant or unauthenticated session → 401. On-demand only (panel expand or manual refresh); no SSE stats payload.

### `AdminStatsResponse`

| Field | Type | Description |
|-------|------|-------------|
| `participants_active_count` | int | Unique participants with ≥1 submission or ≥1 vote |
| `total_submissions` | int | Participant-attributed queue entries (all statuses) |
| `total_votes_cast` | int | Total vote rows |
| `distinct_voted_songs_count` | int | Distinct YouTube videos with aggregated `vote_count` > 0 |
| `queue_counts` | `QueueStatusCounts` | Per-status entry counts |
| `top_submitters` | `ParticipantRankingItem[]` | ≤10 by submission count DESC |
| `top_voters` | `ParticipantRankingItem[]` | ≤10 by votes cast DESC |
| `top_songs` | `SongRankingItem[]` | ≤10 by aggregated votes DESC |

### `QueueStatusCounts`

| Field | Type |
|-------|------|
| `pending_review` | int |
| `queued` | int |
| `playing` | int |
| `played` | int |
| `rejected` | int |

### `ParticipantRankingItem`

| Field | Type |
|-------|------|
| `participant_id` | string |
| `display_name` | string | `display_name`, else email local-part, else `Participante` |
| `count` | int |

### `SongRankingItem`

| Field | Type |
|-------|------|
| `youtube_video_id` | string |
| `title` | string |
| `vote_count` | int |

Tie-break at rank 10: alphabetical by `display_name` or `title`. After `DELETE /api/queue/history`, aggregates reflect surviving rows only. Operator submissions (`submitted_by_participant_id IS NULL`) excluded from submitter rankings.

## Queue history and filler reserve (017)

### Schema (Alembic 0010)

`queue_entries`: `priority` (`normal`|`low`, default `normal`), `source` (`participant`|`operator_filler`|`operator_direct`|`auto_inject`|`operator_requeue`), `finished_at` (set on `played`/`rejected`).

Table `filler_reserve_entries` (max 50, unique `youtube_video_id`). `event_config.filler_auto_inject_enabled` (default `true`).

### Queue ordering (changed)

`queued` order: `vote_count DESC`, `priority ASC` (`normal` before `low`), `created_at ASC`.

### Duplicate video rule (extended)

409 `video already in queue` when same `youtube_video_id` in active queue (`pending_review`, `queued`, `playing`) **or** `filler_reserve_entries`.

### History

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/queue/history` | operator | 200 `HistoryListResponse` |
| POST | `/api/queue/history/{id}/requeue` | operator | 201 `QueueEntryRead` |
| DELETE | `/api/queue/history` | operator | 204 No Content |

`DELETE /api/queue/history`: permanently deletes all `played` and `rejected` rows; ignores UI filter; does not touch active queue or filler reserve; `bump_revision` + SSE `state`; idempotent (empty → 204). Participant → 401.

Query: `status` (`played`|`rejected`), `page`, `page_size` (max 100). Requeue always creates `queued` (never `pending_review`); `source=operator_requeue`; priority `normal` if historical participant submit, else `low`. Participant → 401.

### Operator direct enqueue

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/queue/operator-submit` | operator | 201 `QueueEntryRead` |

Body: `{ youtube_url_or_id, search_query? }`. Creates `queued`, `priority=low`, `source=operator_direct`.

### Filler reserve

| Method | Path | Auth |
|--------|------|------|
| GET/POST | `/api/filler-reserve` | operator |
| DELETE | `/api/filler-reserve` | operator |
| DELETE | `/api/filler-reserve/{id}` | operator |
| PUT | `/api/filler-reserve/reorder` | operator |
| POST | `/api/filler-reserve/{id}/enqueue` | operator |
| POST | `/api/filler-reserve/enqueue-batch` | operator |

Enqueue consumes reserve item(s); `priority=low`, `source=operator_filler`. `DELETE /api/filler-reserve` clears entire reserve (204, `bump_revision`). Participant → 401.

### Filler reserve CSV export/import (018, changed 019)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/filler-reserve/export` | operator | 200 `text/csv` attachment |
| POST | `/api/filler-reserve/import/validate` | operator | 200 `FillerReserveBatchValidation` |
| POST | `/api/filler-reserve/import` | operator | 200 `FillerReserveListResponse` or 422 |

**Export**: UTF-8 BOM; line 1 `url`; lines 2..N+1 canonical `https://www.youtube.com/watch?v={VIDEO_ID}` in position order; empty reserve = header only. `Content-Disposition: attachment; filename="filler-reserve-YYYY-MM-DD.csv"` (UTC date).

**Import validate** (`multipart/form-data` field `file`): line-oriented parsing (one URL per non-empty line; skip header `url`); full validation without DB writes.

**Import commit**: re-validates same file; **appends** validated entries to end of reserve (`position` continues after current max). Does not replace or clear reserve. Empty file or zero addable entries → `can_confirm: false`; commit returns **422**; reserve unchanged.

**Response schema** — `FillerReserveBatchValidation`:

| Field | Meaning |
|-------|---------|
| `add_count` | Entries that will be appended on confirm |
| `skipped_in_reserve` | Duplicates already in reserve (omitted) |
| `skipped_in_queue` | In active queue / pending review (omitted) |
| `skipped_unresolvable` | Metadata unavailable (omitted) |
| `skipped_capacity` | Excess over max 50 (omitted) |
| `can_confirm` | `false` when blocking `errors` non-empty OR `add_count == 0` |
| `errors` | Blocking only: `{ "line": int, "detail": string }` |

**Validation** (both validate and commit):

- Within-file duplicate `youtube_video_id` → blocking.
- Invalid reference format → blocking.
- Rows already in reserve → skip (not error).
- Rows in active queue → skip (not error).
- Unresolvable metadata → skip.
- Append would exceed 50 total → skip excess in order.

**Import `errors[].detail` codes**: `invalid youtube reference`, `duplicate in file`, `duplicate in batch`.

Participant → **401** on all three endpoints.

### Filler reserve playlist (019)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/filler-reserve/playlist/validate` | operator | 200 `FillerReserveBatchValidation` |
| POST | `/api/filler-reserve/playlist` | operator | 200 `FillerReserveListResponse` or 422 |

**Request body** (`application/json`): `{ "youtube_playlist_url": "https://www.youtube.com/playlist?list=PL..." }`

**Accepted URL formats**: playlist URLs with `list=PL…`; single video URLs (`watch?v=`, `youtu.be/`, `shorts/`) without playlist → batch of 1 video.

**Behavior**: parse playlist id (or single video); fetch ordered video ids via YouTube `playlistItems.list` (paginated, max 500 items); run same batch validation as CSV import (`line` = 1-based playlist index). Validate: no DB writes. Commit: re-validate → append addable entries.

| Case | Status | Notes |
|------|--------|-------|
| Playlist unavailable | 422 | `detail: playlist unavailable` |
| Playlist empty | 422 | `detail: playlist empty` |
| Playlist >500 items | 422 | `detail: playlist too large` |
| Zero addable after skips | 422 | `can_confirm: false`, `add_count: 0` |
| Success commit | 200 | Full reserve list |

Participant → **401**.

### Auto-inject (changed 020)

When `filler_auto_inject_enabled` and **zero** `queued` entries (regardless of whether `playing` exists):

1. Evaluate reserve in position order.
2. If candidate `youtube_video_id` is in active queue (`pending_review`, `queued`, `playing`) → **remove** that reserve row (no enqueue), continue with next position.
3. Otherwise transfer first valid candidate to queue as `queued`, `priority=low`, `source=auto_inject` (consume from reserve).
4. At most **one** successful inject per evaluation call.
5. Single `bump_revision` + SSE `state` per evaluation when reserve or queue changed (including duplicate-only removals with no inject).

**Idle path** (no `playing`, no `queued`): inject then auto-start top `queued` per 014 (`_maybe_auto_start_playback` / `skip_or_advance`).

**Playing + empty queued**: inject only; do **not** interrupt `now_playing`.

**Triggers** (explicit mutations only; state GET does not inject):

- Queue lifecycle: `skip_or_advance`, `_maybe_auto_start_playback` when promotion leaves `playing` + 0 `queued`
- Reserve mutations (that do not enqueue): `add_to_reserve`, import/playlist commit, `reorder_reserve` (after persist)
- Config: `filler_auto_inject_enabled` set to `true` when previously `false`

**Not triggers**: `GET /api/state`; `reject_entry` (only `pending_review`); `transfer_to_queue` / manual reserve enqueue (adds to `queued` directly).

Toggle: `PUT /api/event-config/filler-auto-inject`.

### YouTube search (changed)

`GET /api/youtube/search`: operator session bypasses participant rate limit.

### Tests

- `backend/tests/test_queue_history.py`
- `backend/tests/test_filler_reserve.py`
- Extended `test_queue.py`, `test_state.py`, `test_votes.py`

## Auth-token lookup (010)

`api_tokens` has an indexed non-secret `token_prefix` (first 8 chars of the plaintext). Token exchange locates the candidate by prefix then verifies a single bcrypt hash (no full-table scan). Tokens created before 010 have a NULL prefix, no longer validate, and must be regenerated.

## Referential integrity (010)

`queue_entries.submitted_by_participant_id` is a foreign key to `participants.id` (`ON DELETE SET NULL`); migration `0008` nulls orphan references before adding it.

## Concurrency / scaling (010)

SSE fan-out, the search rate limiter (with idle-bucket eviction), YouTube key rotation, and per-key quota counters are in-process. The backend runs with a single replica (see ops-platform); outbound HTTP runs in synchronous FastAPI path operations (threadpool), so the async event loop is not blocked.

## Configuration

| Variable | Purpose |
|----------|---------|
| `JUKEBOX_DATABASE_URL` | SQLAlchemy URL |
| `JUKEBOX_CORS_ALLOW_ORIGINS` | Comma-separated CORS origins |
| `JUKEBOX_OPERATOR_USERNAME` | Operator login |
| `JUKEBOX_OPERATOR_PASSWORD` | Operator password (≥12 chars) |
| `JUKEBOX_SESSION_SECRET` | Session signing key |
| `JUKEBOX_COOKIE_SECURE` | Secure cookie flag |
| `JUKEBOX_FRAME_ANCESTORS` | CSP frame-ancestors |
| `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT` | Enable `POST /api/queue/dev-submit` (default false) |
| `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` | Enable `POST /api/participant/dev-auth` (default false) |
| `JUKEBOX_GOOGLE_CLIENT_ID` | Google OAuth client id (required in prod) |
| `JUKEBOX_GOOGLE_CLIENT_SECRET` | Google OAuth client secret (required in prod) |
| `JUKEBOX_GOOGLE_REDIRECT_URI` | OAuth callback URL registered in Google console |
| `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` | Frontend redirect after OAuth (default `/participar`) |
| `JUKEBOX_YOUTUBE_API_KEYS` | Comma-separated YouTube Data API keys (empty disables search UI) |
| `JUKEBOX_YOUTUBE_SEARCH_MAX_RESULTS` | Max results per search (default 10) |
| `JUKEBOX_YOUTUBE_SEARCH_MIN_QUERY_LENGTH` | Min query length after trim (default 2) |
| `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` | Max submissions per participant per mode: counts `pending_review` in **moderated**, `queued` in **free** (default 2, min 1) |
| `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT` | Max YouTube searches per participant per 10-minute rolling window (default 10, min 1) |
| `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT` | Max votes per participant per 10-minute rolling window (default 2, min 1) |

## Error shape

FastAPI default: `{"detail": "..."}` or validation array for 422.

## Tests

- `backend/tests/test_health.py` — health + CSP header
- `backend/tests/test_bootstrap.py` — operator and event_config bootstrap idempotency
- `backend/tests/test_auth.py` — login, logout, me, token exchange
- `backend/tests/test_tokens.py` — token CRUD
- `backend/tests/test_auth_policy.py` — canonical public route list
- `backend/tests/test_state.py` — state snapshot
- `backend/tests/test_queue.py` — moderation and skip/start
- `backend/tests/test_sse.py` — SSE registration and revision
- `backend/tests/test_participant_auth.py` — dev participant session
- `backend/tests/test_votes.py` — vote limits, reorder, invalid targets
- `backend/tests/test_oauth_google.py` — Google OAuth login/callback
- `backend/tests/test_participant_submit.py` — participant submit limits
- `backend/tests/test_participant_submissions.py` — submissions list
- `backend/tests/test_notifications.py` — SSE notification emit and targeting
- `backend/tests/test_youtube_search.py` — search config, auth, rate limits, key pool failover
- `backend/tests/test_youtube_api_key_usage.py` — per-key usage, SSE `api_key_usage`, auth, persistence
- `backend/tests/test_queue_approval_mode.py` — queue mode moderated/free, mode switch, caps, duplicates
- `backend/tests/test_admin_stats.py` — admin stats aggregates, rankings, queue counts, auth, post-clear-history

## Change history

- **001-foundation-jukebox** — health API, bootstrap, Alembic 0001, pytest suite
- **002-operator-auth-embed-tokens** — operator auth, embed tokens, Alembic 0002
- **004-kiosk-display-queue** — queue, state, SSE, moderation, Alembic 0003
- **005-participant-voting** — participant session, votes, `/participar` API, Alembic 0004
- **006-participant-oauth-submit** — Google OAuth, participant submit, Mis canciones, Alembic 0005
- **007-participant-notifications** — SSE `notification` events, `notification_service`, no migration
- **008-youtube-text-search** — YouTube text search API, multi-key pool, dual-path `/participar` submit UX
- **009-admin-api-key-usage** — per-key YouTube API daily usage tracking, `GET /api/youtube/api-keys/usage`, SSE `api_key_usage`
- **010-hardening-and-polish** — server-side SSE audience routing; `GET`/`PUT /api/event-config`; token prefix lookup (Alembic 0007); submitter FK (Alembic 0008); rate-limiter eviction; deterministic quota reset-on-read; unified submit metadata validation; CORS `allow_headers` scoping; single-replica documentation
- **013-queue-approval-mode** — `event_config.queue_mode` (Alembic 0009); `PUT /api/event-config/queue-mode`; free-mode direct enqueue + `song.approved` on submit; moderated regression unchanged
- **017-admin-queue-history-filler** — queue history + requeue; filler reserve CRUD/reorder/enqueue; operator direct enqueue; priority tie-break ordering; auto-inject on idle; Alembic 0010; `GET/POST /api/queue/history/*`, `/api/filler-reserve/*`, `POST /api/queue/operator-submit`, `PUT /api/event-config/filler-auto-inject`
- **018-filler-reserve-csv** — filler reserve CSV export/import (validate → confirm → atomic replace); `GET /api/filler-reserve/export`, `POST /api/filler-reserve/import/validate`, `POST /api/filler-reserve/import`; no migration
- **019-filler-reserve-playlist** — CSV import append (not replace); playlist validate/commit; `DELETE /api/filler-reserve` clear; `FillerReserveBatchValidation` with `skipped_*` counts; no migration
- **020-fill-queue-from-reserve** — auto-inject when `queued` empty even while `playing`; skip/remove active duplicates from reserve; event-driven triggers including toggle-on; no migration
- **021-collapsible-panels-reset** — collapsible Admin/participant panels; participate reorder; `DELETE /api/queue/history` clear terminal history; no migration
- **023-admin-stats-panel** — `GET /api/admin/stats`; participation totals, queue status counts, top-10 submitters/voters/songs; no migration
- **024-admin-queue-control** — `GET/DELETE /api/queue/active`, `play-now`, `vote-count`, delete active entry; hard delete on vaciar/eliminar; no migration
