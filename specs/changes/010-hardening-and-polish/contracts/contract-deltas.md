# Contract Deltas: 010-hardening-and-polish

**Status**: draft — merge into active contracts before/at implementation (constitution IV & I).

This change modifies three contracts: `backend-api`, `app-core`, `ops-platform`. It is remediation + completion + hygiene; it does not add product surfaces. Unless stated as **changed** or **new**, all 001–009 behavior is unchanged.

---

## backend-api

### SSE audience isolation (changes 004/007/009 behavior)

Current contract: `GET /api/events/stream` (operator **or** participant) broadcasts `state`, `notification`, and `api_key_usage` to **all** subscribers; clients filter. **New behavior**: the server routes by subscriber audience.

| Event | Old delivery | New delivery |
|-------|--------------|--------------|
| `state` | all subscribers | all authorized subscribers (unchanged) |
| `notification` | all subscribers (client filters by `participant_id`) | **only** the subscriber(s) whose authorizing identity matches the target `participant_id` |
| `api_key_usage` | all subscribers | **only** operator-authorized subscribers |

- Each stream connection is tagged at subscribe time with its authorizing audience: `operator` or `participant:{participant_id}`.
- Ambiguous/unknown subscribers are treated as participant-scope (least privilege) and never receive `api_key_usage`.
- The single endpoint and SSE transport are retained; no new stream endpoints.
- Update the change-004/007/009 notes in the active contract that state "server broadcasts to all subscribers; clients ignore" → server-side routing.

### New endpoints — event configuration (resolves "Planned (007+)")

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/event-config` | operator session | 200 `EventConfigRead` |
| PUT | `/api/event-config` | operator session | 200 `EventConfigRead` |

`EventConfigRead` fields (from existing `event_config` singleton `id=1`): `name`, `subtitle`, `app_height_px`, `theme`, `queue_visible_count`, `updated_at`.

`PUT /api/event-config` body: subset or full of `{ name, subtitle, app_height_px, theme, queue_visible_count }`.

Validation:

| Field | Rule |
|-------|------|
| `name` | non-empty string, max length (define in plan) |
| `subtitle` | string, max length; may be empty |
| `app_height_px` | integer > 0 (define sane min/max) |
| `queue_visible_count` | integer within `[1, N]` (align with 004 `queue_visible_count` default 8) |
| `theme` | member of the supported theme set |

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated / participant | 401 | `not authenticated` |
| Invalid field value | 422 | FastAPI validation error / stable `detail` |

On success: persist to `event_config`, bump runtime `revision`, and broadcast the updated `state` over SSE so kiosk/admin reflect the change without reload. **No Alembic migration** (columns already exist).

Remove the `## Planned (007+)` section (`GET`/`PUT /api/event-config`) from the active contract; document these as active.

#### Participant theme delivery (changes 005/006)

- No change needed: `ParticipantStateResponse` (from `GET /api/participant/state`) **already includes** the full `event_config` (with `theme`), so `/participar` applies the theme from state (FR-019). The dedicated operator `GET/PUT /api/event-config` stays operator-only for editing. (See analyze A1 — the earlier concern was dismissed at implementation.)

### API-token verification hardening (changes 002 behavior)

- Add a non-secret **lookup prefix** to `api_tokens` (indexed); token verification locates the candidate row by prefix, then performs a single hash comparison. No full-table bcrypt scan.
- Secret material stays bcrypt-hashed; the prefix is not sufficient to authenticate.
- **Pre-existing tokens without a prefix are rejected** and must be regenerated (one-time; documented in ops-platform / quickstart). Update the 002 token-exchange description accordingly.

### Referential integrity — `queue_entries.submitted_by_participant_id`

- Becomes a **foreign key** to `participants.id` (was a loose nullable string). Migration nulls orphan references before adding the constraint; reversible.

### Submit metadata validation consistency (changes 004/006/008)

- Operator `POST /api/queue/dev-submit` and participant `POST /api/queue/submit` MUST use the **same** metadata validation strictness. Update the contract note that currently allows lenient fallback title on one path only. Error shape for invalid references unchanged (`422 invalid youtube reference`).

### Async / non-blocking outbound I/O (internal; no API surface change)

- YouTube `search.list`, `videos.list`, oEmbed, and Google OAuth token/userinfo calls become non-blocking (async client or off-loop). Timeouts and client-visible error mappings (`503 youtube search unavailable`, OAuth `oauth_error=exchange_failed`, etc.) are **unchanged**.

### Rate limiter & quota-day (changes 008/009)

- Search rate limiter evicts expired/idle windows (bounded memory); externally observable `429 search rate limit exceeded` behavior unchanged.
- Quota-day reset evaluated deterministically on each usage read/increment at the Pacific boundary (no traffic dependency). `ApiKeyUsageListResponse` shape unchanged.

### CORS

- `allow_headers` restricted to the SPA's actual request headers (not `*`) when `allow_credentials=True`. Origins behavior unchanged.

### Migrations

| Revision | Change |
|----------|--------|
| `0007_api_token_prefix` | Add indexed non-secret lookup prefix column to `api_tokens` |
| `0008_queue_submitter_fk` | Null orphan `submitted_by_participant_id`, add FK → `participants.id` (reversible) |

(No migration for event-config; `event_config` columns already exist.)

### Route auth policy additions

| Path | Auth |
|------|------|
| `GET /api/event-config` | operator session |
| `PUT /api/event-config` | operator session |

`backend/tests/test_auth_policy.py` canonical list updated to include the two event-config routes as operator-protected.

