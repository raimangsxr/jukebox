---
id: 010-hardening-and-polish
type: change
status: draft
modifies:
  - backend-api
  - app-core
  - ops-platform
depends_on:
  - 001-foundation-jukebox
  - 002-operator-auth-embed-tokens
  - 003-kubernetes-manifests
  - 004-kiosk-display-queue
  - 005-participant-voting
  - 006-participant-oauth-submit
  - 007-participant-notifications
  - 008-youtube-text-search
  - 009-admin-api-key-usage
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Hardening & Polish

**Feature Branch**: `010-hardening-and-polish` | **Change id**: `010-hardening-and-polish` | **Date**: 2026-07-22

**Created**: 2026-07-22

**Status**: Draft

**Input**: Revisión global del proyecto (contratos activos + código backend/frontend). Corregir los defectos de seguridad, robustez y coherencia detectados, completar la configuración de evento editable (placeholder "próximamente"), pulir la UX/visual del kiosk y del admin, ampliar cobertura de tests y sanear la higiene SDD/repo. **Fuera de alcance**: nuevas features de producto (posición/ETA en cola, Web Push, protocolo iframe kiosk, historial, multi-evento, moderación asistida) — se abordan en cambios posteriores.

## Clarifications

### Session 2026-07-22

- Q: ¿Una change consolidada o varias agrupadas? → A: **Una única change consolidada** que toca los tres contratos (`backend-api`, `app-core`, `ops-platform`).
- Q: ¿La corrección de fuga por SSE se resuelve solo filtrando en cliente? → A: **No**. El filtrado DEBE ser en **servidor**: los eventos de operador (`api_key_usage`) no viajan a suscriptores participantes, y cada `notification` se entrega **solo** al `participant_id` destinatario.
- Q: ¿El editor de "Evento" requiere migración de datos? → A: **No**. La tabla `event_config` ya tiene todas las columnas (`name`, `subtitle`, `app_height_px`, `theme`, `queue_visible_count`); solo hay que exponerlas y editarlas.
- Q: ¿Se acepta invalidar sesiones al rotar `JUKEBOX_SESSION_SECRET`? → A: **Sí**. Rotar el secreto invalida cookies de operador/participante y estados OAuth en vuelo; es aceptable dado el tamaño de uso. Ver Assumptions.
- Q: ¿Se resuelve el escalado horizontal introduciendo estado externo (Redis) en este cambio? → A: **No en este cambio**. Se fija y documenta explícitamente el despliegue **de una sola réplica** como restricción operativa; externalizar el estado compartido queda diferido (Non-Goals).
- Q: ¿Alcance de temas al conectar `event_config.theme` (FR-019)? → A: **Solo `default` (oscuro actual)**. Se valida el campo y se aplica el tema oscuro existente como `default`; temas adicionales (claro, acento) quedan fuera de alcance (feature futura). Un valor no reconocido cae al `default`.
- Q: ¿Qué pasa con los embed/API tokens existentes tras añadir prefijo indexado (FR-008)? → A: **Forzar regeneración**. Los tokens previos sin prefijo dejan de validar; el operador los regenera una vez y reconfigura los embeds del kiosk. Sin fallback de escaneo O(n) para legados. Procedimiento documentado en ops.
- Q: ¿Rotar `JUKEBOX_SESSION_SECRET` como parte de este cambio (FR-006)? → A: **Sí, rotar ahora**. Se genera un secreto nuevo al remediar; invalida cookies de operador/participante y estados OAuth en vuelo (re-login único). Correcto por posible exposición en el historial de git.
- Q: ¿Rol de `event_config.app_height_px` en el layout responsivo (FR-020)? → A: **Objetivo, no recorte**. El layout es responsivo (720p–4K sin recorte) y `app_height_px` se usa como altura objetivo/hint cuando cabe; sigue editable en "Evento". No se deprecia el campo.

## SDD Context

- Depends on: **all prior changes 001–009** (this change hardens and polishes existing behavior; it does not introduce new product surfaces).
- Modifies contracts: `backend-api`, `app-core`, `ops-platform`.
- Product baseline unchanged: collaborative YouTube jukebox with kiosk display, participant voting/submission, operator moderation, YouTube search, per-key usage tracking.
- This change is **remediation + completion + hygiene**, grouped into independently testable workstreams (security, backend robustness, event configuration, frontend polish, tests, SDD/repo hygiene).

