---
description: "Task list for 008-youtube-text-search"
---

# Tasks: Participant YouTube Text Search

**Input**: Design documents from `specs/changes/008-youtube-text-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: SC-002/006/007/008 in `test_youtube_search.py`; SC-003 regression subset; Vitest in `participate.component.spec.ts` (active-path UX + result rows).

**Organization**: US1 includes full result rows (FR-005) and dual-path UX before MVP checkpoint; US2 adds distinguishability tests; US3 errors/limits; US4 regression.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Manifest + Contract Consolidation)

**Purpose**: Register change and merge contract deltas before code (Constitution II + IV)

- [x] T001 Verify `008-youtube-text-search` in `specs/manifest.yml` as `draft` with `active.change` and `context_pack` pointing to `specs/changes/008-youtube-text-search/context-pack.md`
- [x] T002 Update `specs/contracts/backend-api/contract.md` from `specs/changes/008-youtube-text-search/contracts/contract-deltas.md` (search endpoints, key pool, rate limits, error shapes; consolidate dual-path rules under one **Participate submit UX** subsection to avoid FR-003 drift)
- [x] T003 Update `specs/contracts/app-core/contract.md` from `specs/changes/008-youtube-text-search/contracts/contract-deltas.md` (dual-path UX, stacked layout, sticky footer, Spanish strings; same consolidated subsection as T002)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend search API, key pool, rate limiting, and route auth policy

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `youtube_api_keys`, `youtube_search_max_results`, and `youtube_search_min_query_length` to `backend/app/config.py` with `JUKEBOX_` prefix and key-list parser helper
- [x] T005 Add `SearchConfigResponse`, `SearchResultItem`, and `SearchResponse` to `backend/app/schemas.py`; extend `SubmitRequest` with optional `search_query` for `original_query=search:{query}` in `backend/app/services/queue_service.py` `submit_as_participant`
- [x] T006 Create `backend/app/services/youtube_api_key_pool.py` with round-robin `acquire_key()`, `mark_exhausted()` until Pacific midnight, and `has_available_key()`
- [x] T007 Create `backend/app/services/search_rate_limiter.py` with rolling 10-per-5-minute window per `participant_id`
- [x] T008 Create `backend/app/services/youtube_search_service.py` calling YouTube Data API `search.list` via urllib, parsing results, capping at `youtube_search_max_results`, and retrying on per-key quota exhaustion
- [x] T009 Create `backend/app/routers/youtube.py` with `GET /api/youtube/search/config` (public) and `GET /api/youtube/search` (participant auth, rate limit, service call)
- [x] T010 Register `youtube` router in `backend/app/main.py`
- [x] T011 [P] Extend `backend/tests/conftest.py` with fixtures to mock YouTube Data API HTTP responses and set `JUKEBOX_YOUTUBE_API_KEYS` for tests
- [x] T012 Extend `backend/tests/test_auth_policy.py` with `PUBLIC_PATHS_008` (`GET /api/youtube/search/config`) and participant-protected `GET /api/youtube/search`

**Checkpoint**: Backend search endpoints callable; auth policy matches contract

---

## Phase 3: User Story 1 — Search and Submit a Song (Priority: P1) 🎯 MVP

**Goal**: Signed-in participant searches, sees **title + thumbnail + channel** per row, selects a result, submits via sticky **Enviar canción**; stacked dual-path layout with active section highlight.

**Independent Test**: Sign in → search → distinguishable rows → select → **Enviar canción** → **Mis canciones** shows **Pendiente de revisión** with `original_query` reflecting search context.

### Tests for User Story 1

- [x] T013 [US1] Create `backend/tests/test_youtube_search.py` covering: `GET /api/youtube/search/config` enabled/disabled; `GET /api/youtube/search` 401 without session; happy path returns `SearchResultItem` list with mocked API; **max 10 results** when API returns more than `youtube_search_max_results` (FR-006)

### Implementation for User Story 1

- [x] T014 [P] [US1] Add `SearchConfigResponse`, `SearchResultItem`, and `SearchResponse` interfaces in `frontend/src/app/models/youtube-search.ts`
- [x] T015 [US1] Extend `frontend/src/app/services/participant.service.ts` with `getSearchConfig()`, `searchYoutube(q)`, `submitSong(urlOrId, searchQuery?)` (optional `search_query` body), and initial `mapSearchError()`
- [x] T016 [US1] Refactor `frontend/src/app/participate/participate.component.html` to **stacked layout**: search block above URL block (both always visible); remove inline URL submit button
- [x] T017 [US1] Extend `frontend/src/app/participate/participate.component.ts` with search state (`searchQuery`, `searchResults`, `selectedResult`, `searchLoading`), **Buscar** + **Enter** handlers, and row selection setting `activePath='search'`
- [x] T018 [US1] Implement search result list rows in `frontend/src/app/participate/participate.component.html` with **title**, **thumbnail** (`<img>`), and **channel** per `FR-005`
- [x] T019 [US1] Add selected-row highlight and Spanish loading copy in `frontend/src/app/participate/participate.component.html` and `participate.component.ts` (`searchLoading` does not block vote/Mis canciones)
- [x] T020 [US1] Add sticky footer **Enviar canción** in `participate.component.html` and submit handler in `participate.component.ts` (search path → `submitSong(videoId, searchQuery)` passing optional `search_query` for `original_query`)
- [x] T021 [US1] Implement dual-path `activePath` (`'search' | 'url' | null`) in `participate.component.ts`: URL text edit activates URL path; focus alone does not switch; section highlight in `participate.component.html` and `participate.component.css`
- [x] T022 [US1] Add sticky footer and main content `padding-bottom` styles in `frontend/src/app/participate/participate.component.css` (`z-index` below notification toast per plan)
- [x] T023 [US1] Extend `backend/tests/test_youtube_search.py` with search-path submit via `POST /api/queue/submit` mirroring **006** cases for SC-002: pending limit (2), active own (1), duplicate active video, invalid metadata, and assert `original_query` starts with `search:` when submitted from search context
- [x] T024 [US1] Create `frontend/src/app/participate/participate.component.spec.ts` covering active-path UX: section highlight on URL edit vs row select; URL focus without edit does not switch path; sticky footer submits correct path
- [x] T025 [US1] Run `pytest backend/tests/test_youtube_search.py -k "config or search or submit"` and `npm --prefix frontend test -- participate.component.spec` and fix failures

**Checkpoint**: US1 — search + full result rows + submit + dual-path UX (MVP)

---

## Phase 4: User Story 2 — Understand Search Results (Priority: P1)

**Goal**: Confirm participants can distinguish recordings (multi- and single-result cases).

**Independent Test**: Search popular song → multiple distinguishable rows; single-result search still submittable.

### Tests for User Story 2

- [x] T026 [P] [US2] Extend `frontend/src/app/participate/participate.component.spec.ts` asserting result row renders title, thumbnail, and channel from mock `SearchResultItem`, and single-result list still enables submit when selected

**Checkpoint**: US2 — distinguishability validated in unit tests

---

## Phase 5: User Story 3 — Search Errors and Empty Results (Priority: P2)

**Goal**: Spanish feedback for short/whitespace-only query, special characters, empty results, rate limit, network failure, API unavailable; search disabled when no keys; failover transparent; URL submit always works.

**Independent Test**: Whitespace-only blocked → empty API → rate limit 429 → network 503 → all keys exhausted; URL submit succeeds throughout.

### Tests for User Story 3

- [x] T027 [US3] Extend `backend/tests/test_youtube_search.py` covering: `invalid search query` (422) for too-short and **whitespace-only** queries; `search rate limit exceeded` (429); empty `items[]`; **simulated `URLError`/timeout** → 503 `youtube search unavailable` (FR-009); single-key quota failover (SC-007); all keys exhausted (503, SC-008)

### Implementation for User Story 3

- [x] T028 [US3] Complete Spanish `mapSearchError()` strings in `frontend/src/app/services/participant.service.ts` per `contracts/contract-deltas.md`
- [x] T029 [US3] Load `getSearchConfig()` on participate bootstrap in `participate.component.ts`; show search block **disabled** with Spanish message when `enabled=false` in `participate.component.html`
- [x] T030 [US3] Add client-side min-length and **trim/whitespace-only** guard before API call; normalize special-character queries (pass through to API after trim); empty-results Spanish state in `participate.component.ts` and `participate.component.html`
- [x] T031 [US3] Display search API/network errors without blocking URL submit in `participate.component.ts`; ensure new search replaces prior result list (no list accumulation)
- [x] T032 [US3] Run `pytest backend/tests/test_youtube_search.py` and fix failures

**Checkpoint**: US3 — error/limit/failover paths covered

---

## Phase 6: User Story 4 — No Regression on Participate Flows (Priority: P1)

**Goal**: Voting, URL submit, Mis canciones SSE, and notification toasts unchanged after search UI.

**Independent Test**: Vote + URL submit + notification toast after search UI present; behaviors match 005–007.

### Tests for User Story 4

- [x] T033 [US4] Run `pytest backend/tests/test_votes.py backend/tests/test_participant_submit.py backend/tests/test_notifications.py backend/tests/test_sse.py backend/tests/test_auth_policy.py` regression subset with search routes enabled
- [x] T034 [US4] Verify URL-only submit path in `frontend/src/app/participate/participate.component.ts` matches 006 behavior when `activePath='url'` (same error mapping via `mapSubmitError`)
- [x] T035 [US4] Verify `frontend/src/app/participate/notification-toast.component.css` still displays above sticky submit footer (`z-index`); fix layout only if regression

**Checkpoint**: SC-003 regression guard passes

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full validation and change closure

- [x] T036 Run full `pytest backend/tests` with zero failures
- [x] T037 Run `npm --prefix frontend test` and `npm --prefix frontend run build` with zero errors
- [x] T038 Execute manual validation per `specs/changes/008-youtube-text-search/quickstart.md` including **SC-001** timing (search → submit → Mis canciones pending within **5 seconds** on local/staging Wi‑Fi)
- [x] T039 Mark change `implemented` in `specs/manifest.yml` and clear or update `active.change`
- [x] T040 Update implementation validation in `specs/changes/008-youtube-text-search/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — **includes FR-005 result rows before MVP checkpoint**
- **Phase 4 (US2)**: Depends on US1 (T018–T024)
- **Phase 5 (US3)**: Depends on Phase 2; frontend error UX depends on US1 (T015–T022)
- **Phase 6 (US4)**: Depends on US1–US3
- **Phase 7 (Polish)**: Depends on US1–US4

