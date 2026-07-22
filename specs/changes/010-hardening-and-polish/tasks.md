---
description: "Task list for 010-hardening-and-polish"
---

# Tasks: Hardening & Polish

**Input**: Design documents from `specs/changes/010-hardening-and-polish/`

**Prerequisites**: [spec.md](./spec.md) (user stories), [plan.md](./plan.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md)

**Tests**: Included — the spec explicitly requires tests for changed behavior (FR-025/FR-026) and the constitution (principle V) mandates them.

**Organization**: Grouped by user story (US1–US8) so each ships as an independent increment. Priorities: US1/US2 = P1, US3/US4/US5 = P2, US6/US7/US8 = P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency)
- **[Story]**: owning user story (US1…US8)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare SDD scaffolding and dependency baseline before behavior changes.

- [ ] T001 [P] Merge `contracts/contract-deltas.md` into active contracts `specs/contracts/backend-api/contract.md`, `specs/contracts/app-core/contract.md`, `specs/contracts/ops-platform/contract.md` (add 010 sections; do not yet flip statuses that depend on implementation).
- [ ] T002 [P] Choose async HTTP approach (`httpx.AsyncClient` vs `asyncio.to_thread`) and record in `specs/changes/010-hardening-and-polish/research.md`; if `httpx`, add it to `backend/pyproject.toml` dependencies.
- [ ] T003 [P] Confirm Angular Material/CDK are unused (grep `mat-`, `@angular/material`, `@angular/cdk` under `frontend/src`) and record removal plan in research.md.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infrastructure that later stories build on. No user-visible behavior yet.

**⚠️ CRITICAL**: complete before starting US1/US2 implementation that depends on it.

- [ ] T004 [P] Add an `audience`-aware subscribe API to `backend/app/services/sse_hub.py`: `subscribe(audience)` where audience ∈ {`operator`, `participant:{id}`}; keep existing broadcast for `state`; add routed helpers `broadcast_api_key_usage` (operators only) and `deliver_notification(participant_id, payload)`.
- [ ] T005 Wire subscriber audience from the stream identity in `backend/app/routers/state.py` `GET /api/events/stream` (use `get_stream_subscriber` result; default to participant-scope when ambiguous).
- [ ] T006 [P] Add `EventConfigRead` and `EventConfigUpdate` schemas in `backend/app/schemas.py` (fields: `name`, `subtitle`, `app_height_px`, `theme`, `queue_visible_count`, `updated_at`) with validation bounds from research.md.

**Checkpoint**: SSE hub can route by audience; event-config schemas exist.

---

## Phase 3: User Story 1 — SSE data isolation (P1) 🎯 MVP

**Goal**: Operator-only and participant-targeted events never reach the wrong subscribers; `state` unaffected.

**Independent Test**: Connect participant + operator SSE clients; trigger a usage change and approve a song for A; assert participant stream excludes `api_key_usage` and only A receives its `notification`.

### Tests for US1 (write first, must fail) ⚠️

- [ ] T007 [P] [US1] In `backend/tests/test_sse.py`, assert `api_key_usage` is delivered to operator subscribers only (participant subscriber never receives it) and `state` still reaches all subscribers.
- [ ] T008 [P] [US1] In `backend/tests/test_notifications.py`, assert `song.approved`/`song.up_next` reach only the target `participant_id`'s subscriber, not other participants nor operator/kiosk.

### Implementation for US1

- [ ] T009 [US1] Route `api_key_usage` broadcasts through the operator-only path in `backend/app/services/youtube_api_key_usage_service.py` (call `broadcast_api_key_usage`).
- [ ] T010 [US1] Change `backend/app/services/notification_service.py` to deliver via `deliver_notification(participant_id, …)` instead of global broadcast.
- [ ] T011 [US1] Verify frontend consumers still work with server-side routing (no client change required): `frontend/src/app/services/display-state.service.ts` (kiosk/admin) and `participant-state.service.ts` (participant). Remove now-redundant client-side notification filtering only if it stays correct.

**Checkpoint**: SSE isolation enforced server-side; `state` regression-free.

---

## Phase 4: User Story 2 — Secrets hygiene (P1)

**Goal**: No secrets tracked; session secret rotated; CORS tightened.

