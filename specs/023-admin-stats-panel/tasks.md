---
description: "Task list for 023-admin-stats-panel"
---

# Tasks: Panel de estadísticas en Admin

**Input**: Design documents from `specs/023-admin-stats-panel/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Backend `backend/tests/test_admin_stats.py`; `admin-stats.util.spec.ts` (create `admin-stats.util.ts` only if helpers extracted per T027); manual quickstart Phases 1–9 (constitution V).

**Organization**: Grouped by user story (US1–US4). All stories P1. Depends on **021-collapsible-panels-reset** (admin accordion). **No migration.**

**TDD**: Within each user story phase, complete **Tests** tasks before **Implementation** tasks (do not mark test tasks `[P]` parallel to implementation in the same story).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US4)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [X] T001 [P] Merge `specs/023-admin-stats-panel/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (`GET /api/admin/stats`, `AdminStatsResponse`, Estadísticas panel layout).
- [X] T002 Verify `specs/manifest.yml` has change `023-admin-stats-panel` (`status: planned`, `modifies: backend-api, app-core`) and `active.change` / `active.context_pack` point to this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: API schemas, stats service skeleton, router registration, frontend types/service, admin panel shell.

**⚠️ CRITICAL**: No user story UI sections can ship until T010 exposes a callable endpoint; summary/rankings may return zeros/empty until US-specific tasks complete.

- [X] T003 Add `AdminStatsResponse`, `QueueStatusCounts`, `ParticipantRankingItem`, `SongRankingItem` in `backend/app/schemas.py` per [contracts/contract-deltas.md](./contracts/contract-deltas.md).
- [X] T004 Create `backend/app/services/stats_service.py` with `build_admin_stats_response(db)` returning **stub** zeros and empty ranking lists (structure matches schema).
- [X] T005 Create `backend/app/routers/admin_stats.py` — `GET /api/admin/stats` with `CurrentUser`, delegates to `build_admin_stats_response`.
- [X] T006 Register `admin_stats` router in `backend/app/main.py`.
- [X] T007 [P] Add `frontend/src/app/models/admin-stats.ts` — TypeScript interfaces mirroring `AdminStatsResponse`.
- [X] T008 [P] Add `frontend/src/app/services/admin-stats.service.ts` — `getStats()` → `GET /api/admin/stats`.
- [X] T009 Extend `AdminPanelId` and `panelExpanded` in `frontend/src/app/admin/admin.component.ts` with `stats: false`; insert collapsed **Estadísticas** `<app-collapsible-section>` after Historial in `frontend/src/app/admin/admin.component.html` (placeholder content OK).
- [X] T010 Wire stats loading in `frontend/src/app/admin/admin.component.ts`: shared `loadStats()` called **only** when `setPanelExpanded('stats', true)` (not on init, not while collapsed); store snapshot + shared `statsLoading` / `statsError` flags used by all sections.
- [X] T010b [US1] Add unit coverage in `frontend/src/app/admin/admin-stats.util.spec.ts` (or `admin.component.spec.ts` if lighter) — `loadStats` / expand handler **not** invoked when panel stays collapsed (guards no `/api/admin/stats` call).

**Checkpoint**: Operator can expand Estadísticas and receive 200 with stub payload; **zero** `/api/admin/stats` requests while panel collapsed (network tab + unit guard).

---

## Phase 3: User Story 1 — Ver resumen de participación (Priority: P1) 🎯 MVP

**Goal**: Summary totals visible on expand — participantes activos, envíos, votos, canciones distintas con votos.

**Independent Test**: Expand Estadísticas with known activity → summary numbers match DB; empty event shows zeros (quickstart Phases 1–2, 7).

### Tests for US1 (write first, must fail) ⚠️

- [X] T011 [US1] Add summary aggregate tests in `backend/tests/test_admin_stats.py` — `participants_active_count` (submission ∪ vote), `total_submissions`, `total_votes_cast`, `distinct_voted_songs_count`; empty DB returns zeros; participant without activity excluded. **Complete before T012.**

### Implementation for US1

