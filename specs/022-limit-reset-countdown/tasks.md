---
description: "Task list for 022-limit-reset-countdown"
---

# Tasks: Contador de reinicio de límites en participación

**Input**: Design documents from `specs/022-limit-reset-countdown/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Backend `test_limit_windows.py` + updates to `test_votes.py` / `test_youtube_search.py` / `test_participant_submit.py`; FE `limit-countdown.util.spec.ts`, `participant-limits.util.spec.ts`, `participate.component.spec.ts`; manual quickstart T032 (constitution V for countdown UI).

**Organization**: Grouped by user story (US1–US3). All stories P1. Depends on **016-participant-limits-ux** (limits ENV + participate labels).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US3)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [X] T001 [P] Merge `specs/022-limit-reset-countdown/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (fixed-window limits + `ParticipantStateResponse` fields + participate countdown UI).
- [X] T002 Verify `specs/manifest.yml` has change `022-limit-reset-countdown` (`status: planned`, `modifies: backend-api, app-core`) and `active.change` / `active.context_pack` point to this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Migration, shared limit-window service, API schema/types, countdown utilities.

**⚠️ CRITICAL**: No user story UI work can begin until T007 stub is in place; **real** limit values required before T017/T023 (see T007 note).

- [X] T003 Create Alembic migration in `backend/alembic/versions/` adding `participants.votes_quota_reset_at`, `participants.searches_quota_reset_at` (nullable timestamptz) and `participant_searches` table per [data-model.md](./data-model.md).
- [X] T004 Add `ParticipantSearch` model and `votes_quota_reset_at` / `searches_quota_reset_at` columns on `Participant` in `backend/app/models.py`.
- [X] T005 Implement `backend/app/services/limit_window_service.py` — fixed window helpers; **`WINDOW` duration from `get_settings()`** (same 10-minute deployment config as `JUKEBOX_MAX_*` limits per FR-003, not a hardcoded-only constant); expire/clear `*_quota_reset_at`, `remaining(max, used, ends_at)`, start window only at full quota. Document in module/tests: `reset_at` set on first full-quota consume, cleared on expiry (aligns spec FR-004 with contract countdown rule).
- [X] T006 Extend `ParticipantStateResponse` in `backend/app/schemas.py` with `searches_remaining`, `votes_quota_reset_at`, `searches_quota_reset_at` (optional ISO datetimes).
- [X] T007 Wire limit fields in `backend/app/services/state_service.py` `build_participant_state_response()` — **stub OK in Phase 2** (`searches_remaining` = max, `*_quota_reset_at` = null). **Before T017/T023**: must call real `vote_service` / search limit helpers (after T015 and T021) so UI never binds against stub values.
- [X] T008 [P] Add `frontend/src/app/limit-countdown.util.ts` — `secondsUntil(isoEndsAt)`, `formatCountdownMmSs(seconds)`, `shouldShowQuotaCountdown(resetAt)` (canonical names per plan/contracts).
- [X] T009 [P] Add `frontend/src/app/limit-countdown.util.spec.ts` — MM:SS formatting, past/future reset_at, zero boundary.
- [X] T010 [P] Extend `frontend/src/app/models/jukebox-state.ts` `ParticipantStateResponse` with `searches_remaining`, `votes_quota_reset_at`, `searches_quota_reset_at`.
- [X] T011 [P] Update `frontend/src/app/participant-limits.util.ts` — `votesRemainingLabel(remaining, max, resetAt?)` and new `searchesRemainingLabel(remaining, max, resetAt?)` with «Cupo completo en MM:SS» via `formatCountdownMmSs` when active; remove «cada 10 min» when no window.
- [X] T012 [P] Add `frontend/src/app/participant-limits.util.spec.ts` — label copy for full quota, active window, limit-exceeded coherence with `resetAt` (FR-009), and no countdown cases.

**Checkpoint**: Migration applies; types and utils ready; state endpoint returns **real** limits before participate UI tasks.

---

## Phase 3: User Story 1 — Contador de reinicio de votos (Priority: P1) 🎯 MVP

**Goal**: Header shows live vote countdown from first vote at full quota; fixed window does not extend on second vote.

