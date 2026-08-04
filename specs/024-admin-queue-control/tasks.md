---
description: "Task list for 024-admin-queue-control"
---

# Tasks: Control de cola de reproducción en Admin

**Input**: Design documents from `specs/024-admin-queue-control/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: `backend/tests/test_admin_queue_control.py`; `admin.component.spec.ts` / `admin-queue.util.spec.ts`; manual [quickstart.md](./quickstart.md) (constitution V).

**Organization**: User stories US1, US1b, US2 (P1), US3–US5 (P2). Depends on **021-collapsible-panels-reset** (accordion). **No migration.**

**TDD**: Within each story phase, complete **Tests** tasks before **Implementation** tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1, US1b, US2…)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [X] T001 [P] Merge `specs/024-admin-queue-control/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (active queue routes, Cola de reproducción panel, Moderación trim).
- [X] T002 Verify `specs/manifest.yml` lists change `024-admin-queue-control` (`status: planned`, `modifies: backend-api, app-core`) and `active.change` / `active.context_pack` point to this feature (done if manifest already updated).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schemas, read-only list endpoint, panel shell. Write/mutate routes ship in user-story phases (US2–US5); `_promote_next_or_idle` lands in **Phase 6 (US3, T023)**.

**⚠️ CRITICAL**: No **write** routes (vaciar, delete, play-now, vote-count) until their story phase. `GET /api/queue/active` must work after T010.

- [X] T003 Add `ActiveQueueEntryRead`, `ActiveQueueListResponse`, `VoteCountUpdateRequest` in `backend/app/schemas.py` per [contracts/contract-deltas.md](./contracts/contract-deltas.md).
- [X] T004 Implement `list_active_queue(db)` in `backend/app/services/queue_service.py` — `now_playing` + full `queued` list with `submitted_by_display_name` and `source`.
- [X] T005 Add `GET /api/queue/active` in `backend/app/routers/queue.py` (**before** `/{entry_id}/approve` routes) with `CurrentUser`, returns `list_active_queue`.
- [X] T006 [P] Add `ActiveQueueListResponse` / `ActiveQueueEntryRead` types in `frontend/src/app/models/jukebox-state.ts` (or `frontend/src/app/models/admin-queue.ts`).
- [X] T007 [P] Add `getActiveQueue()` in `frontend/src/app/services/queue-admin.service.ts` → `GET /api/queue/active`.
- [X] T008 Extend `AdminPanelId` and `panelExpanded` in `frontend/src/app/admin/admin.component.ts` with `queue: false`; insert collapsed **Cola de reproducción** `<app-collapsible-section>` **after Moderación, before Historial** in `frontend/src/app/admin/admin.component.html` (placeholder OK).
- [X] T008b [US1] Assert default accordion in `frontend/src/app/admin/admin.component.spec.ts` (or extend existing spec): on init `panelExpanded.moderation === true`, `panelExpanded.queue === false`, and other panels collapsed (FR-001).
- [X] T009 Wire `loadActiveQueue()` in `frontend/src/app/admin/admin.component.ts` when `setPanelExpanded('queue', true)`; store `activeQueue`, `activeQueueLoading`, `activeQueueError`.
- [X] T010 [P] Add `frontend/src/app/admin/admin-queue.util.ts` with Spanish labels for `source`, status, and empty-state copy (optional spec in `admin-queue.util.spec.ts`).

**Checkpoint**: Expand Cola de reproducción → 200 with ordered active list; Moderación unchanged for now.

---

## Phase 3: User Story 1 — Ver cola activa ordenada (Priority: P1) 🎯 MVP

**Goal**: Full active queue list with metadata, badge counter, live SSE refresh while expanded.

**Independent Test**: Playing + queued entries → expand panel → correct order and fields; SSE vote updates list (quickstart Phases 1–2, 8).

### Tests for US1 (write first, must fail) ⚠️

