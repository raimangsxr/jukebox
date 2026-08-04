---
description: "Task list for 017-admin-queue-history-filler"
---

# Tasks: Historial de cola y canciones de relleno en Admin

**Input**: Design documents from `specs/017-admin-queue-history-filler/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Included — constitution principle V and plan require `test_queue_history.py`, `test_filler_reserve.py`, plus ordering regression.

**Organization**: Grouped by user story (US1–US4). US1/US2/US4 = P1, US3 = P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US4)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [x] T001 [P] Merge `specs/017-admin-queue-history-filler/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (draft sections; finalize status in Polish).
- [x] T002 [P] Add change entry `017-admin-queue-history-filler` to `specs/manifest.yml` with `status: draft`, `modifies: [backend-api, app-core]`, and set `active.change` + `active.context_pack` to this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, shared enums, and queue ordering all stories depend on.

**⚠️ CRITICAL**: Complete before user story implementation.

- [x] T003 Add Alembic migration `backend/alembic/versions/0010_queue_history_filler.py` — `queue_entries.priority`, `queue_entries.source`, `queue_entries.finished_at`, table `filler_reserve_entries`, `event_config.filler_auto_inject_enabled`, backfill and index `(status, finished_at)`.
- [x] T004 [P] Add `QueueEntryPriority`, `QueueEntrySource`, extended `QueueEntry` columns, and `FillerReserveEntry` model in `backend/app/models.py`.
- [x] T005 [P] Add history, reserve, and config DTOs (`HistoryListResponse`, `HistoryQueueEntryRead` with `source`, `FillerReserveEntryRead`, `FillerReserveReorderRequest`, `OperatorQueueSubmitRequest`, `FillerAutoInjectUpdate`) and extend `QueueEntryRead.priority` + `EventConfigRead.filler_auto_inject_enabled` in `backend/app/schemas.py`.
- [x] T006 Set `finished_at` when marking `played` or `rejected` in `backend/app/services/queue_service.py` (`reject_entry`, `skip_or_advance`).
- [x] T007 Update queue ordering (votes → priority rank → `created_at`) in `backend/app/services/state_service.py` and `backend/app/services/queue_service.py` (`_top_queued`, `_recompute_positions`, `get_queue_strip`, `get_all_queued`); vote reorder inherits via `_recompute_positions` in `backend/app/services/vote_service.py`.
- [x] T007b Set `priority=normal` and `source=participant` on participant submit paths in `backend/app/services/queue_service.py` (`submit_as_participant`, `approve_entry`/`_enqueue_entry` for participant-origin entries).
- [x] T008 [P] Set `filler_auto_inject_enabled=True` default in `backend/app/bootstrap.py` `ensure_event_config`.
- [x] T009 Register new `filler_reserve` router in `backend/app/main.py`.

**Checkpoint**: DB migrates; priority sort active; `finished_at` populated on terminal transitions.

---

## Phase 3: User Story 1 — Consultar historial y re-encolar (Priority: P1) 🎯 MVP

**Goal**: Operator views played/rejected history and re-queues entries directly to `queued`.

**Independent Test**: Play/reject songs → open **Historial** in `/admin` → re-encolar → new entry in kiosk queue; duplicate blocked with 409; moderated mode skips `pending_review`.

### Tests for US1 (write first, must fail) ⚠️

- [x] T010 [P] [US1] Create `backend/tests/test_queue_history.py` — list pagination/filter, operator auth 401, **participant auth 401** on history routes (FR-014), requeue from `played`/`rejected`, priority rules, duplicate 409 **including video in `filler_reserve_entries`**, moderated mode direct-to-queued, **`revision` bump after requeue** (FR-015).

### Implementation for US1

- [x] T011 [US1] Implement `list_history` and `requeue_from_history` (set `source=operator_requeue`, priority rules, `_enqueue_entry`) in `backend/app/services/queue_service.py`.
- [x] T012 [US1] Add `GET /api/queue/history` and `POST /api/queue/history/{id}/requeue` in `backend/app/routers/queue.py`.
- [x] T013 [P] [US1] Add `getHistory` and `requeue` methods in `frontend/src/app/services/queue-admin.service.ts`.
- [x] T014 [US1] Add **Historial** section in `frontend/src/app/admin/admin.component.html` and `frontend/src/app/admin/admin.component.ts` — paginated table with columns: título, miniatura, `youtube_video_id`, estado, `finished_at`, `source`, participante, motivo rechazo; filtro por estado; acción Re-encolar con confirmación y manejo de errores 409.