### Tests (add/extend)

- `test_sse.py` / `test_notifications.py` — assert audience isolation: participant streams exclude `api_key_usage`; `notification` delivered only to target participant.
- `test_event_config.py` (new) — GET/PUT, validation, auth policy, `state`/revision propagation.
- `test_tokens.py` / `test_auth.py` — prefix-based lookup; rejection + reissue of prefix-less tokens.
- `test_youtube_api_key_usage.py` — quota rollover evaluated on read at boundary.
- `test_youtube_search.py` — rate-limiter eviction.
- Migration test for `0008` orphan nulling.
- `test_auth_policy.py` — updated canonical route list.

---

## app-core

### Admin — "Evento" section (replaces placeholder)

| Section | Position | Content |
|---------|----------|---------|
| **Evento** | After **Uso de API Keys** (existing position) | Editable Spanish form (was "próximamente" placeholder) |

Form fields bound to `GET/PUT /api/event-config`:

| Field (Spanish label) | Source | Control |
|-----------------------|--------|---------|
| Nombre | `name` | text |
| Subtítulo | `subtitle` | text |
| Altura del display (px) | `app_height_px` | number |
| Tema | `theme` | select (supported themes) |
| Canciones visibles en la cola | `queue_visible_count` | number |

Copy (Spanish):

| Key | Spanish |
|-----|---------|
| `save` | Guardar cambios |
| `saved_ok` | Configuración del evento guardada. |
| `save_error` | No se pudo guardar la configuración del evento. |
| `validation_error` | Revisa los campos: valores fuera de rango. |

Data flow: on `/admin` init `GET /api/event-config`; on save `PUT /api/event-config`; kiosk/admin reflect changes via existing `DisplayStateService` `state$` (SSE), no reload.

### Theme application (wires previously-unused `event_config.theme`)

- The SPA MUST apply `event_config.theme` (from `state`) on kiosk `/` and participant `/participar`. Unrecognized theme → default dark theme. Document the supported theme set and the applied tokens.

### Kiosk display layout (changes 004 behavior)

- Replace the fragile fixed-pixel height (`--jukebox-app-height` as a hard clip) with a responsive layout: the configured `app_height_px` becomes a **target**, not a hard `max-height` that clips. Player (2/3) + QR (1/3) top region and the ~10% queue strip MUST remain visible without clipping from 720p to 4K.

### Moderation UX (changes 004 behavior)

- Per-row busy state: acting on one pending entry disables only that row's Aprobar/Rechazar controls, not the whole table. Replace the single global `moderationBusy` flag.

### QR panel (changes 004 behavior)

- Regenerate the QR image only when the participation URL changes, not on every `ngOnChanges`/change-detection cycle.

### App shell / routing

- Add a Spanish **404** page for unknown routes (replace the silent `**` → `/` redirect).
- Add loading states for long-running fetches on `/admin` and `/participar`.

### Dependencies

- Remove unused **Angular Material** and **CDK** from `package.json`; production build stays within the configured budget (800 kb warn / 1.5 mb error initial).

### Dev/test affordances

- Confine `AuthService.resetForTesting()`, `ParticipantService.devAuthAsync()`, and the dev-auth login button to test builds or gate them so they are not reachable in production (`environment.allowDevParticipantAuth` already false in prod; extend the guard to the residual affordances).

### Tests (add)

- Guards (`authGuard`, `guestGuard`, `displayGuard`) behavior.
- `authInterceptor` 401 branching by route (`/`, `/participar`, `/login`, other).
- At least one SSE service (`DisplayStateService` or `ParticipantStateService`) including audience handling.
- Event-config admin form (load, edit, validation, save).

### Unchanged

- Login, tokens panel, participant OAuth/search/submit/voting/notifications, api-key usage table (except it now updates only for operator via server-side SSE routing — the client already only renders on `/admin`).

---

## ops-platform

### Secrets hygiene (changes 001 baseline)

- `.env` MUST be removed from version control and ignored by `.gitignore`; only `.env.example` remains tracked.
- Document a **session-secret rotation** procedure (effect: invalidates operator/participant cookies and in-flight OAuth state → users re-authenticate).
- Document **one-time API/embed token regeneration** required by the token-prefix change.

### Deployment topology (changes 003 behavior)

- `deploy/k8s/backend.yaml` MUST set `replicas: 1`.
- `deploy/k8s/README.md` MUST document that SSE fan-out, search rate limiting, YouTube key rotation, and per-key quota counters are **per-process** and require single-replica operation until external shared state (e.g. Redis) is introduced. No HPA/PDB for the backend while this holds.
- The GitOps mirror (`argocd-apps/manifests/jukebox/`) inherits the same `replicas: 1`.

### CI

- No pipeline shape change; new backend pytest and frontend vitest tests run in the existing `release-images.yml` steps. Optionally document that new tests must pass before image build.

### Unchanged

- Compose services, Dockerfiles, nginx, release/bump workflows, ingress, migration Job ordering (the two new Alembic revisions `0007`/`0008` run via the existing migration Job before backend rollout).

---

## SDD hygiene (docs — not a runtime contract, tracked here for completeness)

- Reconcile active-contract consolidation headers and change history to include **009** and **010**; remove `backend-api` "Planned (007+) event-config".
- Remove the duplicated `.specify/.specify/` directory (single canonical `.specify/`).
- Update `AGENTS.md` "Active SDD work" and `specs/manifest.yml` (`changes[]` entry + `active`) for `010-hardening-and-polish`.