- [X] T011 [US1] Add list + auth tests in `backend/tests/test_admin_queue_control.py` — `GET /api/queue/active` 401 participant; order (playing + queued positions); `source` and `submitted_by_display_name`; empty active queue. **Complete before T012.**

### Implementation for US1

- [X] T012 [US1] Harden `list_active_queue` in `backend/app/services/queue_service.py` if gaps found by T011 (ordering, display-name fallback).
- [X] T013 [US1] Add header badge in `frontend/src/app/admin/admin.component.html` for Cola de reproducción — count `now_playing + queued.length`, live via reload/SSE.
- [X] T014 [US1] Render active queue rows in `frontend/src/app/admin/admin.component.html` — title, thumbnail, votes, position, status, priority, duration, source, submitter, created_at, **Previsualizar** link (`youtubeUrl()` like Moderación) (FR-004; use `admin-queue.util.ts` labels).
- [X] T015 [US1] Subscribe to operator SSE `state` in `frontend/src/app/admin/admin.component.ts` while `panelExpanded.queue` → call `loadActiveQueue()` for live updates (FR-006).

**Checkpoint**: US1 independently testable per quickstart Phases 1–2 and 8.

---

## Phase 4: User Story 1b — Controles globales de reproducción (Priority: P1)

**Goal**: Move Iniciar reproducción, Saltar canción, playback status, and audio hint from Moderación to Cola de reproducción.

**Independent Test**: Buttons only in queue panel; same skip/start behavior (quickstart Phase 3).

### Implementation for US1b

- [X] T016 [US1b] Remove playback status block and Iniciar/Saltar buttons from Moderación section in `frontend/src/app/admin/admin.component.html`.
- [X] T017 [US1b] Add playback status (`playbackStatusLabel`, `playbackAudioHint`) and Iniciar/Saltar buttons to Cola de reproducción panel in `frontend/src/app/admin/admin.component.html` — reuse `advancePlayback()`, `canStartPlayback`, `canSkipPlayback`, `playbackBusy` from `frontend/src/app/admin/admin.component.ts`.
- [X] T017b [US1b] Add test in `frontend/src/app/admin/admin.component.spec.ts` — Moderación template does **not** contain «Iniciar reproducción» / «Saltar canción»; Cola de reproducción section contains them (FR-016–FR-018).

**Checkpoint**: US1b testable per quickstart Phase 3; Moderación shows only mode + pending table.

---

## Phase 5: User Story 2 — Vaciar toda la cola (Priority: P1)

**Goal**: `DELETE /api/queue/active` hard-deletes all active entries; confirm dialog; no filler auto-inject.

**Independent Test**: Playing + queued → Vaciar → confirm → all gone, pending/reserve untouched (quickstart Phase 7).

### Tests for US2 (write first, must fail) ⚠️

- [X] T018 [US2] Add vaciar tests in `backend/tests/test_admin_queue_control.py` — permanent delete; runtime cleared; `pending_review` survives; no `maybe_inject_from_reserve` after clear; 401 participant on `DELETE /api/queue/active`; after clear, participant `GET /api/participant/submissions` omits deleted entries (FR-014). **Complete before T019.**

### Implementation for US2

- [X] T019 [US2] Implement `clear_active_queue(db)` in `backend/app/services/queue_service.py` — hard delete `queued`/`playing`, clear `now_playing_entry_id`, **no** filler inject, `bump_revision`.
- [X] T020 [US2] Add `DELETE /api/queue/active` in `backend/app/routers/queue.py` returning `StateResponse`.
- [X] T021 [US2] Add `clearActiveQueue()` in `frontend/src/app/services/queue-admin.service.ts` and **Vaciar cola** button with confirm dialog in `frontend/src/app/admin/admin.component.{ts,html}` (mirror historial vaciar pattern); disabled when active empty.

**Checkpoint**: US2 independently testable per quickstart Phase 7.

---

## Phase 6: User Story 3 — Forzar reproducir (Priority: P2)