**Independent Test**: `git ls-files .env` empty and ignored; app boots from `.env.example`; rotated secret invalidates old cookies cleanly.

- [ ] T012 [US2] Add `.env` to root `.gitignore`; `git rm --cached .env` (keep local file); confirm `.env.example` stays tracked.
- [ ] T013 [US2] Rotate `JUKEBOX_SESSION_SECRET`: generate a new value for `.env`/deployment secret; document in `deploy/k8s/README.md` and `specs/changes/010-hardening-and-polish/quickstart.md` (effect: one-time re-auth).
- [ ] T014 [P] [US2] Restrict CORS `allow_headers` to the SPA's actual headers (e.g. `content-type`) in `backend/app/main.py`/`config.py` while keeping `allow_credentials` + explicit origins.
- [ ] T015 [P] [US2] Add a backend test asserting the app boots and health/CSP behavior is unchanged with the tightened CORS headers (extend `backend/tests/test_health.py` or add a CORS test).

**Checkpoint**: Secrets remediated; CORS scoped.

---

## Phase 5: User Story 3 — Non-blocking I/O & scale-safe topology (P2)

**Goal**: Outbound HTTP off the event loop; single-replica pinned and documented.

**Independent Test**: Concurrency test shows no event-loop serialization; manifests pin `replicas: 1`; README documents the constraint.

### Tests for US3 ⚠️

- [ ] T016 [P] [US3] Add/extend `backend/tests/test_youtube_search.py` to assert search still returns expected results/errors after the async migration (regression), mocking the async client.
- [ ] T017 [P] [US3] Extend `backend/tests/test_oauth_google.py` to assert OAuth token/userinfo behavior and error codes unchanged after async migration.

### Implementation for US3

- [ ] T018 [P] [US3] Migrate `backend/app/services/youtube_search_service.py` outbound call off the event loop (per T002 decision); preserve 10 s timeout and `503` mapping.
- [ ] T019 [P] [US3] Migrate `backend/app/services/youtube_meta.py` (oEmbed + `videos.list`) similarly; preserve error mapping.
- [ ] T020 [P] [US3] Migrate `backend/app/services/google_oauth_service.py` token/userinfo calls similarly; preserve `oauth_error=` mappings.
- [ ] T021 [US3] Set `replicas: 1` in `deploy/k8s/backend.yaml`.
- [ ] T022 [US3] Document single-replica requirement (SSE fan-out, rate limiting, key rotation, quota counters are per-process) in `deploy/k8s/README.md`.

**Checkpoint**: Responsive under concurrency; topology matches runtime assumptions.

---

## Phase 6: User Story 4 — Backend robustness fixes (P2)

**Goal**: Token lookup, rate-limiter memory, quota reset, FK integrity, submit validation all correct.

**Independent Test**: Targeted tests per fix pass.

### Tests for US4 ⚠️

- [ ] T023 [P] [US4] `backend/tests/test_tokens.py`/`test_auth.py`: token exchange resolves by prefix with ≤1 hash comparison; prefix-less legacy token is rejected.
- [ ] T024 [P] [US4] `backend/tests/test_youtube_search.py`: rate-limiter evicts expired windows (bucket count bounded after window passes).
- [ ] T025 [P] [US4] `backend/tests/test_youtube_api_key_usage.py`: quota-day reset reflected on the next read across the Pacific boundary with no intervening traffic.
- [ ] T026 [P] [US4] `backend/tests/test_migrations_0008.py`: orphan `submitted_by_participant_id` set null; FK rejects non-existent participant.
- [ ] T027 [P] [US4] `backend/tests/test_participant_submit.py`/`test_queue.py`: operator dev-submit and participant submit reject invalid references identically.

### Implementation for US4

- [ ] T028 [US4] Migration `backend/alembic/versions/0007_api_token_prefix.py`: add indexed non-secret prefix column to `api_tokens` (downgrade drops it).
- [ ] T029 [US4] Store prefix on token create and verify by prefix in `backend/app/security.py` + `backend/app/routers/tokens.py`/`auth.py`; reject prefix-less rows. Update `backend/app/models.py`.
- [ ] T030 [P] [US4] Add eviction of expired/idle windows in `backend/app/services/search_rate_limiter.py`.
- [ ] T031 [P] [US4] Make Pacific quota-day reset deterministic on read/increment in `backend/app/services/youtube_api_key_usage_service.py`.
- [ ] T032 [US4] Migration `backend/alembic/versions/0008_queue_submitter_fk.py`: null orphans then add FK `queue_entries.submitted_by_participant_id` → `participants.id`; reversible. Update `backend/app/models.py`.
- [ ] T033 [US4] Unify submit metadata strictness (use strict validation on operator `dev-submit`) in `backend/app/services/queue_service.py`/`youtube_meta.py`.

