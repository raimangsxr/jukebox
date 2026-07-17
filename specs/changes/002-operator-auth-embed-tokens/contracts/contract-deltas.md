# Contract Deltas: 002-operator-auth-embed-tokens

**Status**: implemented — merged into active contracts

## backend-api

### New endpoints

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/auth/login` | public | 200 `MeResponse` + Set-Cookie |
| POST | `/api/auth/logout` | session | 204 |
| GET | `/api/auth/me` | session | 200 `MeResponse` |
| POST | `/api/auth/token` | public | 200 `MeResponse` + Set-Cookie |
| GET | `/api/tokens` | session | 200 `TokenListResponse` |
| POST | `/api/tokens` | session | 201 `TokenCreateResponse` (plaintext once) |
| DELETE | `/api/tokens/{id}` | session | 204 |

### Error shapes

| Case | Status | Body |
|------|--------|------|
| Invalid login | 401 | `{"detail":"invalid credentials"}` |
| Missing session | 401 | `{"detail":"not authenticated"}` |
| Invalid/revoked embed token | 401 | `{"detail":"invalid or revoked token"}` |
| Malformed body | 422 | FastAPI validation error |

### New persistence

- Table `api_tokens` (see `data-model.md`)

### Session

- `request.session["user_id"]` → `users.id`
- Dependency `get_current_user` → 401 if missing/invalid

### Public vs protected (after 002)

| Public | Protected |
|--------|-----------|
| `GET /api/health` | `GET /api/auth/me` |
| `POST /api/auth/login` | `GET/POST/DELETE /api/tokens` |
| `POST /api/auth/token` | Future business endpoints |

### Future protected routes policy

Endpoints added in changes 003+ (queue, SSE, event-config writes, moderation) MUST use `get_current_user` unless explicitly documented public. `backend/tests/test_auth_policy.py` asserts the canonical public route list for this change and fails if a new router is mounted without updating the policy doc in this contract.

## app-core

### New services

- `AuthService` — bootstrap with `?token=`, login, logout, me; `displayError` state for kiosk
- `authInterceptor` — credentials + route-aware 401 handling
- `authGuard`, `displayGuard`, `guestGuard`

### Route guards

| Path | Guard | Notes |
|------|-------|-------|
| `/login` | `guestGuard` | Authed → `/admin` |
| `/admin` | `authGuard` | Unauthed → `/login` |
| `/` | `displayGuard` | Kiosk errors on-route; unauthed direct visit → `/login` |
| `/participar` | none | Public |

### Display error states (kiosk)

| Trigger | UI on `/` | Redirect `/login` |
|---------|-----------|-------------------|
| Invalid/revoked `?token=` | `"Token inválido o revocado"` | No |
| 401 on protected API while on `/` | `"Sesión caducada"` | No |
| Unauthenticated, no `?token=` | — | Yes |

### Admin UI

- Tokens section: list, create (label), revoke, copy-once plaintext panel
- Logout button

### Bootstrap

`AppComponent` calls `AuthService.bootstrap()` on init (before future iframe services).

### Interceptor 401 behavior

| Current route | Action |
|---------------|--------|
| `/` (display) | Set `displayError = 'session_expired'`; no navigation |
| Other routes | `logout()` + navigate `/login` |
| Exempt URLs | `/api/auth/login`, `/api/auth/me`, `/api/auth/token` (no redirect loop) |