**Goal**: `POST /api/queue/{id}/play-now` promotes queued entry; interrupt marks previous `played`.

**Independent Test**: Force 3rd queued while playing → target plays, interrupted in historial (quickstart Phase 4).

### Tests for US3 (write first, must fail) ⚠️

- [X] T022 [US3] Add play-now tests in `backend/tests/test_admin_queue_control.py` — promote queued; interrupt → `played` not deleted; no-op if already playing; 409 invalid status; **401 participant on `POST /api/queue/{id}/play-now`** (FR-013). **Complete before T023.**

### Implementation for US3

- [X] T023 [US3] Extract shared `_promote_next_or_idle(db)` in `backend/app/services/queue_service.py` from skip tail logic; use in skip, delete, play-now paths.
- [X] T024 [US3] Implement `force_play_entry(db, entry_id)` in `backend/app/services/queue_service.py` per [data-model.md](./data-model.md).
- [X] T025 [US3] Add `POST /api/queue/{entry_id}/play-now` in `backend/app/routers/queue.py` returning `StateResponse`.
- [X] T026 [US3] Add `playNow(id)` in `frontend/src/app/services/queue-admin.service.ts` and **Forzar reproducir** per queued row in `frontend/src/app/admin/admin.component.{ts,html}` (disabled/hidden for `now_playing`).

**Checkpoint**: US3 independently testable per quickstart Phase 4.

---

## Phase 7: User Story 4 — Modificar votos (Priority: P2)

**Goal**: `PATCH /api/queue/{id}/vote-count` sets denormalized count and reorders queued without stopping playback.

**Independent Test**: Increase votes on lower row → positions swap; editing playing row does not stop playback (quickstart Phase 5).

### Tests for US4 (write first, must fail) ⚠️

- [X] T027 [US4] Add vote-count tests in `backend/tests/test_admin_queue_control.py` — reorder queued; playing status unchanged; **100% position match** with `queued_order_columns` after update (SC-004); 422 negative; no participant vote limit; **401 participant on `PATCH /api/queue/{id}/vote-count`** (FR-013). **Complete before T028.**

### Implementation for US4

- [X] T028 [US4] Implement `set_entry_vote_count(db, entry_id, vote_count)` in `backend/app/services/queue_service.py` — `_recompute_positions`, `bump_revision`.
- [X] T029 [US4] Add `PATCH /api/queue/{entry_id}/vote-count` in `backend/app/routers/queue.py` with `VoteCountUpdateRequest`.
- [X] T030 [US4] Add `setVoteCount(id, voteCount)` in `frontend/src/app/services/queue-admin.service.ts` and **Modificar votos** modal/input per row in `frontend/src/app/admin/admin.component.{ts,html}` — client validation (reject negative, empty, non-numeric) with Spanish error before API call; surface API 422 in modal (US4 scenario 3).

**Checkpoint**: US4 independently testable per quickstart Phase 5.

---

## Phase 8: User Story 5 — Eliminar entrada (Priority: P2)

**Goal**: `DELETE /api/queue/active/{id}` permanent delete with confirm; auto-advance if deleting playing.

**Independent Test**: Delete queued vs playing; cancel confirm; gone from Mis canciones (quickstart Phase 6).

### Tests for US5 (write first, must fail) ⚠️

- [X] T031 [US5] Add delete-active tests in `backend/tests/test_admin_queue_control.py` — hard delete + votes CASCADE; playing → next promotes; not in historial terminal; 401 participant on `DELETE /api/queue/active/{id}`; after delete, participant `GET /api/participant/submissions` omits entry (FR-014). **Complete before T032.**

### Implementation for US5

- [X] T032 [US5] Implement `delete_active_entry(db, entry_id)` in `backend/app/services/queue_service.py` using `_promote_next_or_idle` when deleting `playing`.
- [X] T033 [US5] Add `DELETE /api/queue/active/{entry_id}` in `backend/app/routers/queue.py` (**before** generic `/{entry_id}` routes if needed).
- [X] T034 [US5] Add `deleteActiveEntry(id)` in `frontend/src/app/services/queue-admin.service.ts` and **Eliminar de la cola** with mandatory confirm dialog per row in `frontend/src/app/admin/admin.component.{ts,html}`.

