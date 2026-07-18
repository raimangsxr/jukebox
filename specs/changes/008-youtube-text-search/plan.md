# Implementation Plan: Participant YouTube Text Search

**Branch**: `005-youtube-text-search` (git) | **Change id**: `008-youtube-text-search` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/008-youtube-text-search/spec.md`

## Summary

Add YouTube Data API text search on `/participar` alongside existing URL submit (006). Backend: `GET /api/youtube/search` (participant auth, rate limit 10/5min, multi-key round-robin pool with quota failover), `GET /api/youtube/search/config`, reuse `POST /api/queue/submit` with video id from selected result. Frontend: stacked search + URL blocks, single active path with section highlight, sticky **Enviar canción** footer; search disabled gracefully when no keys.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (existing); Angular standalone, TailwindCSS, FormsModule; YouTube Data API v3 `search.list`; urllib HTTP (same as `youtube_meta.py`)

**Storage**: No new tables — ephemeral search results; existing `queue_entries` on submit

**Testing**: pytest (`test_youtube_search.py`, submit/vote/notification regression); Vitest for participate search UX; `npm run build`

**Target Platform**: Docker Compose / K8s; mobile `/participar` via QR

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Search + submit visible in Mis canciones within **5s** on event Wi‑Fi (SC-001); empty results feedback within **3s** (SC-004)

**Constraints**: Free-tier API quota only; 4–5 key pool; no ads in search UI; Spanish UI; dual submit paths equivalent; URL always available when authenticated

**Scale/Scope**: 2 new REST endpoints; 3 backend services; participate UI refactor (search block + sticky footer); contract deltas for `backend-api` + `app-core`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted |
| V. Tests for changed behavior | Pass | `test_youtube_search.py` + frontend specs + regression |
| VI. Sibling conventions | Pass | `/api/*` prefix, participant session, Spanish UI |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/changes/008-youtube-text-search/
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
├── app/
│   ├── config.py                          # + youtube_api_keys, search limits
│   ├── schemas.py                         # + SearchConfigResponse, SearchResultItem, SearchResponse
│   ├── routers/
│   │   └── youtube.py                     # GET /api/youtube/search, /config (new)
│   ├── services/
│   │   ├── youtube_api_key_pool.py        # round-robin + exhausted_until (new)
│   │   ├── youtube_search_service.py      # search.list + parse (new)
│   │   └── search_rate_limiter.py         # 10/5min per participant (new)
│   └── main.py                            # include youtube router
└── tests/
    └── test_youtube_search.py

frontend/src/app/
├── participate/
│   ├── participate.component.*            # dual-path UI, sticky footer, result rows
│   └── participate.component.spec.ts      # active-path UX + result row Vitest (US1/US2)
├── services/
│   └── participant.service.ts             # search API + error maps
└── models/
    └── youtube-search.ts                  # SearchResultItem types (new)
```

**Structure Decision**: New `youtube` router namespace; submit unchanged in `queue_service`; participate component owns dual-path UX state.

## Phase 0 — Research

See [research.md](./research.md). Resolved: YouTube Data API, key pool, rate limit, endpoints, urllib client, dual-path UX, testing.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **Settings**: `youtube_api_keys: str = ""` → parse to list; optional `youtube_search_max_results=10`, `youtube_search_min_query_length=2`
2. **`YoutubeApiKeyPool`**: module singleton; `acquire_key()` round-robin; `mark_exhausted(key)` until next Pacific midnight; `has_available_key()`
3. **`search_rate_limiter`**: `check_and_record(participant_id) -> bool`; prune timestamps older than 5 minutes
4. **`youtube_search_service.search_videos(query)`**:
   - Validate min length
   - Loop keys: build URL with `key=`, parse `items[]` → `SearchResultItem`
   - On quota error → next key; on success → return list (cap max results)
   - All keys fail → raise 503
5. **`routers/youtube.py`**:
   - `GET /search/config` → `{ enabled: bool(keys) }`
   - `GET /search?q=` → participant dep → rate limit → service → `SearchResponse`
6. **Submit path**: unchanged `POST /api/queue/submit` with video id; optional `original_query` body field or derive from session — **decision**: extend `SubmitRequest` with optional `search_query` used only to set `original_query=search:{query}` when present

### Frontend design

1. **Bootstrap**: `GET /api/youtube/search/config` on participate load
2. **Search block** (top): input, **Buscar**, loading/empty/error states, result list with thumbnails
3. **URL block** (below): existing input; remove inline submit button
4. **State**: `activePath`, `selectedResult`; URL `(ngModelChange)` sets `activePath='url'`; row click sets `activePath='search'`
5. **Section classes**: `[class.active-section]` on search/url containers per `activePath`
6. **Sticky footer**: fixed bottom bar with single **Enviar canción**; disabled when no valid active payload or `submitting`
7. **Submit handler**: if `activePath==='search'` → submit video id; if `'url'` → submit URL string
8. **Errors**: extend `mapSubmitError` / new `mapSearchError` for Spanish
9. **Layout**: `pb-24` (or similar) on main; toast `z-50` above footer `z-40`

### API error mapping (frontend)

| `detail` | Spanish |
|----------|---------|
| `search rate limit exceeded` | Has hecho demasiadas búsquedas… |
| `youtube search unavailable` | La búsqueda no está disponible ahora… |
| `invalid search query` | Escribe al menos 2 caracteres… |

(Existing submit errors unchanged.)

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts + manifest

Merge contract deltas; confirm manifest `008` active.

### Phase B — Backend search foundation

Config, schemas, key pool, rate limiter, search service, router, tests.

### Phase C — Frontend search UI

Models, participant service, participate template refactor (stacked layout, sticky footer, active path).

### Phase D — Integration + regression

Quickstart manual paths; full pytest + Vitest + build; 005–007 regression.

### Phase E — Closure

Mark tasks complete; manifest `implemented` after validation.

## Risks

| Risk | Mitigation |
|------|------------|
| Quota exhaustion mid-event | 4–5 key pool + participant rate limit; URL fallback always visible |
| Multi-replica rate limit / key state drift | Document per-process limits; defer Redis if needed |
| Sticky footer vs notification toast overlap | z-index + bottom padding; manual quickstart |
| Submit via search bypasses oEmbed title | `submit_as_participant` still runs `fetch_youtube_metadata_strict` |
| Google API response shape changes | Parse defensively; tests with fixture JSON |

## Complexity Tracking

> No violations.
