# Implementation Plan: Operator Auth and Embed Tokens

**Branch**: `002-operator-auth-embed-tokens` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/002-operator-auth-embed-tokens/spec.md`

## Summary

Add operator session login, embed token CRUD, and Angular auth layer so `/admin` is password-protected and `/` (display) authenticates via `?token=` embed exchange or existing session. **Kiosk-safe display UX**: failed token exchange or expired session on `/` shows a static Spanish error — never redirects to `/login`. Port proven patterns from amrn-bull `003-auth-and-tokens`; tokens UI lives in `/admin`.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, passlib/bcrypt, Starlette SessionMiddleware; Angular standalone, RxJS, TailwindCSS

**Storage**: PostgreSQL — new `api_tokens` table; existing `users` unchanged

**Testing**: pytest (backend `test_auth.py`, `test_tokens.py`); `npm run build` (frontend)

**Target Platform**: Docker Compose / Linux server; kiosk iframe via kiosk-screen

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Login + token exchange &lt; 500 ms p95 on local network; single operator, handful of embed tokens

**Constraints**: Cookie `jukebox_session` (HttpOnly, SameSite=Lax); CSP `frame-ancestors` from 001; Spanish UI strings; no rate limiting in this change

**Scale/Scope**: Single operator per deployment; 7 auth endpoints; 4 guarded Angular routes (`/login`, `/admin`, `/`, `/participar` public)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` into `specs/contracts/**/contract.md` at implement start (T001–T002); auth policy test T008 |
| IV. Contract updates before implementation | Pass | Deltas drafted; consolidation required before code |
| V. Tests for changed behavior | Pass | `test_auth.py`, `test_tokens.py` + manual quickstart scenarios |
| VI. Sibling conventions | Pass | Mirror bull `/api/auth/*`, `?token=` param, `jukebox_session`; **display error UX diverges from bull** (kiosk requirement) |

**Post-design re-check**: All gates pass. No constitution violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/changes/002-operator-auth-embed-tokens/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/contract-deltas.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py              # mount auth + tokens routers
│   ├── models.py            # + ApiToken
│   ├── schemas.py           # auth + token Pydantic models
│   ├── security.py          # get_current_user, token hash/verify
│   └── routers/
│       ├── auth.py
│       └── tokens.py
├── alembic/versions/
│   └── 0002_api_tokens.py
└── tests/
    ├── conftest.py
    ├── test_auth.py
    └── test_tokens.py

frontend/src/app/
├── services/auth.service.ts
├── auth.guard.ts            # authGuard + displayGuard
├── auth.interceptor.ts
├── login/login.component.ts
├── admin/admin.component.ts
└── display/display.component.ts   # error state UI
```

**Structure Decision**: Monorepo `backend/` + `frontend/` per 001 foundation and sibling apps.

## Phase 0 — Research

See [research.md](./research.md). All NEEDS CLARIFICATION resolved (including kiosk display error states from clarify session 2026-07-17).

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |

### Backend design

1. **`security.py`**: `CurrentUser`, `get_current_user` (401 `not authenticated`), `generate_token`, `hash_token`, `verify_token`, `find_active_token`
2. **`routers/auth.py`**: `POST /login`, `POST /logout`, `GET /me`, `POST /token` (public exchange)
3. **`routers/tokens.py`**: `GET`, `POST`, `DELETE /{id}` — all require session
4. **Migration `0002_api_tokens`**: table per data-model

### Frontend design

1. **`AuthService`**: bootstrap strips `?token=`, exchanges or calls `/me`; expose `displayError: 'token_invalid' | 'session_expired' | null` for kiosk UX
2. **`displayGuard`** (route `/`, US1 stub → US2 full): US1 — unauthenticated without session → `/login`; US2 — add embed bootstrap, allow `displayError` state, token exchange failure UI
3. **`authGuard`** (`/admin`): standard — unauthenticated → `/login?returnUrl=…`
4. **`guestGuard`** (`/login`): authed → `/admin`
5. **`authInterceptor`**: `withCredentials: true`; on 401 — if current route is `/`, set `displayError = 'session_expired'` and **do not** navigate to `/login`; else logout + `/login`
6. **`DisplayComponent`**: placeholder + static error panel when `displayError` non-null (Spanish copy)
7. **`AdminComponent`**: tokens CRUD panel (US3) + **logout button (US1)**

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts

Merge contract deltas into active `backend-api` and `app-core` contracts.

### Phase B — Backend

Models, security, routers, migration, tests.

### Phase C — Frontend auth core

AuthService, guards, interceptor, routes, AppComponent bootstrap.

### Phase D — Frontend UI

Login form (US1), admin logout (US1), tokens panel (US3), display error states (US2).

### Phase E — Validation

pytest, build, quickstart manual paths; CSP header assertions in `test_health.py` (existing + custom ancestors case).

## Risks

| Risk | Mitigation |
|------|------------|
| Bull interceptor always redirects 401 → `/login` | Jukebox interceptor checks `Router.url` or `displayError` path for `/` |
| Token in URL leaks via Referer | Document revoke policy in admin; strip param after exchange |
| CORS + cookies in dev | `allow_credentials=True` + interceptor `withCredentials` |
| `guestGuard` redirect target | Clarified: `/admin` (not `/`) |

## Complexity Tracking

> No violations.