**Checkpoint**: US5 independently testable per quickstart Phase 6.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validation, docs hygiene, regression.

- [X] T035 Run `cd backend && pytest tests/test_admin_queue_control.py -q` and fix failures.
- [X] T035b Add parametrized auth test in `backend/tests/test_admin_queue_control.py` if not already covered — participant 401 on all five new routes in one test (FR-013 consolidation).
- [X] T036 Run `npm --prefix frontend run build` and fix TypeScript/template errors.
- [X] T037 Execute manual validation per [quickstart.md](./quickstart.md) Phases 1–12 — include auth all routes (Phase 9), participant sync (Phase 10), subjective timing checks SC-001/002/003/008 (Phase 11), stats impact (Phase 12).
- [X] T038 Update `specs/manifest.yml` change `024-admin-queue-control` to `implemented` and `AGENTS.md` active change summary after merge.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — **blocks** all user stories.
- **US1 (Phase 3)**: Depends on Foundational.
- **US1b (Phase 4)**: Depends on Phase 3 panel shell (same HTML file — run after US1 or same PR).
- **US2 (Phase 5)**: Depends on Foundational; independent of US3–US5.
- **US3 (Phase 6)**: Depends on T023 `_promote_next_or_idle`; can parallel US4/US5 after Foundational if promotion helper landed early.
- **US4 (Phase 7)**: Depends on Foundational only (may parallel US2 after Phase 2).
- **US5 (Phase 8)**: Depends on T023 promotion helper (shared with US3).
- **Polish (Phase 9)**: After desired stories complete.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 | Foundational | Active list + SSE refresh |
| US1b | US1 panel shell | Playback controls location |
| US2 | Foundational | Vaciar cola |
| US3 | Foundational + promote helper | Force play |
| US4 | Foundational | Vote edit reorder |
| US5 | Foundational + promote helper | Delete + confirm |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T006 ∥ T007 ∥ T010 while T003–T005 sequential; T008–T009 after types exist
- **After Phase 2**: US2 (T018–T021) ∥ US4 (T027–T030) in parallel (different service functions)
- **US3 and US5**: sequential on `queue_service.py` unless promotion helper merged first

### Parallel Example: Foundational

```bash
# After T003 schemas:
Task T006 "types in frontend/src/app/models/jukebox-state.ts"
Task T007 "getActiveQueue in queue-admin.service.ts"
Task T010 "admin-queue.util.ts labels"
```

### Parallel Example: P2 stories

```bash
# After Phase 2, different developers:
Dev A: US2 vaciar (T018–T021)
Dev B: US4 vote-count (T027–T030)
# Then US3/US5 on shared queue_service with coordination
```

---

## Implementation Strategy

### MVP First (US1 + US1b)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1 list + live refresh)
3. Complete Phase 4 (US1b move playback controls)
4. **STOP and VALIDATE** quickstart Phases 1–3, 8
5. Demo operable queue view with global playback in one panel

### Incremental Delivery

1. Setup + Foundational → list endpoint works
2. US1 + US1b → MVP (view + play/skip)
3. US2 → vaciar cola
4. US3 → force play
5. US4 → edit votes
6. US5 → delete entry
7. Polish → full quickstart

### Suggested MVP Scope

**US1 + US1b** (Phases 1–4): operator sees full queue and controls playback without per-row mutations.

---

## Notes

- Register `/active` routes **before** `/{entry_id}/approve` in `backend/app/routers/queue.py`.
- Hard delete affects `GET /api/admin/stats` totals — covered in quickstart Phase 10.
- Do not call `maybe_inject_from_reserve` after `clear_active_queue`.
- Moderación must not retain duplicate playback UI after US1b.
