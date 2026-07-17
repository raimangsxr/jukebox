---
description: "Task list for 002-operator-auth-embed-tokens"
---

# Tasks: Operator Auth and Embed Tokens

**Input**: Design documents from `specs/changes/002-operator-auth-embed-tokens/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: Included — spec SC-004 requires `test_auth.py` and `test_tokens.py`.

**Organization**: Tasks grouped by user story (US1, US2, US3) for independent implementation and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Contract Consolidation)

**Purpose**: Merge contract deltas before code (Constitution IV)

- [x] T001 Update `specs/contracts/backend-api/contract.md` from `specs/changes/002-operator-auth-embed-tokens/contracts/contract-deltas.md` (include future-route auth policy section)
- [x] T002 Update `specs/contracts/app-core/contract.md` from `specs/changes/002-operator-auth-embed-tokens/contracts/contract-deltas.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend models, security, test fixtures, and auth policy scaffold

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Add `ApiToken` model to `backend/app/models.py` per `data-model.md`
- [x] T004 [P] Add auth and token Pydantic schemas to `backend/app/schemas.py`
- [x] T005 Extend `backend/app/security.py` with `CurrentUser`, `get_current_user`, `generate_token`, `hash_token`, `verify_token`, `find_active_token`
- [x] T006 Create Alembic migration `backend/alembic/versions/0002_api_tokens.py`
- [x] T007 Extend `backend/tests/conftest.py` with `operator_credentials`, `authed_client`, and `embed_token` fixture (inserts hashed `api_tokens` row via DB helper — no US3 API required)
- [x] T008 Add `backend/tests/test_auth_policy.py` asserting canonical public routes (`/api/health`, `/api/auth/login`, `/api/auth/token`) per contract future-route policy

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — Operator Login (Priority: P1) 🎯 MVP

**Goal**: Moderator logs in at `/login` with username/password, reaches `/admin` with persistent session, and can logout from admin UI. `/` has baseline `displayGuard` (unauthed → `/login`).

**Independent Test**: `POST /api/auth/login` → 200 + Set-Cookie; `GET /api/auth/me` → user; invalid creds → 401; Angular login → `/admin`; logout clears session.

### Tests for User Story 1

- [x] T009 [US1] Add `backend/tests/test_auth.py` covering login, logout, me, and invalid credentials *(expected to fail until T010–T011 land)*

### Implementation for User Story 1

- [x] T010 [US1] Create `backend/app/routers/auth.py` with `POST /login`, `POST /logout`, `GET /me`
- [x] T011 [US1] Mount auth router in `backend/app/main.py`
- [x] T012 [P] [US1] Create `frontend/src/app/services/auth.service.ts` with login, logout, me, and bootstrap shell
- [x] T013 [P] [US1] Create `frontend/src/app/auth.interceptor.ts` with `withCredentials` and 401 → logout + `/login` (non-display routes)
- [x] T014 [US1] Create `frontend/src/app/auth.guard.ts` with `authGuard`, `guestGuard` (authed `/login` → `/admin`), and `displayGuard` stub (unauthed `/` → `/login`)
- [x] T015 [US1] Wire `frontend/src/app/app.config.ts`, `frontend/src/app/app.routes.ts`, `frontend/src/app/app.component.ts` (guards on `/login`, `/admin`, `/`; `/participar` unguarded)
- [x] T016 [US1] Implement login form in `frontend/src/app/login/login.component.ts` (Spanish errors, redirect `/admin` or safe `returnUrl`)
- [x] T017 [US1] Add logout control to `frontend/src/app/admin/admin.component.ts` (calls `AuthService.logout`, redirects `/login`)
- [x] T018 [US1] Run `pytest backend/tests/test_auth.py` and fix failures

**Checkpoint**: Operator login/logout via UI and API; `/admin` and baseline `/` guarded

---

## Phase 4: User Story 2 — Kiosk Iframe via Embed Token (Priority: P1)

**Goal**: Display loads at `/?token=<plaintext>` without login form; invalid/revoked token and expired session show static Spanish errors on `/` (no `/login` redirect).

**Independent Test**: Seed token via `embed_token` fixture or `POST /api/tokens` (curl) → `POST /api/auth/token` succeeds; revoked → 401; `/?token=bad` shows "Token inválido o revocado".

### Tests for User Story 2

- [x] T019 [US2] Extend `backend/tests/test_auth.py` with token exchange (valid, invalid, revoked) using `embed_token` fixture

