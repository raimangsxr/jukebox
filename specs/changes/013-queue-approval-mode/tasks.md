---
description: "Task list for 013-queue-approval-mode"
---

# Tasks: Selector de modo de cola (Moderado / Libre)

**Input**: Design documents from `specs/changes/013-queue-approval-mode/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Included — constitution principle V and plan require `test_queue_approval_mode.py` plus regression on submit/notifications.

**Organization**: Grouped by user story (US1–US4). US1/US2 = P1, US3/US4 = P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US4)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [x] T001 [P] Merge `specs/changes/013-queue-approval-mode/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (draft sections; finalize status in Polish).
- [x] T002 [P] Add change entry `013-queue-approval-mode` to `specs/manifest.yml` with `status: draft`, `modifies: [backend-api, app-core]`, and set `active.change` + `active.context_pack` for this feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and shared helpers all stories depend on.

**⚠️ CRITICAL**: Complete before user story implementation.

- [x] T003 Add Alembic migration `backend/alembic/versions/0009_event_config_queue_mode.py` — `event_config.queue_mode VARCHAR(16) NOT NULL DEFAULT 'moderated'`.
- [x] T004 [P] Add `QueueMode` enum (`moderated`, `free`) and `EventConfig.queue_mode` mapped column with default in `backend/app/models.py`.
- [x] T005 [P] Add `queue_mode` to `EventConfigRead` and new `QueueModeUpdate` schema in `backend/app/schemas.py`; keep `EventConfigSummary` unchanged (no `queue_mode`). Existing `GET /api/event-config` must serialize `queue_mode` via `EventConfigRead.model_validate` once the model column exists (no separate router task).
- [x] T006 Set `queue_mode=moderated` in `backend/app/bootstrap.py` `ensure_event_config` seed row.
- [x] T007 Add `get_queue_mode(db) -> QueueMode` helper (in `backend/app/services/queue_service.py` or a small `event_config_service.py`) reading the singleton `event_config` row.

**Checkpoint**: DB migrates; mode readable; default is Moderado.

---

## Phase 3: User Story 1 — Elegir modo Moderado (Priority: P1) 🎯 MVP

**Goal**: Default **Moderado** behavior unchanged — submits → `pending_review`, approve/reject → queue.

**Independent Test**: With `queue_mode=moderated`, participant submit → pending in `/admin`, not in kiosk queue until approve; existing moderation flow works.

### Tests for US1 (write first, must fail) ⚠️

- [x] T008 [P] [US1] Create `backend/tests/test_queue_approval_mode.py` with moderated regression cases: default mode, submit → `pending_review`, absent from `GET /api/state` queue, present in `GET /api/queue/pending`, pending cap still applies.

### Implementation for US1

- [x] T009 [US1] Branch `submit_as_participant` in `backend/app/services/queue_service.py` on `get_queue_mode(db)`; **moderated** path preserves existing `pending_review` creation and `_count_participant_pending` limit (FR-005, FR-018).

**Checkpoint**: Moderado parity with pre-change behavior; tests green for US1.

---

## Phase 4: User Story 2 — Elegir modo Libre (Priority: P1)

**Goal**: **Libre** submits enqueue directly with notification and queued cap.

**Independent Test**: Set `queue_mode=free` via **DB fixture** (before T018 lands) or via `PUT /api/event-config/queue-mode` (after T018) → participant submit → `queued` on kiosk <5s, toast `song.approved`, not in pending list; third submit hits 429.

### Tests for US2 (write first, must fail) ⚠️

- [x] T010 [P] [US2] Extend `backend/tests/test_queue_approval_mode.py` with free-mode cases: submit → `queued`, excluded from `GET /api/queue/pending`, `queued` cap 429, queue-full 409, and **409 `video already in queue` on duplicate submit in free mode** (FR-015).
- [x] T011 [P] [US2] Extend `backend/tests/test_notifications.py` — free submit emits `song.approved` only to submitting participant (007 routing).
- [x] T012 [P] [US2] Extend `backend/tests/test_participant_submit.py` — assert `POST /api/queue/submit` response `status` is `queued` when `queue_mode=free` and `pending_review` when `queue_mode=moderated` (FR-013).