**Independent Test**: Full votes → no countdown → cast one vote → «X de Y votos disponibles · Cupo completo en MM:SS» in header → ticks down → at expiry full quota restored (quickstart Phases 1–3).

### Tests for US1 (write first, must fail) ⚠️

- [X] T013 [P] [US1] Add vote fixed-window tests in `backend/tests/test_limit_windows.py` — first vote at full quota sets `votes_quota_reset_at`; **second vote within window keeps same `votes_quota_reset_at` instant**; expired window restores max; invalid vote does not start window.
- [X] T014 [P] [US1] Update `backend/tests/test_votes.py` for fixed-window semantics (replace rolling-window expectations).

### Implementation for US1

- [X] T015 [US1] Refactor `backend/app/services/vote_service.py` — use `limit_window_service` + `participant.votes_quota_reset_at`; set anchor on first vote at full quota; `votes_remaining` from in-window count.
- [X] T016 [US1] Ensure `backend/app/routers/votes.py` `VoteResponse.state` includes `votes_quota_reset_at` and updated `votes_remaining` via `build_participant_state_response` (complete T007 for votes).
- [X] T017 [US1] Bind vote countdown in `frontend/src/app/participate/participate.component.html` header via `votesRemainingLabel()` using `state.votes_quota_reset_at` (**after T016**).
- [X] T018 [US1] In `frontend/src/app/participate/participate.component.ts`, pass `votes_quota_reset_at` into label helper; ensure vote success merges full `state` from `applyVoteResponse`.
- [X] T019 [P] [US1] Update `frontend/src/app/participate/participate.component.spec.ts` — smoke: header label includes «Cupo completo en» when mock `votes_quota_reset_at` is set; omits countdown when null.

**Checkpoint**: US1 independently testable per [quickstart.md](./quickstart.md) Phases 1–3 (auto-refresh at zero completed in US3).

---

## Phase 4: User Story 2 — Contador de reinicio de búsquedas (Priority: P1)

**Goal**: Search subsection shows «X de Y búsquedas disponibles» and countdown from first successful search at full quota; paste URL does not affect search window.

**Independent Test**: Full searches → label without countdown → one search → countdown appears → paste URL only leaves search countdown unchanged (quickstart Phase 4).

### Tests for US2 (write first, must fail) ⚠️

- [X] T020 [P] [US2] Add search fixed-window tests in `backend/tests/test_limit_windows.py` — `participant_searches` row on allowed search; window anchor; invalid query does not insert.
- [X] T021 [P] [US2] Add test in `backend/tests/test_participant_submit.py` (or `test_limit_windows.py`) — **URL submit does not** insert `participant_searches` or set `searches_quota_reset_at` (FR-010).
- [X] T022 [P] [US2] Update `backend/tests/test_youtube_search.py` and `backend/tests/test_rate_limiter.py` for DB-backed participant search limits (remove or adapt in-memory-only assumptions).

### Implementation for US2

- [X] T023 [US2] Refactor `backend/app/services/search_rate_limiter.py` to DB-backed fixed window using `participant_searches` + `participant.searches_quota_reset_at` (delegate to `limit_window_service`); keep operator/non-participant bypass in `backend/app/routers/youtube.py`.
- [X] T024 [US2] Expose `searches_remaining` and `searches_quota_reset_at` in `build_participant_state_response()` in `backend/app/services/state_service.py` (complete T007 for searches).
- [X] T025 [US2] Add searches quota label in `frontend/src/app/participate/participate.component.html` Buscar en YouTube subsection using `searchesRemainingLabel()` (**after T024**).
- [X] T026 [US2] In `frontend/src/app/participate/participate.component.ts`, refresh search limit display after successful `runSearch()` from updated participant state (or `refresh()`).

**Checkpoint**: US2 independently testable per [quickstart.md](./quickstart.md) Phase 4.

---

## Phase 5: User Story 3 — Coherencia servidor–cliente (Priority: P1)

**Goal**: Countdown matches server within ≤2s; multi-tab updates without manual action; auto `refresh()` at `00:00`; limit errors coherent with countdown.