**Checkpoint**: Robustness defects closed with tests.

---

## Phase 7: User Story 5 — Editable event configuration (P2)

**Goal**: `GET/PUT /api/event-config` + admin "Evento" editor + theme wiring (`default`).

**Independent Test**: Edit all fields in `/admin`, save, and the kiosk reflects them (incl. theme) via SSE.

### Tests for US5 ⚠️

- [ ] T034 [P] [US5] `backend/tests/test_event_config.py`: GET returns current config; PUT persists; invalid values → 422; participant/anon → 401; PUT bumps revision and broadcasts `state`.
- [ ] T035 [P] [US5] `backend/tests/test_auth_policy.py`: add `GET`/`PUT /api/event-config` to the canonical operator-protected route list.
- [ ] T036 [P] [US5] `frontend` spec for the event-config form (load, validation message, successful save) in `frontend/src/app/admin/`.

### Implementation for US5

- [ ] T037 [US5] Add `backend/app/routers/event_config.py` (`GET`/`PUT /api/event-config`, operator session, validation, persist, bump revision, broadcast `state`); register in `backend/app/main.py`.
- [ ] T038 [P] [US5] Add `frontend/src/app/models/event-config.ts` and `frontend/src/app/services/event-config.service.ts` (`getConfig`, `updateConfig`).
- [ ] T039 [US5] Replace the "próximamente" placeholder in `frontend/src/app/admin/admin.component.html`/`.ts` with an editable Spanish form (Nombre, Subtítulo, Altura, Tema, Canciones visibles) + validation + success/error copy.
- [ ] T040 [P] [US5] Apply `event_config.theme` (`default` only; unknown → default) on `frontend/src/app/display/display.component.*` (from `state`) and `frontend/src/app/participate/participate.component.*` (from participant state — depends on T057).
- [ ] T057 [US5] Add a `theme` field to `ParticipantStateResponse` (echo of `event_config.theme`) in `backend/app/schemas.py` + the `GET /api/participant/state` handler, so `/participar` has a data path for the theme (FR-019). Extend `backend/tests/test_participant_auth.py` (or state test) to assert `theme` is present. No migration.

**Checkpoint**: Event config editable end-to-end; theme field live on kiosk and participar.

---

## Phase 8: User Story 6 — Frontend visual/UX polish (P3)

**Goal**: Responsive kiosk, per-row moderation, QR caching, dead-dep removal, 404/loading, dev-affordance gating.

**Independent Test**: Kiosk renders 720p–4K without clipping; one-row moderation busy; QR stable; Material/CDK gone; 404 page present.

- [ ] T041 [US6] Make kiosk layout responsive in `frontend/src/app/display/display.component.html`/`.css`: `app_height_px` as target (CSS var) without a hard clipping `max-height`; verify 720p/1080p/2160p.
- [ ] T042 [P] [US6] Per-row moderation busy state (keyed by entry id) in `frontend/src/app/admin/admin.component.ts`/`.html`, replacing the single `moderationBusy` flag.
- [ ] T043 [P] [US6] Cache QR and regenerate only on URL change in `frontend/src/app/display/qr-panel.component.ts`.
- [ ] T044 [P] [US6] Remove `@angular/material` and `@angular/cdk` from `frontend/package.json` (+ lockfile); confirm build within budget.
- [ ] T045 [P] [US6] Add `frontend/src/app/not-found/not-found.component.*` (Spanish 404) and point `**` in `frontend/src/app/app.routes.ts` to it; add loading states on `/admin` and `/participar` fetches.
- [ ] T046 [P] [US6] Gate `AuthService.resetForTesting`, `ParticipantService.devAuthAsync`, and the dev-auth button so they are unreachable in production builds.

**Checkpoint**: SPA finished and dependency-lean.