### User Story Dependencies

| Story | Depends on | Independent test without other stories |
|-------|------------|----------------------------------------|
| US1 | Foundational | Yes — pytest + Vitest + manual E2E submit |
| US2 | US1 result rows | Yes — Vitest distinguishability |
| US3 | Foundational + US1 frontend | Yes — pytest limits/failover/network |
| US4 | US1–US3 | Yes — regression tests |

### Parallel Opportunities

- **Phase 1**: T002 and T003 — different contract files
- **Phase 2**: T011 parallel with T004–T010; T012 after T010
- **Phase 3**: T014 parallel with T013; T024 parallel with T023 after T021
- **Phase 4**: T026 parallel with T032 (US3 backend tests) after US1
- **Phase 6**: T033, T034, T035 in parallel

### Parallel Example: User Story 1

```bash
# After Phase 2:
Task T013: backend/tests/test_youtube_search.py (initial)
Task T014: frontend/src/app/models/youtube-search.ts

# After T017:
Task T018: result rows (FR-005)
Task T019: loading state
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1–2 (T001–T012)
2. Complete Phase 3 US1 (T013–T025)
3. **STOP and VALIDATE**: quickstart Phase 1–2
4. Add US2 → US3 → US4 → Polish

### Incremental Delivery

1. Setup + Foundational → search API + auth policy ready
2. US1 → search + result rows + submit + dual-path UX (MVP)
3. US2 → distinguishability unit tests
4. US3 → errors, limits, failover, disabled state
5. US4 → regression
6. Polish → manifest closure

### Suggested MVP Scope

**T001–T025** (Setup + Foundational + US1).

---

## Notes

- No Alembic migration for 008
- Search submit uses existing `POST /api/queue/submit` with 11-char video id; `original_query` = `search:{query}` when submitting from search path
- `JUKEBOX_YOUTUBE_API_KEYS` comma-separated; never expose keys to clients
- Multi-replica: in-process rate limit and key pool state acceptable for v1 (research.md)
- Notification toast (`z-50`) must remain above sticky submit footer (`z-40`)
- Spanish UI strings in `contracts/contract-deltas.md`
- Mock YouTube API in tests — do not call live API in CI