**Checkpoint**: Historial + re-encolar end-to-end; US1 tests green.

---

## Phase 4: User Story 2 — Gestionar reserva de canciones de relleno (Priority: P1)

**Goal**: Operator manages filler reserve (add, delete, reorder, manual enqueue to active queue).

**Independent Test**: Add 3 songs to reserve → not visible on kiosk → reorder → **Añadir a cola** consumes item and enqueues with low priority.

### Tests for US2 (write first, must fail) ⚠️

- [x] T015 [P] [US2] Create `backend/tests/test_filler_reserve.py` — CRUD, max 50, duplicate 409 (reserve + active queue), reorder, enqueue consumes reserve, batch enqueue, queue-full 409, **participant auth 401 on all `/api/filler-reserve/*` routes** (FR-014), **operator direct submit** (`POST /api/queue/operator-submit`), **`revision` bump after enqueue/inject** (FR-015).

### Implementation for US2

- [x] T016 [US2] Implement `backend/app/services/filler_reserve_service.py` — add/delete/list/reorder, duplicate checks (reserve + active queue), `transfer_to_queue` with `priority=low` and `source=operator_filler`.
- [x] T017 [US2] Create `backend/app/routers/filler_reserve.py` with `GET/POST/DELETE`, `PUT /reorder`, `POST /{id}/enqueue`, `POST /enqueue-batch`.
- [x] T017b [US2] Implement `create_operator_queued_entry` in `backend/app/services/queue_service.py` and `POST /api/queue/operator-submit` in `backend/app/routers/queue.py` (`priority=low`, `source=operator_direct`; FR-011 direct path).
- [x] T018 [US2] Allow operator session on `GET /api/youtube/search` without participant rate limit in `backend/app/routers/youtube.py`.
- [x] T019 [P] [US2] Create `frontend/src/app/services/filler-reserve.service.ts` for reserve API client; add `operatorSubmit` to `frontend/src/app/services/queue-admin.service.ts`.
- [x] T020 [US2] Add **Reserva de relleno** section in `frontend/src/app/admin/admin.component.html` and `frontend/src/app/admin/admin.component.ts` — list, add URL/search, delete, reorder controls, **Añadir directo a cola** (operator-submit), Añadir a cola desde reserva.
- [x] T021 [P] [US2] Add `priority` to `QueueEntryRead` in `frontend/src/app/models/jukebox-state.ts`.

**Checkpoint**: Reserve management complete; US2 tests green.

---

## Phase 5: User Story 4 — Orden de cola con prioridad en empates (Priority: P1)

**Goal**: On equal votes, `normal` entries sort before `low`; votes remain primary sort key.

**Independent Test**: Enqueue filler + participant song at 0 votes → participant first; more votes on filler moves it ahead.

> **Note**: Priority sort logic is in Foundational (T007); participant `source`/`priority` defaults in T007b. This phase validates behavior end-to-end after US2 enqueue paths exist.

### Tests for US4 (write first, must fail) ⚠️

- [x] T022 [P] [US4] Extend `backend/tests/test_state.py` and `backend/tests/test_votes.py` — tie-break normal before low; higher vote count still wins; filler entry votable.

### Implementation for US4

- [x] T023 [US4] Ensure `priority=low` on operator paths in `backend/app/services/filler_reserve_service.py` (`operator_filler`, `auto_inject`) and verify `create_operator_queued_entry` sets `operator_direct` (depends on T017b).
- [x] T024 [US4] Verify kiosk and admin reflect new order via existing `GET /api/state` SSE path (no participant/kiosk template changes; order from server).

**Checkpoint**: SC-003 ordering rules verified; US4 tests green.

---

## Phase 6: User Story 3 — Inyección automática de relleno en huecos (Priority: P2)

**Goal**: When idle with empty queue and auto-inject enabled, next reserve item (position 1) transfers to queue and plays.

**Independent Test**: Populate reserve → empty active queue → skip/end song → filler auto-starts <5s; toggle off blocks inject.

### Tests for US3 (write first, must fail) ⚠️