### Implementation for US2

- [x] T013 [US2] Extract shared `_enqueue_entry(db, entry)` from `approve_entry` in `backend/app/services/queue_service.py` (queue full, duplicate check, `queued` status, position, `_recompute_positions`, `emit_song_approved`).
- [x] T014 [US2] Add `_count_participant_queued` and **free** branch in `submit_as_participant` — create entry, enqueue via `_enqueue_entry`, apply queued cap instead of pending cap (FR-006, FR-007, FR-016, FR-017).
- [x] T015 [US2] Refactor `approve_entry` in `backend/app/services/queue_service.py` to delegate enqueue body to `_enqueue_entry` (no behavior change for moderated approve).

**Checkpoint**: Libre end-to-end on backend; US2 tests green.

---

## Phase 5: User Story 3 — Cambiar de modo durante el evento (Priority: P2)

**Goal**: Operator can persist mode changes; existing queue/pendings untouched; new submits follow active mode.

**Independent Test**: Toggle mode via API; queue/playing unchanged; legacy `pending_review` rows remain actionable; post-switch submits follow new mode without page reload (SSE revision bump).

### Tests for US3 (write first, must fail) ⚠️

- [x] T016 [P] [US3] Extend `backend/tests/test_queue_approval_mode.py` with mode-switch cases: legacy `pending_review` after switch to free remains actionable; **operator reject on legacy pending after switch to free → `rejected`, not in queue** (FR-008); queue positions unchanged; moderated resumption after switch back.
- [x] T017 [P] [US3] Extend `backend/tests/test_event_config.py` — `GET /api/event-config` includes `queue_mode` (covered by T005 schema); `PUT /api/event-config/queue-mode` auth 401, invalid enum 422, success persists + bumps revision.

### Implementation for US3

- [x] T018 [US3] Implement `PUT /api/event-config/queue-mode` in `backend/app/routers/event_config.py` — validate `QueueModeUpdate`, persist, `bump_revision(db)` for SSE `state` (FR-003, FR-004, FR-009, FR-010, FR-014).

**Checkpoint**: Mode API complete; switch semantics verified.

---

## Phase 6: User Story 4 — Selector visible en el panel de administración (Priority: P2)

**Goal**: Operator sees and changes mode in **Moderación** with Spanish labels and confirm dialog.

**Independent Test**: `/admin` → selector above pending table → confirm → mode persists after reload; Libre shows info message; cancel leaves mode unchanged.

### Implementation for US4

- [x] T019 [P] [US4] Add `queue_mode` and `QueueModeUpdate` types to `frontend/src/app/models/event-config.ts`.
- [x] T020 [P] [US4] Add `updateQueueMode(mode)` calling `PUT /api/event-config/queue-mode` in `frontend/src/app/services/event-config.service.ts`.
- [x] T021 [US4] Add mode selector (Moderado / Libre) above pending table and Libre info banner in `frontend/src/app/admin/admin.component.html` (FR-011, FR-012).
- [x] T022 [US4] Wire `queueMode` from `loadEventConfig()`, `window.confirm` dialog before `updateQueueMode` (per `research.md`), cancel revert, and error handling in `frontend/src/app/admin/admin.component.ts` (FR-019).
- [x] T023 [P] [US4] Extend `frontend/src/app/services/event-config.service.spec.ts` for `updateQueueMode` PUT path.

**Checkpoint**: Full operator UX for mode selection; FR-020 (no `/participar` indicator) satisfied by omission.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression, SDD closure, manual validation.

