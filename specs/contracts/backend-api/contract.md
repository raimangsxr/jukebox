# backend-api Contract

Status: active. Consolidated from changes **001-foundation-jukebox**, **002-operator-auth-embed-tokens** (2026-07-17).

## Purpose

FastAPI + Alembic + PostgreSQL service for amrn-jukebox. Owns persistent event configuration, operator authentication, embed tokens, participant identity (planned), queue state (planned), voting, moderation, and SSE realtime. The Angular SPA is served by a separate `frontend` image in production; every backend route lives under `/api/*`.

## Stack

- Python ≥ 3.11, FastAPI, SQLAlchemy 2.x, Alembic, psycopg 3
- Settings: flat `JUKEBOX_` env prefix via pydantic-settings
- Session cookie: `jukebox_session` (operator)
- Participant cookie (planned): `jukebox_participant_session`

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

### Error shapes

| Case | Status | Body |
|------|--------|------|
| Invalid login | 401 | `{"detail":"invalid credentials"}` |
| Missing session | 401 | `{"detail":"not authenticated"}` |
| Invalid/revoked embed token | 401 | `{"detail":"invalid or revoked token"}` |
| Token not found | 404 | `{"detail":"token not found"}` |
| Malformed body | 422 | FastAPI validation error |

### Session

- `request.session["user_id"]` → `users.id`
- Dependency `get_current_user` → 401 if missing/invalid

### Public vs protected (002)

| Public | Protected |
|--------|-----------|
| `GET /api/health` | `GET /api/auth/me` |
| `POST /api/auth/login` | `GET/POST/DELETE /api/tokens` |
| `POST /api/auth/token` | Future business endpoints (003+) |

### Future protected routes policy

Endpoints added in changes 003+ (queue, SSE, event-config writes, moderation) MUST use `get_current_user` unless explicitly documented public. `backend/tests/test_auth_policy.py` asserts the canonical public route list for this change.

## Health

- `GET /api/health` returns `200` + `{"status": "ok"}` without authentication.

## Security headers

- Every response includes `Content-Security-Policy: frame-ancestors <JUKEBOX_FRAME_ANCESTORS>` (default `'none'`).

## Bootstrap (lifespan)

On application startup:

1. `ensure_operator` — creates operator user from `JUKEBOX_OPERATOR_USERNAME` / `JUKEBOX_OPERATOR_PASSWORD` if missing (password ≥ 12 chars).
2. `ensure_event_config` — creates singleton `event_config` row (`id=1`) with defaults if missing.

Both helpers are idempotent.

## CORS

When `JUKEBOX_CORS_ALLOW_ORIGINS` is non-empty, credentials are allowed for listed origins.

## Persistence

### Alembic 0001

Tables: `users`, `event_config` (includes `queue_visible_count` default 8).

### Alembic 0002

Table: `api_tokens` — `id` (uuid PK), `user_id` FK → users, `label`, `token_hash` (bcrypt, unique), `created_at`, `last_used_at`, `revoked_at`.

## Planned (003+)

- Participant Google OAuth
- `GET /api/state`, SSE streams
- Queue submit, vote, admin moderation
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

## Error shape

FastAPI default: `{"detail": "..."}` or validation array for 422.

## Tests

- `backend/tests/test_health.py` — health + CSP header
- `backend/tests/test_bootstrap.py` — operator and event_config bootstrap idempotency
- `backend/tests/test_auth.py` — login, logout, me, token exchange
- `backend/tests/test_tokens.py` — token CRUD
- `backend/tests/test_auth_policy.py` — canonical public route list

## Change history

- **001-foundation-jukebox** — health API, bootstrap, Alembic 0001, pytest suite
- **002-operator-auth-embed-tokens** — operator auth, embed tokens, Alembic 0002
