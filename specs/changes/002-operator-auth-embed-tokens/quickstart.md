# Quickstart: 002-operator-auth-embed-tokens

Validation after implementation.

## Prerequisites

- Change 001 applied (`docker compose` or local backend + frontend)
- `.env` with `JUKEBOX_OPERATOR_USERNAME` / `JUKEBOX_OPERATOR_PASSWORD` (≥12 chars)

## Phase 1 — Backend API (curl)

```bash
# Login
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"op","password":"change-me-please-1234"}'

# Me
curl -b cookies.txt http://localhost:8000/api/auth/me

# Create token
curl -b cookies.txt -X POST http://localhost:8000/api/tokens \
  -H 'Content-Type: application/json' \
  -d '{"label":"Kiosk sala"}'
# Save plaintext "token" field from response

# Exchange token (fresh cookie jar)
curl -c cookies2.txt -X POST http://localhost:8000/api/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"token":"<plaintext>"}'

# Revoke
curl -b cookies.txt -X DELETE http://localhost:8000/api/tokens/<id>

# Invalid token exchange → 401
curl -X POST http://localhost:8000/api/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"token":"invalid-token"}'
```

## Phase 2 — Angular manual

1. Open `http://localhost:4200/login` → login → lands on `/admin`
2. Create embed token → copy plaintext
3. Private window: `http://localhost:4200/?token=<plaintext>` → lands on `/` (display), URL param stripped
4. Private window: `http://localhost:4200/?token=bad-token` → stays on `/`, shows **"Token inválido o revocado"**, no `/login`
5. Private window: `/participar` loads **without** login
6. Direct visit `http://localhost:4200/` (no token, no session) → redirects to `/login`
7. Logout from admin → `/login` required again for `/admin`

## Phase 3 — Session expiry on display (manual)

1. Authenticate display via valid `?token=`
2. Clear session cookie in devtools (or rotate `JUKEBOX_SESSION_SECRET` and reload)
3. Trigger a protected API call from display (or reload after cookie cleared and call `/me`)
4. Expect **"Sesión caducada"** on `/` — **not** `/login`

## Phase 4 — Automated

```bash
pytest backend/tests/test_auth.py backend/tests/test_tokens.py
npm --prefix frontend run build
```

## Phase 5 — Embed CSP

Automated: `pytest backend/tests/test_health.py::test_health_returns_csp_header` (default `'none'`).

Optional manual: set `JUKEBOX_FRAME_ANCESTORS` to kiosk origin; verify iframe loads when parent allowed.