## Problem

The consolidated review surfaced defects and gaps that do not change *what* the product does but materially affect its **security, correctness, operability, and finish**:

1. **SSE data isolation** — `GET /api/events/stream` admits operator *and* participant sessions and fans out **every** event to **every** subscriber with no server-side filtering. Operator-only `api_key_usage` payloads reach any connected participant, and each `notification` (carrying another participant's `participant_id` and song `title`) is broadcast to all participants; filtering happens only in the client.
2. **Secrets in the repository** — a real `.env` is tracked in git (not gitignored, unlike `.env.example`), exposing `JUKEBOX_SESSION_SECRET` and `JUKEBOX_OPERATOR_PASSWORD` patterns.
3. **Blocking network I/O in the async request path** — YouTube search, oEmbed metadata, `videos.list` duration, and the full Google OAuth flow use synchronous `urllib` inside coroutines, blocking the event loop under load.
4. **In-process shared state is not scale-safe** — SSE hub, search rate limiter, and YouTube key-pool rotation/exhaustion live in module globals; running more than one replica silently breaks event fan-out, rate limiting, key rotation, and quota accounting. The deployment target is Kubernetes/ArgoCD, so this is a real risk.
5. **Robustness gaps** — O(n) bcrypt scan on every API-token exchange; the search rate limiter never evicts idle buckets (unbounded memory); the quota-day reset is lazy and only fires on incoming traffic; `queue_entries.submitted_by_participant_id` has no FK (orphan risk, inconsistent with `votes`); metadata validation differs between operator `dev-submit` (lenient) and participant submit (strict).
6. **Unfinished / rough UI** — the admin **"Evento"** section is a visible placeholder ("próximamente") and no `GET/PUT /api/event-config` exists, so event configuration (name, subtitle, display height, theme, visible queue count) is not editable outside the database; `event_config.theme` is unused; the kiosk layout relies on a fragile fixed-pixel height that can clip content; moderation uses a single global busy flag disabling all rows at once; the QR regenerates on every change-detection cycle; Angular Material/CDK are declared but unused; there is no 404 page or global loading/error shell.
7. **Thin frontend tests + stale SDD docs** — only three pure-logic frontend specs (no component/guard/interceptor/SSE tests); contract headers are out of date (`app-core` header stops at 008 though it documents 009; `backend-api` still lists `event-config` under "Planned"); the `.specify/.specify/` directory duplicates the whole toolchain; `AGENTS.md` "Active SDD work" is stale.

## Goals

- **Eliminate cross-audience data exposure** over SSE via server-side routing/filtering, with no regression to live kiosk/admin/participant updates.
- **Remove committed secrets** from version control and establish `.env` as untracked, with a documented rotation step.
- **Stop blocking the event loop** on all outbound HTTP, and make shared runtime state **safe for the supported deployment topology** (single replica), documented explicitly.
- **Harden auth-token verification, bound rate-limiter memory, make quota-day reset deterministic, enforce referential integrity, and unify submit-metadata validation.**
- **Complete event configuration management**: an operator-editable "Evento" section backed by `GET/PUT /api/event-config`, including theme applied by the frontend.
- **Polish the visual/UX finish** of kiosk and admin (responsive layout, per-row moderation feedback, QR caching, dead-dependency removal, 404/loading states).
- **Raise test coverage** for the changed behaviors on both backend and frontend.
- **Reconcile SDD/repo hygiene** (contract headers, duplicated `.specify`, `AGENTS.md`, manifest).

## Non-Goals

- Any product feature from review section 4 (queue position/ETA for participants, Web Push, kiosk `bull:config`/`bull:resize` iframe protocol, played-songs history, event analytics, multi-event support, assisted/bulk moderation).
- **Externalizing shared state to Redis or another store**, HPA, or multi-replica scale-out — explicitly deferred; this change instead **pins and documents single-replica** operation.
- Creating/editing/deleting YouTube API keys from the UI (keys remain deployment config; 009 unchanged except where isolation applies).
- Adding light/dark theme *switching UX* beyond wiring the existing `event_config.theme` value; a full multi-theme design system is out of scope.
- Internationalization / multi-language (UI stays Spanish, `lang="es"`).
- Changing the queue lifecycle, voting rules, OAuth provider, or moderation semantics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - SSE data isolation (Priority: P1)

As a participant on `/participar`, I must never receive over the realtime stream any data addressed to operators or to other participants; and as an operator, my API-key usage data must not leak to attendees' devices.

**Why this priority**: Active exposure of operator-only data and of other participants' identifiers/titles to every connected device is a security/privacy defect present in production today.

**Independent Test**: Connect a participant SSE client and an operator SSE client; trigger a YouTube search (usage change) and approve a song for participant A; assert the participant stream never receives `api_key_usage`, and that a `notification` for A is delivered only to A's stream, not to participant B or to the kiosk.

**Acceptance Scenarios**:

1. **Given** a participant SSE subscriber and an operator action that changes API-key usage, **When** the `api_key_usage` event is broadcast, **Then** the participant stream does **not** receive it and the operator/admin stream does.
2. **Given** two participant subscribers A and B, **When** a `song.approved`/`song.up_next` notification targets A, **Then** only A's stream receives the `notification` event; B's stream does not.
3. **Given** any subscriber, **When** the queue/runtime `state` changes, **Then** all authorized subscribers still receive the `state` event as before (no regression).
4. **Given** a participant tries to read `GET /api/youtube/api-keys/usage` directly, **When** the request is made, **Then** it is rejected with `401`/`403` (unchanged 009 behavior).

---

### User Story 2 - Secrets hygiene (Priority: P1)

As the operator/maintainer, I need application secrets kept out of version control so a repo clone or leak cannot reveal the session secret or operator password.

**Why this priority**: Committed secrets are a standing exposure; remediation is low-effort and high-impact.

**Independent Test**: Confirm `.env` is no longer tracked (`git ls-files .env` empty), is ignored by git, and that `.env.example` remains the only committed template; confirm the documented rotation step exists.

**Acceptance Scenarios**:

1. **Given** the repository, **When** listing tracked files, **Then** `.env` is not tracked and is matched by `.gitignore`.
2. **Given** a fresh clone, **When** following the quickstart, **Then** the operator copies `.env.example` to `.env` and the app boots with local values.
3. **Given** the session secret is rotated, **When** the backend restarts, **Then** existing operator/participant cookies are invalidated cleanly (users re-authenticate) with no server error.

---

### User Story 3 - Non-blocking outbound I/O and scale-safe state (Priority: P2)

As an operator running a live event, I need the backend to stay responsive while it calls YouTube/Google, and I need the deployment topology to match the runtime's shared-state assumptions.

**Why this priority**: Blocking calls degrade responsiveness under concurrency; a silent multi-replica misconfiguration would break realtime and quota accounting during an event.

**Independent Test**: Under concurrent participant searches, assert request handlers do not serialize on outbound HTTP (event loop not blocked); confirm deployment manifests pin a single replica and the constraint is documented.

**Acceptance Scenarios**:

1. **Given** an outbound YouTube/Google HTTP call, **When** it is in flight, **Then** other request handlers continue to progress (no event-loop blocking).
2. **Given** the Kubernetes manifests, **When** inspected, **Then** backend `replicas` is `1` and the README documents that SSE fan-out, rate limiting, key rotation, and quota counters are per-process and require single-replica until external state is introduced.
3. **Given** the existing YouTube search, OAuth, and metadata flows, **When** exercised after the I/O change, **Then** their functional behavior and error mapping are unchanged (regression).

---

### User Story 4 - Backend robustness fixes (Priority: P2)

As the maintainer, I want token verification, rate-limiter memory, quota-day reset, referential integrity, and submit validation to be correct and consistent.

**Why this priority**: These are latent correctness/resource defects that worsen with scale and data volume.

**Independent Test**: Targeted tests for each fix (token lookup by prefix; rate-limiter eviction; quota-day rollover on read at the Pacific boundary; FK constraint rejects orphan links; unified metadata validation across submit paths).

**Acceptance Scenarios**:

1. **Given** many active API tokens, **When** a token is exchanged, **Then** verification locates the candidate by an indexed prefix and performs at most one hash comparison for the matching token (no full-table bcrypt scan).
2. **Given** a token that predates the prefix scheme, **When** it is presented, **Then** it is rejected and the operator is instructed to regenerate it (documented one-time reissue).
3. **Given** participants who searched long ago, **When** their rate-limit windows expire, **Then** their buckets are evicted and memory does not grow unbounded.
4. **Given** the Pacific quota-day boundary passes with no traffic, **When** the next usage read occurs, **Then** counts reflect the reset (used 0 / remaining 100) deterministically.
5. **Given** a `queue_entries` row, **When** `submitted_by_participant_id` is set, **Then** it must reference an existing participant (FK enforced); pre-existing orphan references are cleaned (set null) by migration.
6. **Given** operator `dev-submit` and participant submit, **When** each resolves metadata, **Then** both use the same validation strictness (invalid references rejected consistently).

---

### User Story 5 - Editable event configuration (Priority: P2)

As an operator on `/admin`, I want to edit the event name, subtitle, display height, theme, and visible queue count and have the kiosk reflect the changes, replacing the current "próximamente" placeholder.

**Why this priority**: The "Evento" section is a visibly unfinished feature and event settings are otherwise only editable in the database.

**Independent Test**: Open `/admin` → edit name/subtitle/height/theme/visible-count → save → confirm `PUT /api/event-config` persists and the kiosk `/` reflects the new values (via existing `state`/SSE) including the applied theme.

**Acceptance Scenarios**:

1. **Given** an operator session, **When** I open the "Evento" section, **Then** I see the current `event_config` values in an editable form (not a placeholder).
2. **Given** I change the event name and subtitle and save, **When** the request succeeds, **Then** `PUT /api/event-config` returns the updated config and the kiosk header and QR panel show the new values without a full reload (state/SSE).
3. **Given** I set the theme to a supported value, **When** I save, **Then** the frontend applies the corresponding theme on kiosk/participant surfaces (the previously unused `event_config.theme` now takes effect).
4. **Given** I submit an invalid value (e.g. non-positive height, out-of-range visible count, unsupported theme), **When** I save, **Then** the API returns a validation error and the UI shows a Spanish message; the stored config is unchanged.
5. **Given** a participant/unauthenticated caller, **When** they call `PUT /api/event-config`, **Then** it is rejected (`401`); `GET /api/event-config` visibility follows the documented auth policy.

---

### User Story 6 - Frontend visual/UX polish (Priority: P3)

As a viewer of the kiosk and as an operator, I want a display that adapts to the screen without clipping, per-row moderation feedback, and a finished, dependency-lean SPA.

**Why this priority**: Improves reliability and finish; lower urgency than security/correctness.

**Independent Test**: Verify the kiosk renders without clipping across common resolutions; moderation disables only the acted row; QR regenerates only when its URL changes; unused Material/CDK removed; a 404 page and loading states exist.

**Acceptance Scenarios**:

1. **Given** kiosk resolutions from 720p to 4K, **When** the display renders, **Then** player, QR, and queue strip remain visible without clipping (responsive layout, not a fixed pixel height that overflows).
2. **Given** a pending queue with many entries, **When** I approve/reject one, **Then** only that row's controls show a busy state; other rows remain actionable.
3. **Given** the participation URL is unchanged, **When** display state updates, **Then** the QR image is not regenerated every change-detection cycle.
4. **Given** the built SPA, **When** dependencies are inspected, **Then** unused Angular Material/CDK are removed and the initial bundle is within budget.
5. **Given** an unknown route, **When** navigated to, **Then** a Spanish 404 page is shown (instead of a silent redirect), and long-running loads show a loading state.

---

### User Story 7 - Test coverage for changed behavior (Priority: P3)

As the maintainer, I want automated tests covering the new/changed behavior so regressions are caught.

**Why this priority**: Constitution principle V requires tests for changed behavior; frontend coverage is currently thin.

**Independent Test**: New/extended backend tests (SSE isolation, event-config CRUD + auth, token-prefix lookup, rate-limiter eviction, quota rollover on read, FK migration) and frontend tests (guards, interceptor, SSE services, event-config form) pass in CI.

**Acceptance Scenarios**:

1. **Given** the SSE isolation change, **When** tests run, **Then** they assert participant streams exclude `api_key_usage` and cross-participant `notification`.
2. **Given** the event-config endpoint, **When** tests run, **Then** they cover read, update, validation errors, and auth policy.
3. **Given** the frontend, **When** vitest runs, **Then** guards, the auth interceptor's 401 branching, and at least one SSE service and the event-config form are covered.

---

### User Story 8 - SDD and repository hygiene (Priority: P3)

As an agent/maintainer following SDD, I want contracts, manifest, agent instructions, and the toolchain directory to be accurate and non-duplicated.

**Why this priority**: Keeps the SDD source-of-truth trustworthy; low functional risk.

**Independent Test**: Contracts reflect implemented state (headers include 009/010; no stale "Planned event-config"); `.specify/.specify/` duplication removed; `AGENTS.md` active section and `manifest.yml` reflect this change.

**Acceptance Scenarios**:

1. **Given** the active contracts, **When** read, **Then** their consolidation headers and change history include all implemented changes and this change's outcomes; `event-config` is documented as active, not planned.
2. **Given** the repo, **When** inspected, **Then** the nested `.specify/.specify/` duplicate toolchain is removed (single canonical `.specify/`).
3. **Given** `AGENTS.md` and `manifest.yml`, **When** read, **Then** they reflect `010-hardening-and-polish` as the active/most-recent change with correct status.

---

### Edge Cases

- SSE subscriber whose session type cannot be determined → treated as least-privileged (participant-scope), never receives operator events.
- A single browser holding both an operator session and a participant session → server routes events by the identity used to authorize *that* stream connection, not by cookies present.
- Session-secret rotation mid-event → all clients get `401` and are prompted to re-authenticate; kiosk shows the existing "Sesión caducada" state (002) rather than an error.
- Orphan `submitted_by_participant_id` values already in the database at migration time → set to `null` (submissions remain, attribution dropped) before the FK is added; migration is reversible.
- Existing API/embed tokens without a stored prefix → invalid after the change; operator regenerates them (one-time, documented; kiosk embeds must be re-issued).
- `event_config` edited to an `app_height_px` or `queue_visible_count` outside allowed bounds → rejected with validation error; kiosk continues using the last valid value.
- Theme value not recognized by the frontend → frontend falls back to the default dark theme.
- Outbound HTTP timeout after migration to async client → same error mapping as today (`503 youtube search unavailable`, OAuth `exchange_failed`, etc.).

## Requirements *(mandatory)*

### Functional Requirements — Security & isolation

- **FR-001**: The backend MUST route SSE events by audience so that `api_key_usage` events are delivered **only** to operator-authorized subscribers and never to participant-authorized subscribers.
- **FR-002**: `notification` events (`song.approved`, `song.up_next`) MUST be delivered **only** to the SSE subscriber(s) matching the target `participant_id`; other participants and kiosk/operator subscribers MUST NOT receive them.
- **FR-003**: `state` events MUST continue to be delivered to all authorized subscribers (no regression).
- **FR-004**: Server-side routing MUST classify each subscriber by the identity that authorized its `/api/events/stream` connection (operator vs participant); ambiguous/unknown subscribers MUST be treated as participant-scope (least privilege).
- **FR-005**: `.env` MUST NOT be tracked by git; `.gitignore` MUST ignore it while keeping `.env.example` tracked.
- **FR-006**: `JUKEBOX_SESSION_SECRET` MUST be rotated as part of this remediation (new value), and the project MUST document the rotation procedure and its effect (invalidates operator/participant cookies and in-flight OAuth state → one-time re-authentication).
- **FR-007**: CORS configuration MUST restrict `allow_headers` to the headers actually used by the SPA instead of `*` when credentials are allowed.
- **FR-008**: API-token verification MUST NOT perform a full-table bcrypt scan; it MUST locate the candidate token via an indexed lookup (e.g. a stored non-secret prefix) and verify only the matching hash.

### Functional Requirements — Robustness & operability

- **FR-009**: All outbound HTTP (YouTube `search.list`, `videos.list`, oEmbed, Google OAuth token/userinfo) MUST NOT block the event loop; it MUST use an async client or be offloaded off the event loop.
- **FR-010**: The search rate limiter MUST bound its memory by evicting expired/idle participant windows.
- **FR-011**: The quota-day reset MUST be evaluated deterministically on each usage read/increment so displayed counts reflect the Pacific-day boundary even without intervening traffic.
- **FR-012**: `queue_entries.submitted_by_participant_id` MUST be backed by a foreign key to `participants.id`; a migration MUST null out pre-existing orphan references before adding the constraint and MUST be reversible.
- **FR-013**: Operator `dev-submit` and participant submit MUST apply the **same** YouTube metadata validation strictness (invalid references rejected consistently across both paths).
- **FR-014**: The Kubernetes manifests MUST set backend `replicas: 1`, and `deploy/k8s/README.md` MUST document that SSE fan-out, rate limiting, key rotation, and quota counters are per-process and require single-replica operation until external shared state is introduced.

### Functional Requirements — Event configuration

- **FR-015**: The backend MUST expose `GET /api/event-config` and `PUT /api/event-config` operating on the singleton `event_config` row (fields: `name`, `subtitle`, `app_height_px`, `theme`, `queue_visible_count`). No schema migration is required (columns already exist).
- **FR-016**: `PUT /api/event-config` MUST require an operator session and MUST validate inputs (positive `app_height_px`, `queue_visible_count` within a defined range, `theme` within the supported set) returning `422`/`400` with stable `detail` on invalid input; `GET` auth policy MUST be documented in the contract.
- **FR-017**: On successful update, the change MUST propagate to connected kiosk/admin via the existing `state` snapshot and SSE (no full reload required).
- **FR-018**: The admin **"Evento"** section MUST replace the "próximamente" placeholder with an editable Spanish form bound to `GET/PUT /api/event-config`, with validation messages and success feedback.
- **FR-019**: The frontend MUST apply `event_config.theme` on kiosk and participant surfaces so the field is no longer unused. Scope is limited to a single supported value `default` (the current dark theme); any other/unrecognized value MUST fall back to `default`. Additional themes (light, accent) are out of scope for this change. The kiosk obtains `theme` from the existing `state` snapshot; participant clients MUST obtain `theme` via `GET /api/participant/state` (add `theme` to `ParticipantStateResponse`), since there is otherwise no data path delivering event config to `/participar`.

### Functional Requirements — Frontend polish

- **FR-020**: The kiosk layout MUST render without clipping across common display resolutions (e.g. 720p–4K), replacing the fragile fixed-pixel height with a responsive approach that still honors the operator-configured height as a target, not a hard clip.
- **FR-021**: Moderation actions MUST show per-row busy state; acting on one pending entry MUST NOT disable controls for other rows.
- **FR-022**: The QR image MUST be regenerated only when the participation URL changes, not on every change-detection cycle.
- **FR-023**: Unused dependencies (Angular Material, CDK) MUST be removed; the production build MUST stay within existing bundle budgets.
- **FR-024**: The SPA MUST provide a Spanish 404 page for unknown routes (instead of a silent redirect to kiosk) and MUST show loading states for long-running fetches on admin/participant surfaces.

### Functional Requirements — Tests & hygiene

- **FR-025**: Automated tests MUST cover SSE audience isolation (FR-001/FR-002), event-config read/update/validation/auth (FR-015/FR-016), token-prefix lookup (FR-008), rate-limiter eviction (FR-010), quota rollover on read (FR-011), and the FK migration (FR-012).
- **FR-026**: Frontend tests MUST cover the three guards, the auth interceptor's 401 branching, at least one SSE service, and the event-config form.
- **FR-027**: Active contracts (`backend-api`, `app-core`, `ops-platform`) MUST be updated to reflect implemented state: headers/change history include 009 and 010; `event-config` documented as active (removed from "Planned"); SSE isolation semantics documented.
- **FR-028**: The duplicated `.specify/.specify/` directory MUST be removed, leaving a single canonical `.specify/`.
- **FR-029**: `AGENTS.md` active section and `specs/manifest.yml` MUST be updated to reflect `010-hardening-and-polish`.
- **FR-030**: Test/dev-only affordances in production frontend code (`AuthService.resetForTesting`, `ParticipantService.devAuthAsync`, and dev-auth UI) MUST be confined to test builds or clearly gated so they are not reachable in production.
- **FR-031**: All existing behavior from changes 001–009 (auth, tokens, queue lifecycle, moderation, voting, OAuth, submit, search, notifications, api-key usage) MUST continue to work (**regression**).

### Key Entities

- **SSE subscriber (audience-scoped)**: A stream connection tagged at subscribe time with its authorizing identity (operator vs participant + `participant_id`); used for server-side event routing. No new persistence.
- **API token (with lookup prefix)**: Existing `api_tokens` gains a non-secret indexed prefix used to locate the candidate before hash verification; the secret remains bcrypt-hashed. (Migration.)
- **Event configuration (editable)**: The existing singleton `event_config` (`name`, `subtitle`, `app_height_px`, `theme`, `queue_visible_count`) becomes readable/writable via API and editable in admin. (No migration.)
- **Queue entry submitter (FK)**: `queue_entries.submitted_by_participant_id` becomes a foreign key to `participants.id`. (Migration + orphan cleanup.)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In automated tests, **0** `api_key_usage` events reach participant SSE subscribers and **0** cross-participant `notification` events are delivered (100% isolation).
- **SC-002**: `git ls-files .env` returns empty and CI/quickstart confirm `.env` is ignored; **0** secrets tracked.
- **SC-003**: Under a concurrency test with N simultaneous searches, backend request latency for unrelated endpoints does not degrade proportionally to outbound-call latency (event loop not blocked).
- **SC-004**: API-token exchange performs **at most one** hash comparison per request regardless of the number of active tokens.
- **SC-005**: Operators can edit and persist all `event_config` fields from `/admin`, and the kiosk reflects the change (including theme) within the SSE update window (~5 s), with **0** database edits required.
- **SC-006**: The kiosk renders without content clipping at 720p, 1080p, and 2160p in layout tests/manual checks.
- **SC-007**: Moderating one entry leaves all other rows actionable (per-row busy state) — verified in a component test.
- **SC-008**: Unused Material/CDK removed; production bundle remains within the configured budget (≤ error threshold).
- **SC-009**: New/extended tests for all changed behaviors pass in CI; frontend adds guard/interceptor/SSE/event-config coverage.
- **SC-010**: Active contracts, `manifest.yml`, and `AGENTS.md` are consistent with implemented state; **0** stale "Planned event-config" references; single canonical `.specify/`.
- **SC-011**: Full regression suite for 001–009 passes with no functional degradation.

## Assumptions

- **Single-replica deployment is acceptable** for the current event scale; externalizing shared state (Redis) and horizontal scale-out are deferred to a future change. Manifests are pinned to `replicas: 1` and this is documented.
- **Session-secret rotation is acceptable to perform** as part of secrets remediation; the resulting one-time re-authentication of operators/participants is tolerable (small user base).
- **Existing API/embed tokens will be regenerated** once after the token-prefix change; there is no requirement to transparently migrate secret material of pre-existing tokens.
- **`event_config` already contains all needed columns**; exposing/editing them needs no migration. The set of supported `theme` values is small and defined during planning (at minimum the current dark theme plus one alternative or "default").
- **The SSE transport and single stream endpoint are retained**; isolation is achieved by server-side routing/tagging, not by adding new endpoints (kiosk/participant/operator continue to use `GET /api/events/stream`).
- **The async I/O migration preserves existing timeouts and error mappings** (YouTube `503`, OAuth error codes) so client-visible behavior is unchanged.
- **Orphan `submitted_by_participant_id` values are rare/absent** in real data; nulling them on migration is acceptable and reversible.
- **CI already runs backend pytest and frontend vitest** (per ops-platform contract); new tests slot into the existing pipelines.