---

## Phase 9: User Story 7 — Test coverage for changed behavior (P3)

**Goal**: Fill the frontend coverage gap; ensure backend changed-behavior tests are green.

**Independent Test**: New guard/interceptor/SSE specs pass; full backend suite passes.

- [ ] T047 [P] [US7] `frontend/src/app/auth.guard.spec.ts`: `authGuard`, `guestGuard`, `displayGuard` behavior.
- [ ] T048 [P] [US7] `frontend/src/app/auth.interceptor.spec.ts`: 401 branching by route (`/`, `/participar`, `/login`, other).
- [ ] T049 [P] [US7] SSE service spec (`display-state.service.spec.ts` or extend `participant-state.service.spec.ts`) covering event handling/reconnect.
- [ ] T050 [US7] Run full `pytest backend/tests` and `npm --prefix frontend run test`; fix regressions surfaced.

**Checkpoint**: Coverage raised; suites green.

---

## Phase 10: User Story 8 — SDD & repository hygiene (P3)

**Goal**: Contracts/manifest/agent docs accurate; toolchain de-duplicated.

**Independent Test**: Contracts include 009/010, no stale "Planned event-config"; single `.specify/`; manifest/AGENTS reflect 010.

- [ ] T051 [US8] Reconcile active-contract headers/change history to include 009 and 010; remove `## Planned (007+)` event-config from `specs/contracts/backend-api/contract.md`; document SSE isolation + event-config as active in all three contracts.
- [ ] T052 [P] [US8] Remove the duplicated `.specify/.specify/` directory (keep single canonical `.specify/`); verify no scripts reference the nested path.
- [ ] T053 [P] [US8] Update `AGENTS.md` "Active SDD work" and `specs/manifest.yml` (`010` status → `implemented` on completion; `active.change` → null or next).

**Checkpoint**: SDD source-of-truth consistent.

---

## Phase 11: Closure — Regression & validation

- [ ] T054 Author `specs/changes/010-hardening-and-polish/quickstart.md` with manual validation steps (SSE isolation, secret rotation/token reissue, event-config edit reflected on kiosk, kiosk resolutions, single-replica note, and a responsiveness check under concurrent searches for SC-003 since it has no dedicated automated assertion).
- [ ] T055 Run `scripts/compose-smoke.sh` and `scripts/k8s-validate.sh`; confirm `/api/health`, CSP, login, kiosk still pass (regression FR-031/SC-011).
- [ ] T056 Flip `specs/manifest.yml` change `010` status to `implemented` and update `AGENTS.md` once all checkpoints pass.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)** → no deps.
- **Foundational (P2)** → after Setup; blocks US1 and US5 (SSE routing + event-config schemas).
- **US1, US2 (P1)** → after Foundational (US2 mostly independent of Foundational; can start after Setup).
- **US3, US4, US5 (P2)** → after Foundational; independent of each other.
- **US6, US7, US8 (P3)** → after their respective feature stories land (US6 depends on US5 for theme/editor; US7 depends on US1/US5 for new tests; US8 after implementation).
- **Closure (Phase 11)** → last.

### Within a story

- Tests first (must fail) → migrations/models → services → routers/endpoints → frontend → integration.

### Parallel opportunities

- T001–T003 (Setup) in parallel.
- Async migrations T018/T019/T020 in parallel (different files).
- Robustness fixes T030/T031 in parallel; migrations T028 and T032 sequential only if they touch `models.py` together (coordinate the shared file).
- Frontend polish T042–T046 largely parallel (different files).
- All `[P]` test tasks within a story in parallel.

### Suggested increment order (MVP → complete)

1. Setup + Foundational.
2. **US1 (SSE isolation)** — security MVP; stop & validate.
3. **US2 (secrets/CORS)** — security.
4. US3 (async + topology) → US4 (robustness) → US5 (event-config).
5. US6 (polish) → US7 (tests) → US8 (hygiene) → Closure.

## Notes

- `[P]` = different files, no dependency. Coordinate edits to shared files (`models.py`, `admin.component.*`, `main.py`) to avoid conflicts.
- Verify each test fails before implementing its behavior.
- Commit per task or logical group; keep each user story independently demoable.
- Do not expand into review section 4 (new features) — out of scope for 010.
