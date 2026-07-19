---
description: "Task list for 009-admin-api-key-usage"
---

# Tasks: Admin YouTube API Key Usage

**Input**: Design documents from `specs/changes/009-admin-api-key-usage/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: SC-002–SC-006 in `test_youtube_api_key_usage.py`; SSE emit tests; extend `test_youtube_search.py` for increment on search; regression via quickstart + `npm run build`.

**Organization**: US1 delivers operator usage list (REST + admin UI); US2 adds exact tracking + SSE live updates; US3 edge/empty states; Polish covers regression.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Manifest + Contract Consolidation)

**Purpose**: Register change and merge contract deltas before code (Constitution II + IV)

- [x] T001 Verify `009-admin-api-key-usage` in `specs/manifest.yml` as `draft` with `active.change` and `context_pack` pointing to `specs/changes/009-admin-api-key-usage/context-pack.md`
- [x] T002 Update `specs/contracts/backend-api/contract.md` from `specs/changes/009-admin-api-key-usage/contracts/contract-deltas.md` (`GET /api/youtube/api-keys/usage`, SSE `api_key_usage`, accounting rules, migration 0006, test list)
- [x] T003 Update `specs/contracts/app-core/contract.md` from `specs/changes/009-admin-api-key-usage/contracts/contract-deltas.md` (Uso de API Keys section, Spanish copy, DisplayStateService SSE merge)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Persistence, usage service core, SSE broadcast plumbing, auth policy

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create Alembic migration `backend/alembic/versions/0006_youtube_api_key_daily_usage.py` for table `youtube_api_key_daily_usage` per `data-model.md` (unique `key_hash` + `quota_day`)
- [x] T005 Add `YoutubeApiKeyDailyUsage` SQLAlchemy model to `backend/app/models.py`
- [x] T006 Add `ApiKeyUsageItem` and `ApiKeyUsageListResponse` Pydantic schemas to `backend/app/schemas.py`
- [x] T007 Create `backend/app/services/youtube_api_key_usage_service.py` with `pacific_quota_day()`, `next_pacific_midnight()`, `key_hash()`, `ensure_rows_for_configured_keys()`, `roll_quota_day_if_needed()`, `build_usage_list()`, `record_attempt()` (FOR UPDATE increment), and `mark_google_exhausted()` (force 100/0)
- [x] T008 Extend `backend/app/services/youtube_api_key_pool.py` so `acquire_key()` skips keys marked `exhausted` in DB for the current Pacific quota day (keep in-memory `exhausted_until` in sync via `mark_exhausted` / usage service)
- [x] T009 Add `format_api_key_usage_event()` and `broadcast_api_key_usage()` to `backend/app/services/sse_hub.py`
- [x] T010 [P] Extend `backend/tests/conftest.py` with helpers to set `JUKEBOX_YOUTUBE_API_KEYS` for multi-key usage tests and optional SSE `api_key_usage` collector
- [x] T011 Extend `backend/tests/test_auth_policy.py` with operator-only `GET /api/youtube/api-keys/usage` (401 for unauthenticated and participant session)

**Checkpoint**: Usage service builds masked list from DB; SSE formatter ready; migration applies

---

## Phase 3: User Story 1 — View Daily Usage per API Key (Priority: P1) 🎯 MVP

**Goal**: Operator sees **Uso de API Keys** table with usados/restantes/límite, masked identifiers, and próximo reinicio label.

**Independent Test**: Sign in on `/admin` → section shows each configured key with counts matching `GET /api/youtube/api-keys/usage`; no full secrets in UI or API.

### Tests for User Story 1

- [x] T012 [US1] Create `backend/tests/test_youtube_api_key_usage.py` covering: `GET /api/youtube/api-keys/usage` 401 without operator session; happy path returns ordered `keys[]` with masked suffix only; `daily_limit=100`; `next_reset_at` present; empty `keys` when no `JUKEBOX_YOUTUBE_API_KEYS`

### Implementation for User Story 1

- [x] T013 [US1] Add `GET /api/youtube/api-keys/usage` to `backend/app/routers/youtube.py` with `CurrentUser` dep calling `build_usage_list(db)`
- [x] T014 [P] [US1] Add `ApiKeyUsageItem` and `ApiKeyUsageListResponse` interfaces in `frontend/src/app/models/youtube-api-key-usage.ts`
- [x] T015 [US1] Add **Uso de API Keys** section to `frontend/src/app/admin/admin.component.html` between **Moderación** and **Evento** with table columns Clave, Usados, Restantes, Límite, Estado and global **Próximo reinicio** label
- [x] T016 [US1] Load usage snapshot via `GET /api/youtube/api-keys/usage` in `frontend/src/app/admin/admin.component.ts` on init; store in component state; Spanish `load_error` on failure
- [x] T017 [US1] Render masked `label` + `masked_suffix`, counts, and **Activa**/**Agotada** status in `frontend/src/app/admin/admin.component.html` and `admin.component.ts`
- [x] T018 [US1] Run `pytest backend/tests/test_youtube_api_key_usage.py -k "usage or auth"` and fix failures

**Checkpoint**: US1 — static usage list visible in admin (MVP without live SSE)

---

## Phase 4: User Story 2 — Real-Time Usage Updates (Priority: P1)

**Goal**: Exact attempt-based tracking on search/metadata calls; admin table updates via SSE within 5s without polling.

**Independent Test**: `/admin` open → participant search → correct key `used_count` +1 via `api_key_usage` SSE; counts survive backend restart.

### Tests for User Story 2

- [x] T019 [US2] Extend `backend/tests/test_youtube_api_key_usage.py` covering: `record_attempt` increments by 1 per outbound send; failed HTTP after send still increments; at 100 sets `exhausted`; persistence across new DB session (restart simulation)
- [x] T020 [US2] Extend `backend/tests/test_youtube_api_key_usage.py` with SSE `api_key_usage` emit after increment using `collect_sse_events_after` pattern from `backend/tests/conftest.py`
- [x] T021 [US2] Extend `backend/tests/test_youtube_search.py` asserting search request increments usage for the acquired key
- [x] T022 [US2] Extend `backend/tests/test_participant_submit.py` (or `test_youtube_api_key_usage.py`) asserting `fetch_youtube_duration_sec` metadata path increments usage for the acquired key (FR-002)
- [x] T023 [US2] Extend `backend/tests/test_youtube_search.py` asserting 422 invalid query and 429 rate limit do **not** increment any key usage (FR-003)

### Implementation for User Story 2

- [x] T024 [US2] Wire `record_attempt(db, api_key)` before outbound HTTP in `backend/app/services/youtube_search_service.py`; on 403 quota call `mark_google_exhausted()` and `pool.mark_exhausted()`; pass `db` session into search path from router
- [x] T025 [US2] Wire `record_attempt(db, api_key)` before outbound HTTP in `backend/app/services/youtube_meta.py` `fetch_youtube_duration_sec()` with quota-exhausted sync
- [x] T026 [US2] Call `broadcast_api_key_usage()` from `record_attempt`, `mark_google_exhausted`, and `roll_quota_day_if_needed` in `backend/app/services/youtube_api_key_usage_service.py`
- [x] T027 [US2] Extend `frontend/src/app/services/display-state.service.ts` with `apiKeyUsage$` / snapshot; listen for SSE `api_key_usage` events on existing `EventSource` (ignore on kiosk)
- [x] T028 [US2] Subscribe `frontend/src/app/admin/admin.component.ts` to `displayState.apiKeyUsage$` and merge into usage table without manual refresh
- [x] T029 [US2] Run `pytest backend/tests/test_youtube_api_key_usage.py backend/tests/test_youtube_search.py backend/tests/test_participant_submit.py -k "usage or increment or sse or rate"` and fix failures

**Checkpoint**: US2 — live SSE updates + exact tracking on API activity

---

## Phase 5: User Story 3 — Empty and Edge States (Priority: P2)

**Goal**: Spanish empty state, exhausted rows at 100/0 (including Google quota-exhausted), new keys appear at 0/100 on reload.

**Independent Test**: No keys → empty message; mocked quota-exhausted → 100/0 Agotada; add key to env → reload shows 0/100.

### Tests for User Story 3

- [x] T030 [US3] Extend `backend/tests/test_youtube_api_key_usage.py` covering: `mark_google_exhausted` when local count &lt; 100 sets `used_count=100`; failover increments both keys (+1 each); Pacific quota-day roll resets counts (mock or freeze time)

### Implementation for User Story 3

- [x] T031 [US3] Add Spanish empty state `No hay API keys de YouTube configuradas.` in `frontend/src/app/admin/admin.component.html` when `keys.length === 0`
- [x] T032 [US3] Add visual **Agotada** badge styling for exhausted rows in `frontend/src/app/admin/admin.component.css` (status text from T017)
- [x] T033 [US3] Ensure `ensure_rows_for_configured_keys()` in `backend/app/services/youtube_api_key_usage_service.py` creates 0/100 rows for newly added keys and omits removed keys from `build_usage_list()` (edge case: key removed from config)
- [x] T034 [US3] Run `pytest backend/tests/test_youtube_api_key_usage.py` and fix failures

**Checkpoint**: US3 — edge states and exhaustion display complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression, build, manual validation, closure

- [x] T035 Run full regression: `pytest backend/tests/test_youtube_api_key_usage.py backend/tests/test_youtube_search.py backend/tests/test_sse.py backend/tests/test_notifications.py backend/tests/test_participant_submit.py`
- [x] T036 Run `npm --prefix frontend run build` and fix any compile errors
- [x] T037 Execute manual validation per `specs/changes/009-admin-api-key-usage/quickstart.md` including **SC-001** timing checks (10s load, 5s SSE) in Phases 1–2
- [x] T038 Update `specs/changes/009-admin-api-key-usage/spec.md` status to **Implemented** and set `specs/manifest.yml` change `009-admin-api-key-usage` status to `implemented` after validation passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on Phase 2; integrates with US1 admin UI (T027–T028 after T015–T017)
- **US3 (Phase 5)**: Depends on US1 UI shell; tests overlap US2 service — run after US2 backend hooks
- **Polish (Phase 6)**: Depends on US1–US3

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | Foundational | REST + admin table, masked keys, reset label |
| US2 | Foundational + US1 UI | SSE increment on search, persistence |
| US3 | US1 + US2 | Empty/exhausted/new-key edge cases |

### Parallel Opportunities

- **Phase 1**: T002 and T003 [sequential on same contracts — do T002 then T003]
- **Phase 2**: T010 parallel with T004–T009 after T006 schemas exist
- **Phase 3**: T014 parallel with T013
- **Phase 4**: T019–T023 test files parallel; T024 and T025 parallel (different service files)
- **Phase 5**: T031–T032 parallel (HTML vs CSS)

---

## Parallel Example: User Story 2

```bash
# Backend integration hooks in parallel:
# T024 — youtube_search_service.py
# T025 — youtube_meta.py

# Tests in parallel after service exists:
# T019 — increment + persistence tests
# T020 — SSE emit tests
# T021 — search increment test
# T022 — metadata increment test
# T023 — no-increment on 422/429 test
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Operator sees usage table with correct masked data
5. Demo before enabling live tracking

### Incremental Delivery

1. Setup + Foundational → persistence layer ready
2. US1 → admin usage snapshot (MVP)
3. US2 → exact tracking + SSE (full feature value)
4. US3 → edge states polish
5. Polish → regression + manifest closure

### Suggested MVP Scope

**User Story 1** (Phases 1–3): delivers visible quota dashboard; US2 required for “exact” and real-time requirements from spec.

---

## Notes

- Never return full API key in REST or SSE payloads (SC-006)
- Attempt increment happens **before** `urllib` send (clarify session)
- Reuse existing `/api/events/stream` — no second EventSource on admin
- `JUKEBOX_YOUTUBE_API_KEYS` remains deployment-only; no admin edit UI
- Pool skips DB-exhausted keys via T008 (`youtube_api_key_pool.py`)