**Independent Test**: Reload with active window → countdown within 2s of server; vote in tab A updates tab B promptly; countdown does not jump on second vote (quickstart Phases 5–6).

### Tests for US3 (write first, must fail) ⚠️

- [X] T027 [P] [US3] Add coherence tests in `backend/tests/test_limit_windows.py` — `GET /api/participant/state` returns stable `*_quota_reset_at` across sequential calls; expired window clears columns.
- [X] T028 [P] [US3] In `backend/tests/test_votes.py` and `backend/tests/test_youtube_search.py` — when vote/search limit exceeded, subsequent `GET /api/participant/state` (or error response `state` if present) shows **same** `*_quota_reset_at` as before rejection (FR-009).

### Implementation for US3

- [X] T029 [US3] In `frontend/src/app/participate/participate.component.ts`, add 1 Hz tick updating display from `state.*_quota_reset_at`; call `cdr.markForCheck()` each tick (OnPush); on `secondsUntil <= 0` call `ParticipantStateService.refresh()` (FR-014, SC-006).
- [X] T030 [US3] In `frontend/src/app/services/participant-state.service.ts`, on SSE `state` event for participant session: **`void this.refresh()`** (full participant state including limits) instead of partial merge that omits `votes_remaining`, `searches_remaining`, and `*_quota_reset_at` — fixes multi-tab sync (US3 sc.2).
- [X] T031 [US3] On tab visibility resume (`document.visibilitychange` or existing live poll), re-sync countdown from latest `state` snapshot in `frontend/src/app/participate/participate.component.ts`.

**Checkpoint**: US3 independently testable per [quickstart.md](./quickstart.md) Phases 5–6.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, contracts finalization, build.

- [X] T032 [P] Run `pytest backend/tests/test_limit_windows.py backend/tests/test_votes.py backend/tests/test_youtube_search.py backend/tests/test_participant_submit.py -q`, `npm --prefix frontend test -- src/app/limit-countdown.util.spec.ts src/app/participant-limits.util.spec.ts src/app/participate/participate.component.spec.ts`, and `npm --prefix frontend run build`.
- [ ] T033 Execute manual validation per `specs/022-limit-reset-countdown/quickstart.md` (Phases 1–8, including Normas screen static copy check) — constitution V for countdown UI.
- [X] T034 [P] Set change `022-limit-reset-countdown` to `status: implemented` in `specs/manifest.yml`; finalize merged contract sections in `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md`; clear or update `active.change` in `AGENTS.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**.
- **US1 (Phase 3)**: T015–T016 before T017; T017 before T019 needs running component.
- **US2 (Phase 4)**: T023–T024 before T025.
- **US3 (Phase 5)**: After US1+US2; T029–T031 depend on T017/T025 labels.
- **Polish (Phase 6)**: After US1–US3.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | Phase 2 + T015–T016 | Vote countdown in header |
| US2 | Phase 2 + T023–T024 | Search countdown in subsection |
| US3 | US1+US2 state fields | Reload, multi-tab, auto-refresh, FR-009 |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T008–T012 ∥ (after T006)
- **US1 tests**: T013 ∥ T014
- **US2 tests**: T020 ∥ T021 ∥ T022
- **US3 tests**: T027 ∥ T028
- **After Phase 2**: US1 backend (T015–T016) ∥ US2 backend (T023–T024)
- **Polish**: T032 ∥ T034

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 → Phase 2 → Phase 3 (T013–T019)
2. **STOP and VALIDATE** quickstart Phases 1–3 (manual refresh OK until T029)

### Incremental Delivery

1. Setup + Foundational
2. US1 (votes) → US2 (searches) → US3 (coherence + auto-refresh) → Polish

---

## Notes

- **Fixed window** replaces rolling 10-minute logic — update all tests that assume per-event expiry.
- `*_quota_reset_at` is **null** when no window → no countdown (SC-002).
- Invalid search/vote must not create `participant_searches` row or `Vote` row / must not set anchor (FR-011).
- SSE `state` does not include limits — **T030** calls full `refresh()` on every participant SSE `state` so multi-tab stays in sync without 15s poll delay.
