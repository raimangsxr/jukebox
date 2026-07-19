# backend-api Contract

Status: active. Consolidated from changes **001-foundation-jukebox**, **002-operator-auth-embed-tokens**, **004-kiosk-display-queue**, **005-participant-voting**, **006-participant-oauth-submit**, **007-participant-notifications**, **008-youtube-text-search**, **009-admin-api-key-usage** (2026-07-19).

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

**Also on the same stream** (`event: notification`, payload `NotificationEventRead`; `event: api_key_usage`, payload `ApiKeyUsageListResponse`):

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

Server broadcasts to all SSE subscribers; kiosk/operator clients ignore `notification` events. `/participar` filters by `participant_id` before showing a toast.

No `notification` on reject, vote reorder, or entries without `submitted_by_participant_id`.

`GET /api/participant/state` returns `ParticipantStateResponse` (all `queued` entries, `votes_remaining`, `max_pending_submissions`). SSE does not include `votes_remaining` or `max_pending_submissions`; clients merge per participant state snapshot.

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
| POST | `/api/queue/dev-submit` | session (if enabled) | 201 `QueueEntryRead` |
| POST | `/api/queue/submit` | participant | 201 `QueueEntryRead` |

`POST /api/queue/submit` body: `{ "youtube_url_or_id": string, "search_query"?: string }`. Creates `pending_review` with `submitted_by_participant_id`; bumps `revision`. When `search_query` is non-empty after trim, `original_query` = `search:{search_query}`; otherwise stores URL/id string (006).

`PendingListResponse.entries[]` uses `PendingQueueEntryRead`: `QueueEntryRead` plus `submitted_by_display_name` (participant display name when linked). `QueueEntryRead.duration_sec` is populated on submit via YouTube Data API when `JUKEBOX_YOUTUBE_API_KEYS` is configured; otherwise `null`.

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
| Rate limit (10 / 5 min) | 429 | `search rate limit exceeded` |
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

### Participant submit errors (006)

API returns stable English `detail` strings; frontend maps to Spanish.

| Case | Status | `detail` |
|------|--------|----------|
| Pending limit | 429 | `pending submission limit reached` |
| Duplicate active video | 409 | `video already in queue` |
| Invalid YouTube / metadata failure | 422 | `invalid youtube reference` |
| Not authenticated | 401 | `not authenticated` |

Participants may submit while they already have songs in `queued` or `playing`; only the pending limit and duplicate-video rules apply.

`JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` (default `2`, min `1`) controls the per-participant `pending_review` cap. `GET /api/participant/state` exposes `max_pending_submissions` for client UX.

`POST /api/queue/skip`: advance when `playing`; start when idle + `queued`; 409 `nothing to advance` when empty.

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

`backend/tests/test_auth_policy.py` asserts the canonical public route list.

## Health

- `GET /api/health` returns `200` + `{"status": "ok"}` without authentication.

## Security headers

- Every response includes `Content-Security-Policy: frame-ancestors <JUKEBOX_FRAME_ANCESTORS>` (default `'none'`).

## Bootstrap (lifespan)

On application startup:

1. `ensure_operator` — creates operator user from `JUKEBOX_OPERATOR_USERNAME` / `JUKEBOX_OPERATOR_PASSWORD` if missing (password ≥ 12 chars).
2. `ensure_event_config` — creates singleton `event_config` row (`id=1`) with defaults if missing.
3. `ensure_jukebox_runtime` — creates singleton `jukebox_runtime` row (`id=1`) if missing.

All helpers are idempotent.

## CORS

When `JUKEBOX_CORS_ALLOW_ORIGINS` is non-empty, credentials are allowed for listed origins.

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

## Planned (007+)

- `GET` / `PUT /api/event-config`

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
| `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` | Max `pending_review` submissions per participant (default 2, min 1) |

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

## Change history

- **001-foundation-jukebox** — health API, bootstrap, Alembic 0001, pytest suite
- **002-operator-auth-embed-tokens** — operator auth, embed tokens, Alembic 0002
- **004-kiosk-display-queue** — queue, state, SSE, moderation, Alembic 0003
- **005-participant-voting** — participant session, votes, `/participar` API, Alembic 0004
- **006-participant-oauth-submit** — Google OAuth, participant submit, Mis canciones, Alembic 0005
- **007-participant-notifications** — SSE `notification` events, `notification_service`, no migration
- **008-youtube-text-search** — YouTube text search API, multi-key pool, dual-path `/participar` submit UX
- **009-admin-api-key-usage** — per-key YouTube API daily usage tracking, `GET /api/youtube/api-keys/usage`, SSE `api_key_usage`