- [x] T025 [P] [US3] Extend `backend/tests/test_filler_reserve.py` with auto-inject cases — idle inject, toggle disabled, empty reserve no-op, `source=auto_inject`, **`revision` bump** (FR-015).

### Implementation for US3

- [x] T026 [US3] Implement `inject_next_if_idle` in `backend/app/services/filler_reserve_service.py` and invoke from `skip_or_advance` and `_maybe_auto_start_playback` in `backend/app/services/queue_service.py`.
- [x] T027 [US3] Implement `PUT /api/event-config/filler-auto-inject` in `backend/app/routers/event_config.py`.
- [x] T028 [P] [US3] Add `filler_auto_inject_enabled` and `updateFillerAutoInject()` in `frontend/src/app/models/event-config.ts` and `frontend/src/app/services/event-config.service.ts`.
- [x] T029 [US3] Add **Inyección automática** toggle in `frontend/src/app/admin/admin.component.html` and `frontend/src/app/admin/admin.component.ts`.

**Checkpoint**: Auto-inject on idle gaps; US3 tests green.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression, validation, SDD closure.

- [x] T030 [P] Extend `backend/tests/test_queue.py` — `finished_at` set on skip/reject regression; existing moderation/skip flows unchanged.
- [x] T030b [P] Add `test_source_audit_all_creation_paths` in `backend/tests/test_filler_reserve.py` (or shared module) asserting FR-017 matrix: `participant`, `operator_requeue`, `operator_filler`, `operator_direct`, `auto_inject` on each creation path.
- [x] T031 Run `specs/017-admin-queue-history-filler/quickstart.md` phases and document SC-001–SC-005 gate results (SC-001/SC-005 manual usability; SC-002/SC-004 timing in quickstart).
- [x] T032 [P] Finalize contract merge status and set `017-admin-queue-history-filler` to `implemented` in `specs/manifest.yml`; run `pytest backend/tests/` and `npm --prefix frontend run build`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**.
- **US1 (Phase 3)**: After Foundational — MVP, no dependency on US2/US3.
- **US2 (Phase 4)**: After Foundational — independent of US1 (parallel possible after Phase 2).
- **US4 (Phase 5)**: After Foundational; tests best after US2 enqueue paths exist (T023 touches both services).
- **US3 (Phase 6)**: Depends on **US2** (reserve must exist) + Foundational config column.
- **Polish (Phase 7)**: After desired user stories complete.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 Historial | Foundational | Re-encolar without reserve |
| US2 Reserva | Foundational | Reserve CRUD without auto-inject |
| US4 Prioridad | Foundational T007/T007b (+ US2 T017b for operator paths) | Vote/order tests |
| US3 Auto-inyect | US2 + Foundational | Idle inject from reserve |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T004 ∥ T005; T008 after T004
- **After Phase 2**: US1 (Phase 3) ∥ US2 (Phase 4) in parallel on different developers
- **Per story**: test tasks marked [P] before implementation in same story

### Parallel Example: After Foundational

```bash
# Developer A — US1 historial
T010 → T011 → T012 → T013 → T014

# Developer B — US2 reserva (parallel)
T015 → T016 → T017 → T018 → T019 → T020 → T021
```

### Parallel Example: User Story 1

```bash
T010  # tests first
T011 → T012  # backend chain
T013      # frontend service (parallel after T012 contract known)
T014      # admin UI
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1)
3. **STOP and VALIDATE** — historial + re-encolar per quickstart Phase 1
4. Demo to operator

### Incremental Delivery

1. Setup + Foundational → schema and ordering ready
2. US1 → historial/re-encolar (MVP)
3. US2 → reserve management
4. US4 → priority tie-break verified
5. US3 → auto-inject + toggle
6. Polish → quickstart + manifest

### Suggested MVP Scope

**User Story 1 only** (Phases 1–3): delivers immediate operator value (history + re-queue) without filler reserve complexity.

---

## Notes

- Re-encolar always creates `queued` entries — never `pending_review` (clarification 2026-08-04).
- Reserve items are **consumed** on transfer to active queue.
- Filler songs in active queue are **votable** (same vote rules).
- Reserve order is **operator-defined**; auto-inject takes position 1.
- Total tasks: **35** (T001–T032, T007b, T017b, T030b).
- Duplicate rule: always check `filler_reserve_entries` + active queue states (FR-004).
- `source` audit matrix: see T030b (FR-017).