- [x] T024 [P] Run `pytest backend/tests/test_queue_approval_mode.py backend/tests/test_participant_submit.py backend/tests/test_notifications.py backend/tests/test_queue.py` and fix failures.
- [x] T025 [P] Run `npm --prefix frontend run build` and `npm --prefix frontend test` (include event-config spec).
- [x] T026 Execute manual validation per `specs/changes/013-queue-approval-mode/quickstart.md` (Phases 1–9), including **SC-002** kiosk timing (Phase 2b), **SC-001/SC-006** guided operator usability review (Phase 9).
- [x] T027 Update `specs/manifest.yml` change `013-queue-approval-mode` status to `implemented` and set `active.change: null` after merge.
- [x] T028 Finalize merged contract sections in `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` referencing change 013.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**.
- **US1 (Phase 3)**: Depends on Foundational — MVP (Moderado regression).
- **US2 (Phase 4)**: Depends on US1 moderated branch (T009) — adds free path; tests set `queue_mode=free` via **DB fixture** until T018 ships.
- **US3 (Phase 5)**: Depends on US2 submit branching — adds persistence API.
- **US4 (Phase 6)**: Depends on US3 `PUT /queue-mode` (T018) — frontend calls that endpoint.
- **Polish (Phase 7)**: Depends on US1–US4 complete.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 Moderado | Foundational | Submit → pending; approve → queue |
| US2 Libre | US1 branch | Submit → direct queue + toast |
| US3 Mode switch | US2 | Toggle mode; legacy pendings; new submit rule |
| US4 Admin UI | US3 API | Selector + confirm in `/admin` |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T004 ∥ T005 (after T003 migration file exists)
- **US1**: T008 test file scaffold ∥ T003–T007 if foundation done
- **US2**: T010 ∥ T011 ∥ T012 (tests); T019 ∥ T020 can start once API contract known (after T018)
- **Polish**: T024 ∥ T025

### Parallel Example: User Story 2

```bash
# Tests in parallel (after T009):
pytest backend/tests/test_queue_approval_mode.py  # T010
pytest backend/tests/test_notifications.py        # T011

# Then sequential implementation:
# T013 → T014 → T015 (same file queue_service.py)
```

### Parallel Example: User Story 4

```bash
# After T018 lands:
# T019 models/event-config.ts ∥ T020 event-config.service.ts
# Then T021 + T022 admin component (same feature area, sequential)
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1–2 (Setup + Foundational)
2. Complete Phase 3 (US1 — Moderado regression)
3. **STOP and VALIDATE**: `pytest backend/tests/test_queue_approval_mode.py -k moderated`
4. Ship-safe: no Libre yet, zero regression risk

### Incremental Delivery

1. Foundation → US1 (Moderado MVP)
2. US2 (Libre backend) → validate quickstart Phases 2–3
3. US3 (mode API + switch tests)
4. US4 (admin UI) → full operator workflow
5. Polish → contracts + manifest

### Suggested task counts

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | 2 | — |
| Foundational | 5 | — |
| US1 | 2 | Moderado P1 |
| US2 | 6 | Libre P1 |
| US3 | 3 | Mode switch P2 |
| US4 | 5 | Admin UI P2 |
| Polish | 5 | — |
| **Total** | **28** | |

---

## Notes

- API enum values: `moderated` / `free`; UI labels: **Moderado** / **Libre**.
- Do not add `queue_mode` to `EventConfigSummary` (participant/kiosk state).
- Reuse 429 detail `pending submission limit reached` for free-mode queued cap.
- **US2 tests**: set `queue_mode='free'` via DB fixture until `PUT /api/event-config/queue-mode` exists (T018); do not block US2 on US3.
- **T001 / T028**: intentional two-step contract merge (draft at start, finalize after validation per constitution IV).
- **GET `queue_mode`**: delivered by T005 schema + model column; verified in T017 — no standalone router task.
- `/participar`: no template changes if submit response `status` + SSE toasts suffice; FR-013 covered by T012 + T026.
- **SC-002** timing and **SC-001/SC-006** usability: manual gates in T026 / quickstart Phase 2b and Phase 9 (no automated perf/usability harness in scope).
