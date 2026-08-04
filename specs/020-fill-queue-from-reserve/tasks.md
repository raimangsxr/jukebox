---
description: "Task list for 020-fill-queue-from-reserve"
---

# Tasks: Rellenar cola visible desde reserva

**Input**: Design documents from `specs/020-fill-queue-from-reserve/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Included — constitution principle V and plan require extending `backend/tests/test_filler_reserve.py`.

**Organization**: Grouped by user story (US1–US3). US1/US2 = P1, US3 = P2. Depends on **017** filler reserve + auto-inject. Backend-only; no migration.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US3)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [X] T001 [P] Merge `specs/020-fill-queue-from-reserve/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (draft Auto-inject section; finalize status in Polish).
- [X] T002 [P] Confirm change `020-fill-queue-from-reserve` in `specs/manifest.yml` has `status: planned`, `active.change` and `active.context_pack` pointing to this feature (no downgrade to `draft`).

---

## Phase 2: Foundational — Inject helper refactor (Blocking)

**Purpose**: Core `maybe_inject_from_reserve` with duplicate-removal loop — **required before all user stories**.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Refactor `inject_next_if_idle` → `maybe_inject_from_reserve` in `backend/app/services/filler_reserve_service.py` — remove `get_now_playing()` early-return; keep `_count_queued == 0` guard; loop reserve by position: active duplicate → delete row + renumber + continue; valid candidate → transfer (`source=auto_inject`, `priority=low`), enqueue; at end of evaluation call single `bump_revision` if reserve or queue changed (including duplicate-only removals with no inject); return entry or None (max one inject per call).
- [X] T004 Update all imports/call sites in `backend/app/services/queue_service.py` to use `maybe_inject_from_reserve` (retain behavior for idle path: inject then promote when no `playing`).

**Checkpoint**: Helper unit-testable in isolation; idle regression verified in Phase 4 (T012).

---

## Phase 3: User Story 1 — Cola visible con canción en reproducción (Priority: P1) 🎯 MVP

**Goal**: While `playing` and `queued` empty, auto-inject next valid reserve song to `queued` without interrupting playback.

**Independent Test**: One song `playing`, zero `queued`, reserve populated, auto-inject on → trigger mutation (e.g. `POST /api/filler-reserve` add) → kiosk `GET /api/state` shows ≥1 `queued` filler; `now_playing` unchanged.

### Tests for US1 (write first, must fail) ⚠️

- [X] T005 [P] [US1] Add `test_inject_while_playing_empty_queued` in `backend/tests/test_filler_reserve.py` — `playing` + reserve + `POST` add to reserve (or skip leaving playing alone) → one `queued` with `source=auto_inject`; `now_playing` id unchanged.
- [X] T006 [P] [US1] Add `test_inject_skips_duplicate_removes_reserve` in `backend/tests/test_filler_reserve.py` — reserve pos1 = same video as `playing`, pos2 = different → pos1 removed from reserve; pos2 injected to `queued`; reserve list revision/SSE updated.
- [X] T007 [P] [US1] Add `test_inject_disabled_while_playing` in `backend/tests/test_filler_reserve.py` — `filler_auto_inject_enabled=false`, playing + empty queued + reserve → mutation → no `queued` entries.
- [X] T008 [P] [US1] Add `test_inject_on_toggle_enable` in `backend/tests/test_filler_reserve.py` — auto-inject off, playing + empty queued + reserve → `PUT /api/event-config/filler-auto-inject` `{true}` → one `queued` with `source=auto_inject`.

### Implementation for US1

- [X] T009 [US1] After promoting to `playing` in `skip_or_advance` and `_maybe_auto_start_playback` in `backend/app/services/queue_service.py`, call `maybe_inject_from_reserve` when `_count_queued(db)==0` and `get_now_playing(db)` is not None (do not auto-start injected row). No hook on `reject_entry` (only affects `pending_review`; no dequeue API for `queued`).
- [X] T010 [US1] Call `maybe_inject_from_reserve` at end of `add_to_reserve`, `append_reserve_entries`, `reorder_reserve`, `commit_import_file`, and `commit_playlist_url` in `backend/app/services/filler_reserve_service.py` when `get_now_playing()` and zero `queued`. Do not hook `transfer_to_queue` (manual enqueue populates `queued` directly).
- [X] T011 [US1] On `PUT /api/event-config/filler-auto-inject` false→true in `backend/app/routers/event_config.py`, call `maybe_inject_from_reserve` once before final `bump_revision` when playing + empty queued + reserve available.

**Checkpoint**: US1 tests green (T005–T008); playing + empty queued fills visible strip via reserve/toggle triggers.

