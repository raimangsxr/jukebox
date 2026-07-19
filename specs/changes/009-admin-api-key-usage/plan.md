# Implementation Plan: Admin YouTube API Key Usage

**Branch**: `006-admin-api-key-usage` (git) | **Change id**: `009-admin-api-key-usage` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/009-admin-api-key-usage/spec.md`

## Summary

Expose per-key YouTube Data API daily usage (used / remaining of 100) to operators on `/admin` in a dedicated **Uso de API Keys** section. Backend persists exact attempt-based counters in PostgreSQL, increments on every outbound pool-attributed request (search + `videos.list` metadata), syncs exhaustion when Google returns quota errors, and broadcasts updates on the existing SSE stream (`event: api_key_usage`). Frontend loads an initial snapshot via REST and merges live updates without polling.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL; Angular standalone, TailwindCSS; existing `YoutubeApiKeyPool` (008); SSE hub (`sse_hub.py`)

**Storage**: New table `youtube_api_key_daily_usage` (Alembic `0006`); keyed by `key_hash` + Pacific `quota_day`

**Testing**: pytest (`test_youtube_api_key_usage.py`, extend `test_youtube_search.py`, SSE helpers); admin component smoke via build; regression 004–008

**Target Platform**: Docker Compose / K8s; operator `/admin`

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Initial usage list within **10s** of admin load (SC-001); SSE update within **5s** of attributed request (SC-001)

**Constraints**: Operator-only read; never expose full API keys; attempt-based counting; Pacific midnight reset; Spanish UI; no HTTP polling; 100 uses/key/day cap

**Scale/Scope**: 1 migration; 1 REST endpoint; 1 SSE event type; 1 usage service; pool/search/meta hooks; admin UI section; contract deltas for `backend-api` + `app-core`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted |
| V. Tests for changed behavior | Pass | `test_youtube_api_key_usage.py` + SSE + search increment tests |
| VI. Sibling conventions | Pass | `/api/*` prefix, operator session, Spanish UI, SSE on `/api/events/stream` |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/changes/009-admin-api-key-usage/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── contracts/contract-deltas.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 0006_youtube_api_key_daily_usage.py   # new
├── app/
│   ├── models.py                             # + YoutubeApiKeyDailyUsage
│   ├── schemas.py                            # + ApiKeyUsageItem, ApiKeyUsageListResponse
│   ├── routers/
│   │   └── youtube.py                        # + GET /api/youtube/api-keys/usage
│   ├── services/
│   │   ├── youtube_api_key_pool.py           # integrate exhaustion with usage service
│   │   ├── youtube_api_key_usage_service.py  # persist, increment, reset, broadcast (new)
│   │   ├── youtube_search_service.py         # record attempt before fetch
│   │   ├── youtube_meta.py                   # record attempt before fetch
│   │   └── sse_hub.py                        # + broadcast_api_key_usage
│   └── main.py
└── tests/
    └── test_youtube_api_key_usage.py         # new

frontend/src/app/
├── admin/
│   ├── admin.component.ts                    # usage section state + SSE merge
│   ├── admin.component.html                  # "Uso de API Keys" table
│   └── admin.component.css                   # optional exhausted badge styles
├── models/
│   └── youtube-api-key-usage.ts              # DTO types (new)
└── services/
    └── display-state.service.ts              # listen for api_key_usage SSE events
```

**Structure Decision**: Extend existing `youtube` router and SSE hub; admin reuses `DisplayStateService` EventSource (already started on `/admin`) for `api_key_usage` events.

## Phase 0 — Research

See [research.md](./research.md). Resolved: PostgreSQL persistence, `key_hash` identity, attempt-based increment, SSE event shape, REST snapshot endpoint, Pacific reset, pool integration points.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **Migration `0006`**: table `youtube_api_key_daily_usage` — `key_hash` (SHA-256 hex), `quota_day` (date, Pacific), `used_count` (int 0–100), `exhausted` (bool), `updated_at`; unique `(key_hash, quota_day)`; index on `quota_day`.

2. **`youtube_api_key_usage_service`** (module functions or small class):
   - `pacific_quota_day(now) -> date` — shared with pool reset logic
   - `key_hash(api_key: str) -> str` — SHA-256 of raw key
   - `ensure_rows_for_configured_keys(db)` — upsert rows for keys in `JUKEBOX_YOUTUBE_API_KEYS` for current quota day
   - `roll_quota_day_if_needed(db)` — when Pacific date advances, counters logically reset (new rows at 0 or delete old day rows)
   - `record_attempt(db, api_key) -> ApiKeyUsageListResponse` — **increment before outbound call**; cap at 100; set `exhausted` at 100; call `broadcast_api_key_usage`
   - `mark_google_exhausted(db, api_key)` — set `used_count=100`, `exhausted=true`, broadcast
   - `build_usage_list(db) -> ApiKeyUsageListResponse` — ordered by config index; masked labels `Clave {n}` + `…{last4}`; include `next_reset_at` (next Pacific midnight ISO)
   - Use `SELECT … FOR UPDATE` on row increment for concurrency safety

3. **Pool / fetch integration**:
   - **`youtube_api_key_pool.py`**: `acquire_key()` skips keys with `exhausted=true` in DB for current Pacific quota day; keep in-memory `exhausted_until` in sync
   - `youtube_search_service`: after `acquire_key()`, call `record_attempt` then `_fetch_with_key`; on 403 quota → `mark_google_exhausted` + `pool.mark_exhausted`
   - `youtube_meta.fetch_youtube_duration_sec`: same pattern per attempt in loop
   - `YoutubeApiKeyPool.mark_exhausted` delegates exhaustion flag to usage service when DB session available, or usage service called by callers (prefer explicit calls from search/meta to keep pool free of DB deps)

4. **`sse_hub`**: add `format_api_key_usage_event` + `broadcast_api_key_usage(payload)` mirroring `broadcast_notification`.

5. **`routers/youtube.py`**: `GET /api/youtube/api-keys/usage` — `CurrentUser` (operator session) → `build_usage_list`.

6. **Daily reset broadcast**: `roll_quota_day_if_needed` emits SSE when day rolls (first request after midnight Pacific).

### Frontend design

1. **Models**: `ApiKeyUsageItem`, `ApiKeyUsageListResponse` (`keys[]`, `next_reset_at`, `daily_limit`).

2. **`DisplayStateService`**: add `apiKeyUsage$` / `apiKeyUsageSnapshot`; on SSE `api_key_usage` event parse and emit; kiosk/display clients ignore unused observable.

3. **`AdminComponent`**:
   - On init: `GET /api/youtube/api-keys/usage` for initial snapshot
   - Subscribe to `displayState.apiKeyUsage$` for live updates
   - New section **between Moderación and Evento** with table: Clave, Usados, Restantes, Estado (Activa / Agotada)
   - Header note: `Próximo reinicio: {next_reset_at}` formatted in Spanish locale
   - Empty state: `No hay API keys de YouTube configuradas.`

4. **No new EventSource** — reuse admin's existing `displayState.start()` connection.

### API error / auth

| Case | Status |
|------|--------|
| Not operator session | 401 |
| Participant session | 401 |

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts + manifest

Merge contract deltas; set manifest `009` active.

### Phase B — Backend persistence + usage service

Migration, model, schemas, usage service, unit tests.

### Phase C — Integration hooks + SSE

Wire search/meta; sse_hub broadcast; router endpoint; SSE tests.

### Phase D — Frontend admin section

Models, DisplayStateService listener, admin template, Spanish copy.

### Phase E — Regression + closure

Quickstart; pytest + build; mark implemented.

## Risks

| Risk | Mitigation |
|------|------------|
| Multi-replica concurrent increments | Row-level lock (`FOR UPDATE`) on usage row |
| In-memory `exhausted_until` vs DB drift | On `mark_google_exhausted`, sync both pool and DB to 100 |
| Kiosk receives `api_key_usage` noise | Event ignored client-side; small payload |
| Key reorder in env | Display uses config order index; `key_hash` tracks same secret across reorder |
| SSE missed while admin offline | Initial GET on each `/admin` visit refreshes snapshot |

## Complexity Tracking

> No violations.
