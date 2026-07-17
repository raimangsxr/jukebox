---
id: 002-operator-auth-embed-tokens
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Operator Auth and Embed Tokens

**Feature Branch**: `002-operator-auth-embed-tokens`

**Created**: 2026-07-17

**Status**: Implemented

**Input**: Add session-based operator login and revocable embed tokens so the kiosk display can load the jukebox iframe without a login form, following the amrn-bull `003-auth-and-tokens` pattern. Participant Google OAuth on `/participar` remains out of scope.

## Clarifications

### Session 2026-07-17

- Q: ¿Nombre del query param del embed token? → A: `token` (mismo que amrn-bull / kiosk-screen).
- Q: ¿Ruta de gestión de tokens? → A: Panel dentro de `/admin`, sin `/tokens` separado.
- Q: ¿Tras login operador, destino por defecto? → A: `/admin` (no `/`).
- Q: ¿`guestGuard` en `/login` redirige a dónde si ya hay sesión? → A: `/admin`.
- Q: ¿El embed token otorga los mismos permisos que login operador? → A: Sí (sesión `jukebox_session` idéntica); el display iframe usa la misma sesión para futuros endpoints protegidos.
- Q: ¿Proteger algún endpoint más allá de tokens en este change? → A: Solo `/api/tokens/*` requiere auth nuevo; no hay otros endpoints de negocio aún. Añadir `GET /api/auth/me` protegido y tests de contrato para rutas futuras documentadas como "auth required when added".
- Q: ¿Comportamiento en `/` cuando falla el intercambio del embed token (revocado/inválido)? → A: Permanecer en `/` y mostrar mensaje de error estático (sin redirigir a `/login` ni formulario de operador).
- Q: ¿Comportamiento en `/` cuando caduca la sesión de operador (401 en iframe kiosk)? → A: Mostrar mensaje de error estático en `/` (p. ej. sesión caducada); sin redirigir a `/login`.

## SDD Context

- Depends on: **001-foundation-jukebox** (`users` table, bootstrap, `jukebox_session` middleware shell, placeholder routes)
- Modifies contracts: `backend-api`, `app-core`
- Reference implementation: `amrn-bull` change `003-auth-and-tokens`
- Product constraint (from 001 clarifications): operator auth is **only** username/password at `/login` → `/admin`; public OAuth is a later change

## Problem

After foundation, every API route beyond health is still unauthenticated and the Angular routes have no guards. Anyone who reaches the backend could call future protected endpoints. The kiosk display must embed `/` in an iframe without showing the operator login, while moderators must authenticate separately to reach `/admin`.

## Goals

- Session-based login for a **single operator** per deployment (`POST /api/auth/login`).
- Revocable **embed tokens** created from `/admin`; plaintext shown once at creation.
- Iframe entry: SPA loads with `?token=<plaintext>`, exchanges via `POST /api/auth/token`, strips query param, keeps session via `jukebox_session` cookie.
- Protect operator-only surfaces; allow display bootstrap via embed token.
- CSP `frame-ancestors` already present from 001 — verified by automated `test_health_returns_csp_header` in `backend/tests/test_health.py`; extend for custom `JUKEBOX_FRAME_ANCESTORS` in polish phase (task T031).
- Angular: working login form, auth guards, token management UI inside `/admin`, HTTP interceptor with credentials.

## Non-Goals

- Google OAuth for participants (change 006+).
- Multi-user operators, password reset, MFA, rate limiting, CSRF tokens.
- Separate `/tokens` route — tokens UI lives in `/admin` (like bull post-007).
- Participant session cookie (`jukebox_participant_session`) — later change.
- Queue, SSE, event-config write APIs — later changes (may require auth from this change).
- k8s manifest changes.

## User Scenarios & Testing

### User Story 1 — Operator login (Priority: P1)

As the event moderator, I open `/login`, enter username and password, and reach `/admin` with a persistent session.

**Why this priority**: Without operator auth, moderation cannot be secured.

**Independent Test**: `POST /api/auth/login` with valid creds returns 200 + Set-Cookie; `GET /api/auth/me` returns user; invalid creds return 401.

**Acceptance Scenarios**:

1. **Given** valid operator credentials, **When** I submit the login form, **Then** I am redirected to `/admin` and subsequent API calls include the session cookie.
2. **Given** invalid credentials, **When** I submit the login form, **Then** I see "Credenciales inválidas" and remain on `/login`.
3. **Given** an authenticated session, **When** I click logout in `/admin`, **Then** the session is cleared and I must log in again to access `/admin`.

---

### User Story 2 — Kiosk iframe via embed token (Priority: P1)

As the organizer, I configure kiosk-screen with a jukebox iframe URL containing a valid embed token so the display loads without the login screen.

**Why this priority**: Core kiosk integration path; blocks display work in change 007.

**Independent Test**: Create embed token via `POST /api/tokens` (curl/authed session), `embed_token` pytest fixture, or admin UI after US3 → open `/?token=…` in fresh browser → display loads authenticated; revoked token returns 401 on exchange.

**Acceptance Scenarios**:

1. **Given** a valid embed token, **When** the display SPA loads `/?token=<plaintext>`, **Then** it exchanges the token, removes the query param from the URL, and renders `/` without visiting `/login`.
2. **Given** a revoked or invalid embed token, **When** the SPA attempts exchange on `/`, **Then** it stays on `/`, shows a static error message (e.g. "Token inválido o revocado"), and does **not** redirect to `/login` or render the operator login form.
3. **Given** an embedded iframe parent allowed by `JUKEBOX_FRAME_ANCESTORS`, **When** the display loads, **Then** CSP permits embedding.
4. **Given** an authenticated display session that later expires, **When** a protected API call returns 401 on `/`, **Then** the display shows a static error message (e.g. "Sesión caducada") and does **not** redirect to `/login`.

---

### User Story 3 — Manage embed tokens in admin (Priority: P2)

As the moderator, I create, list, and revoke embed tokens from `/admin` to provision kiosk URLs.

**Why this priority**: Operational workflow for rotating compromised tokens.

**Independent Test**: `POST /api/tokens` returns plaintext once; `GET /api/tokens` omits plaintext; `DELETE` revokes.

**Acceptance Scenarios**:

1. **Given** I am logged in, **When** I create a token with label "Kiosk sala", **Then** I see the plaintext once with copy guidance and the token appears in the list without the secret.
2. **Given** an active token, **When** I revoke it, **Then** subsequent `POST /api/auth/token` with that plaintext returns 401.

---

### Edge Cases

- Bootstrap already created operator from env — login uses that user; bootstrap remains idempotent.
- Token exchange with malformed body → 422.
- Session cookie missing on protected endpoint → 401 JSON `{"detail":"not authenticated"}`.
- `GET /api/auth/me` without session → 401 (not redirect; SPA handles).
- `/participar` remains **public** — no operator guard on participant route in this change.
- Multiple browser tabs share the same operator session.
- Rotating `JUKEBOX_SESSION_SECRET` invalidates all sessions (documented ops note).
- Failed embed token exchange on `/` (revoked, invalid, malformed) → static error on display route; kiosk must never show operator login.
- Expired operator session on `/` (401 from protected API) → static error on display route; no redirect to `/login`.
- Unauthenticated visit to `/` **without** a `token` query param → redirect to `/login` (operator direct access).

## Requirements

### Functional Requirements

- **FR-001**: System MUST authenticate operators via `POST /api/auth/login` with `{username, password}` and session cookie `jukebox_session`.
- **FR-002**: System MUST provide `POST /api/auth/logout`, `GET /api/auth/me` for operator session lifecycle.
- **FR-003**: System MUST store embed tokens hashed in `api_tokens`; plaintext returned only on creation.
- **FR-004**: System MUST exchange embed token via `POST /api/auth/token` `{token}` and set the same operator session as password login.
- **FR-005**: Operator MUST manage tokens via `GET/POST/DELETE /api/tokens` (authenticated).
- **FR-006**: Angular MUST guard `/admin` with operator auth; `/login` redirects authenticated users away.
- **FR-007**: Angular MUST guard `/` (display) with operator auth **or** successful embed token bootstrap. If embed token exchange fails, `/` MUST render a static error state (no redirect to `/login`). Unauthenticated visit without `?token=` MUST redirect to `/login` (baseline `displayGuard` from US1; embed/error behavior completed in US2).
- **FR-008**: `/participar` MUST remain accessible without operator login in this change.
- **FR-009**: All authenticated HTTP calls MUST use `withCredentials: true`. On protected routes, 401 triggers logout + redirect to `/login` (except auth endpoints). On `/` (display), 401 MUST show a static error state instead of redirecting to `/login` — see FR-007 for failed embed-token exchange and expired operator session.
- **FR-010**: Public endpoints in this change: `GET /api/health`, `POST /api/auth/login`, `POST /api/auth/token`.

### Key Entities

- **User** (existing): operator account; bootstrap from `JUKEBOX_OPERATOR_*`.
- **ApiToken** (new): `id`, `user_id`, `label`, `token_hash`, `created_at`, `last_used_at`, `revoked_at`.

## Success Criteria

- **SC-001**: Moderator completes login and reaches `/admin` in under 30 seconds on first attempt *(manual smoke in quickstart; non-gating UX target, not CI-enforced)*.
- **SC-002**: Kiosk URL with valid token loads display route without login form in a fresh browser profile.
- **SC-003**: Revoked token cannot establish a session (100% rejection in automated tests).
- **SC-004**: `pytest backend/tests` includes `test_auth.py`, `test_tokens.py` and passes with zero failures.
- **SC-005**: `npm run build` succeeds with auth guards and interceptor wired.

## Assumptions

- Single operator user per deployment (same as amrn-bull).
- Token query parameter name is `token` (amrn-bull / kiosk-screen convention).
- Bcrypt for password and token hashing (existing `security.py` pattern).
- Spanish UI strings for login and token panels.
- Alembic migration `0002_api_tokens` adds `api_tokens` table.

## Contract updates (required before implement)

- `specs/contracts/backend-api/contract.md` — auth + tokens endpoints, `api_tokens` schema, protected vs public routes, future-route auth policy
- `specs/contracts/app-core/contract.md` — `AuthService`, guards, interceptor, admin token UI, bootstrap flow