- [X] T012 [US1] Implement summary helpers in `backend/app/services/stats_service.py` — active participants union, submission/vote totals, distinct voted videos; wire into `build_admin_stats_response`.
- [X] T013 [US1] Add **Resumen** section in `frontend/src/app/admin/admin.component.html` — cards/rows for the four summary metrics with empty-state copy when zero.
- [X] T014 [US1] Bind summary fields in `frontend/src/app/admin/admin.component.ts` from stats snapshot; wire shared `statsLoading` / `statsError` from `loadStats()` (reused by Actualizar in T025).

**Checkpoint**: US1 independently testable per [quickstart.md](./quickstart.md) Phases 1–2 and 7.

---

## Phase 4: User Story 2 — Rankings de participantes más activos (Priority: P1)

**Goal**: Top 10 submitters and top 10 voters with display name and count; alphabetical tie-break at rank 10.

**Independent Test**: Seed participants with varied submission/vote counts → both rankings ordered correctly, max 10 rows (quickstart Phase 3).

### Tests for US2 (write first, must fail) ⚠️

- [X] T015 [US2] Add participant ranking tests in `backend/tests/test_admin_stats.py` — `top_submitters` counts all submission statuses; `top_voters` from `votes`; operator entries excluded from submitters; tie-break alphabetical at limit 10; `display_name` fallback uses email local-part when name missing. **Complete before T016.**

### Implementation for US2

- [X] T016 [US2] Implement `_top_submitters` and `_top_voters` in `backend/app/services/stats_service.py` with `ORDER BY count DESC, display_name ASC LIMIT 10`; add `_participant_display_label(participant)` → `display_name`, else email local-part before `@`, else `«Participante»`.
- [X] T017 [US2] Add **Más canciones enviadas** and **Más votos emitidos** lists in `frontend/src/app/admin/admin.component.html` with «Sin datos aún» when empty.
- [X] T018 [US2] Use `participant_display_label()` from API (or shared `frontend/src/app/admin/admin-stats.util.ts`) in ranking lists — same fallback order as backend (name → email local-part → «Participante»).

**Checkpoint**: US2 independently testable per quickstart Phase 3 (participant rankings portion).

---

## Phase 5: User Story 3 — Canciones más votadas (Priority: P1)

**Goal**: Top 10 songs by aggregated `SUM(vote_count)` per `youtube_video_id` with title and total votes.

**Independent Test**: Duplicate video ids across entries → single row with summed votes; songs with zero votes omitted (quickstart Phase 3).

### Tests for US3 (write first, must fail) ⚠️

- [X] T019 [US3] Add song ranking tests in `backend/tests/test_admin_stats.py` — aggregate by `youtube_video_id`, sum votes across entries, title from entry, alphabetical tie-break, exclude zero-vote videos. **Complete before T020.**

### Implementation for US3

- [X] T020 [US3] Implement `_top_songs` in `backend/app/services/stats_service.py` — `GROUP BY youtube_video_id`, `HAVING SUM(vote_count) > 0`, `ORDER BY vote_total DESC, title ASC LIMIT 10`.
- [X] T021 [US3] Add **Canciones más votadas** list in `frontend/src/app/admin/admin.component.html` with truncated title + full title on focus/`title` attr for accessibility.

**Checkpoint**: US3 independently testable per quickstart Phase 3 (songs portion).

---

## Phase 6: User Story 4 — Indicadores de actividad de cola (Priority: P1)

**Goal**: Queue status counters and manual **Actualizar**; stats reflect `DELETE /api/queue/history`; no background fetch while collapsed or open.

**Independent Test**: Counters match queue states; Actualizar refreshes after external activity; vaciar historial zeros played/rejected (quickstart Phases 4–6).

### Tests for US4 (write first, must fail) ⚠️

- [X] T022 [US4] Add queue-count and clear-history tests in `backend/tests/test_admin_stats.py` — `queue_counts` per status; after `DELETE /api/queue/history`, played/rejected drop and rankings update. **Complete before T024.**
- [X] T023 [US4] Add auth test in `backend/tests/test_admin_stats.py` — unauthenticated and participant session → 401 on `GET /api/admin/stats`. **Complete before T024.**

### Implementation for US4