---

## Phase 4: User Story 2 — Hueco total sin reproducción (Priority: P1)

**Goal**: Preserve 017/014 idle auto-inject + auto-start when no `playing` and no `queued`.

**Independent Test**: Empty queue + reserve → `POST /api/queue/skip` → `now_playing` from reserve with `source=auto_inject`; reserve consumed.

### Tests for US2 ⚠️

- [X] T012 [P] [US2] Verify and fix `test_auto_inject_on_idle_skip`, `test_auto_inject_disabled`, `test_auto_inject_empty_reserve_noop` in `backend/tests/test_filler_reserve.py` after T003–T009 — idle inject + auto-start unchanged vs 017/014 baseline; disabled/empty reserve still noop (SC-002).

### Implementation for US2

- [X] T013 [US2] Confirm idle branch in `skip_or_advance` and `_maybe_auto_start_playback` in `backend/app/services/queue_service.py` still calls `maybe_inject_from_reserve` then promotes top `queued` to `playing` when no `now_playing` (regression guard; adjust only if refactor broke ordering).

**Checkpoint**: All prior auto-inject idle tests pass; US2 acceptance scenarios satisfied.

---

## Phase 5: User Story 3 — Participantes ven próximas canciones (Priority: P2)

**Goal**: Injected filler visible on participant queue list with normal vote rules (no UI change).

**Independent Test**: After US1 inject while playing → `GET /api/participant/state` (dev participant) lists injected song in `queue` ordered by vote rules.

### Tests for US3 ⚠️

- [X] T014 [US3] Add `test_participant_state_shows_injected_filler` in `backend/tests/test_filler_reserve.py` — playing + inject → participant state `queue` contains injected `youtube_video_id`; entry votable via existing vote path (optional smoke assert on `POST /api/votes`).

**Checkpoint**: US3 satisfied via existing SSE/state surfaces; no frontend tasks.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Non-mutation guard, validation, manifest hygiene.

- [X] T015 [P] Add `test_get_state_does_not_inject` in `backend/tests/test_filler_reserve.py` — playing + empty queued + reserve, auto-inject enabled → repeated `GET /api/state` does not create `queued` entries until explicit mutation.
- [X] T016 Run `pytest backend/tests/test_filler_reserve.py backend/tests/test_queue.py backend/tests/test_state.py` and `npm --prefix frontend run build`; execute quickstart Phases 1–2 in `specs/020-fill-queue-from-reserve/quickstart.md` for SC-001 functional timing (<3s manual observation).
- [X] T017 [P] Set `020-fill-queue-from-reserve` to `status: implemented` in `specs/manifest.yml`; set `active.change` to `null`; update `AGENTS.md` active change line.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **blocks all user stories**
- **US1 (Phase 3)**: Depends on Phase 2 — **MVP**
- **US2 (Phase 4)**: Depends on Phase 2; best after US1 queue hooks (T009)
- **US3 (Phase 5)**: Depends on US1 inject path (T010–T011)
- **Polish (Phase 6)**: Depends on US1–US3

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 (P1) | Phase 2 | playing + reserve → `queued` filler visible |
| US2 (P1) | Phase 2, T009 | idle skip → auto-inject + play |
| US3 (P2) | US1 | participant state lists injected filler |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 3 tests**: T005 ∥ T006 ∥ T007 ∥ T008 (after T003)
- **Phase 3 impl**: T010 can proceed after T003; T009 on `queue_service.py`; T011 on `event_config.py` in parallel after T003
- **Phase 6**: T015 ∥ T017 (after tests green)

### Parallel Example: US1 tests

```bash
# After T003, launch test stubs together:
# T005 test_inject_while_playing_empty_queued
# T006 test_inject_skips_duplicate_removes_reserve
# T007 test_inject_disabled_while_playing
# T008 test_inject_on_toggle_enable
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup
2. Phase 2 Foundational (T003–T004)
3. Phase 3 US1 tests → implementation (T005–T011)
4. **STOP and VALIDATE** quickstart Phase 1–2

### Incremental Delivery

1. Setup + Foundational → inject helper ready
2. US1 → visible queue while playing (**MVP**)
3. US2 → idle regression locked
4. US3 → participant visibility test
5. Polish → GET noop + manifest

### Task Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001–T002 | — |
| Foundational | T003–T004 | — |
| US1 | T005–T011 | 7 |
| US2 | T012–T013 | 2 |
| US3 | T014 | 1 |
| Polish | T015–T017 | — |
| **Total** | **17** | |

**MVP scope**: Phases 1–3 (T001–T011).  
**Parallel tasks**: 9 marked `[P]`.