### Implementation for User Story 2

- [x] T020 [US2] Add `POST /api/auth/token` to `backend/app/routers/auth.py`
- [x] T021 [US2] Extend `frontend/src/app/services/auth.service.ts` with `?token=` bootstrap, URL param strip, and `displayError` state (`token_invalid` | `session_expired`)
- [x] T022 [US2] Extend `displayGuard` in `frontend/src/app/auth.guard.ts` (allow authenticated or `displayError`; embed bootstrap via `AuthService.bootstrap()`)
- [x] T023 [US2] Update `frontend/src/app/auth.interceptor.ts` to set `session_expired` on 401 when route is `/` (no `/login` navigation)
- [x] T024 [P] [US2] Add static error panel to `frontend/src/app/display/display.component.ts` (Spanish: token invalid, session expired)

**Checkpoint**: Kiosk embed path works; display never shows operator login on auth failure

---

## Phase 5: User Story 3 — Manage Embed Tokens in Admin (Priority: P2)

**Goal**: Moderator creates, lists, and revokes embed tokens from `/admin`; plaintext shown once at creation.

**Independent Test**: `POST /api/tokens` → plaintext once; `GET /api/tokens` omits secret; `DELETE` revokes; admin UI mirrors API.

### Tests for User Story 3

- [x] T025 [US3] Add `backend/tests/test_tokens.py` covering list, create, revoke, and auth-required cases

### Implementation for User Story 3

- [x] T026 [US3] Create `backend/app/routers/tokens.py` with `GET`, `POST`, `DELETE /{id}`
- [x] T027 [US3] Mount tokens router in `backend/app/main.py`
- [x] T028 [US3] Implement tokens panel in `frontend/src/app/admin/admin.component.ts` (list, create with label, revoke, copy-once plaintext)
- [x] T029 [US3] Run `pytest backend/tests/test_tokens.py` and fix failures

**Checkpoint**: Full operator workflow — login, provision kiosk token via admin UI, revoke

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, CSP, build, and change closure

- [x] T030 Run full `pytest backend/tests` including `test_health.py` CSP assertions and `test_auth_policy.py` with zero failures; add `test_health_custom_frame_ancestors` if custom `JUKEBOX_FRAME_ANCESTORS` not yet covered
- [x] T031 Run `npm --prefix frontend run build` with zero errors
- [x] T032 Execute manual validation per `specs/changes/002-operator-auth-embed-tokens/quickstart.md` (login, valid token, invalid token, session expiry on `/`, public `/participar`, SC-001 smoke)
- [x] T033 Mark change `implemented` in `specs/manifest.yml`
- [x] T034 Update implementation validation in `specs/changes/002-operator-auth-embed-tokens/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — MVP target; includes baseline `/` guard and admin logout
- **Phase 4 (US2)**: Depends on Phase 2 + US1 `displayGuard` stub; token seed via T007 fixture (no US3 UI required)
- **Phase 5 (US3)**: Depends on Phase 2 + US1 session auth
- **Phase 6 (Polish)**: Depends on US1–US3 completion

### User Story Dependencies

| Story | Depends on | Independent test without other stories |
|-------|------------|----------------------------------------|
| US1 | Foundational | Yes — login/logout/me via API + UI; `/` redirects unauthed to `/login` |
| US2 | Foundational + US1 displayGuard stub | Yes — `embed_token` fixture + API exchange + display error UI |
| US3 | Foundational + US1 session | Yes — tokens API + admin panel (logout already in US1) |

### Parallel Opportunities

- **Phase 1**: T001 and T002 — different contract files
- **Phase 2**: T004 parallel with T003
- **Phase 3**: T012 and T013 parallel; T016 and T017 parallel after T015
- **Phase 4**: T024 parallel with T022–T023 after T021
- **Phase 5**: T025 parallel with T026 once router shape known

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1–2 (T001–T008)
2. Complete Phase 3 (T009–T018)
3. **STOP and VALIDATE**: Operator login/logout; `/admin` and `/` baseline guarded
4. Demo secured admin

### Suggested MVP Scope

**T001–T018** (Setup + Foundational + US1).

---

## Notes

- Reference: `amrn-bull` `003-auth-and-tokens` (display error UX diverges on `/`)
- Token query param: `token` (strip after exchange)
- Spanish UI strings throughout
- `/participar` stays public (no operator guard)