- [X] T024 [US4] Implement `_queue_status_counts` in `backend/app/services/stats_service.py` — `GROUP BY status` into `QueueStatusCounts`.
- [X] T025 [US4] Add **Estado de cola** counter grid and **Actualizar** button in `frontend/src/app/admin/admin.component.html`; button calls shared `loadStats()` (same loading/error UI as T014).
- [X] T026 [US4] In `frontend/src/app/admin/admin.component.ts`, ensure **no** stats fetch on SSE `state` events, **no** interval polling, and **no** fetch while `panelExpanded.stats === false` (only expand, **Actualizar**, and re-expand via `loadStats()`).

**Checkpoint**: US4 independently testable per quickstart Phases 4–6.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, layout, i18n, contracts finalization, build.

- [X] T027 [P] Add `frontend/src/app/admin/admin-stats.util.ts` with `participantDisplayLabel()` and empty-state copy helpers **if** extracted from component; add `frontend/src/app/admin/admin-stats.util.spec.ts` for labels + collapsed no-fetch guard (complements T010b).
- [X] T031 [P] Compact mobile layout in `frontend/src/app/admin/admin.component.html` — section order **Resumen → Estado de cola → rankings**; verify SC-002 (full v1 visible within **≤2 viewport heights** on standard mobile) during T029.
- [X] T032 [P] Spanish copy audit (FR-013) — all Estadísticas strings in `frontend/src/app/admin/admin.component.html` (headings, buttons, empty states, errors) in Spanish consistent with Admin.
- [X] T028 [P] Run `pytest backend/tests/test_admin_stats.py -q` and `npm --prefix frontend test -- src/app/admin/admin-stats.util.spec.ts` and `npm --prefix frontend run build`.
- [ ] T029 Execute manual validation per `specs/023-admin-stats-panel/quickstart.md` Phases 1–9 — include SC-004 (Actualizar refreshes within **~3s** on local network) and SC-002 mobile scroll check (Phase 9).
- [X] T030 [P] Set change `023-admin-stats-panel` to `status: implemented` in `specs/manifest.yml`; finalize merged contract sections; update `AGENTS.md` active change.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories**.
- **US1 (Phase 3)**: Depends on T010; T011 before T012; T012 before T013–T014.
- **US2 (Phase 4)**: Depends on Phase 2; T015 before T016; **T017 after T013** (same `admin.component.html`).
- **US3 (Phase 5)**: Depends on Phase 2; T019 before T020; **T021 after T017**.
- **US4 (Phase 6)**: Depends on Phase 2; T022–T023 before T024; **T025 after T021**.
- **Polish (Phase 7)**: After US1–US4.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | Phase 2 + summary in service | Summary totals on expand |
| US2 | Phase 2 + US1 optional for same panel | Participant top-10 lists |
| US3 | Phase 2 | Song top-10 list |
| US4 | Phase 2 | Queue counters + Actualizar + clear-history |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T007 ∥ T008; T003–T006 sequential on backend chain; T010b after T010
- **After Phase 2 backends**: T016 ∥ T020 ∥ T024 (same file — coordinate commits)
- **Frontend HTML**: **serialize** T013 → T017 → T021 → T025 (one file)
- **Polish**: T027 ∥ T031 ∥ T032 ∥ T030; T028 after implementation complete

---

## Parallel Example: After Foundational

```bash
# Backend (coordinate stats_service.py):
# T016 top_submitters/voters
# T020 top_songs
# T024 queue_counts

# Frontend admin.component.html — SERIAL only:
# T013 Resumen → T017 participant lists → T021 songs → T025 queue + Actualizar
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 → Phase 2 → Phase 3 (T011–T014)
2. **STOP and VALIDATE** quickstart Phases 1–2, 7

### Incremental Delivery

1. Setup + Foundational
2. US1 summary → US2 participant rankings → US3 song rankings → US4 queue + refresh → Polish

---

## Notes

- **No Alembic migration** — read-only SQL over existing tables.
- Single endpoint returns full `AdminStatsResponse`; extend `stats_service` per story rather than multiple endpoints.
- Operator/filler submissions (`submitted_by_participant_id IS NULL`) never appear in participant submission rankings.
- Rejected and pending submissions **do** count toward submitter totals (clarification 2026-08-04).
