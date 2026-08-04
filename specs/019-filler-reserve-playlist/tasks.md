---
description: "Task list for 019-filler-reserve-playlist"
---

# Tasks: Construir reserva de relleno (playlist, CSV incremental y vaciar)

**Input**: Design documents from `specs/019-filler-reserve-playlist/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Included — constitution principle V and plan require extending `backend/tests/test_filler_reserve.py`.

**Organization**: Grouped by user story (US1–US4). US1/US2 = P1, US3/US4 = P2. Depends on **017** filler reserve + **018** CSV export (export unchanged).

**Phase sequencing note**: Spec lists US1 (playlist) before US2 (CSV) by priority, but tasks implement **US2 before US1** intentionally: CSV import refactor exercises the shared `validate_batch` + `append_reserve_entries` pipeline on the existing 018 import routes before adding playlist endpoints. Both are P1 and can run in parallel after Phase 3 (shared preview UI).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US4)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [X] T001 [P] Merge `specs/019-filler-reserve-playlist/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (draft sections; finalize status in Polish).
- [X] T002 [P] Add change entry `019-filler-reserve-playlist` to `specs/manifest.yml` with `status: draft`, `modifies: [backend-api, app-core]`, and set `active.change` + `active.context_pack` to this feature.

---

## Phase 2: Foundational — Backend (Blocking Prerequisites)

**Purpose**: Shared batch-append pipeline, playlist resolution, and API schemas — **required before all user stories**.

**⚠️ CRITICAL**: No user story backend work can begin until this phase is complete.

- [X] T003 [P] Add `FillerReserveBatchValidation`, `FillerReserveBatchLineError`, and `FillerReservePlaylistRequest` in `backend/app/schemas.py` (replace `FillerReserveImportValidation`; `add_count`, `skipped_*`; remove `will_clear_reserve`).
- [X] T004 [P] Add `parse_youtube_playlist_id`, `fetch_playlist_video_ids`, and `resolve_playlist_or_video_ids` in `backend/app/services/youtube_meta.py` (paginated `playlistItems.list` at 50 items/page; single-video URL → 1-item batch; reject >500 items with `playlist too large`; target SC-001 validate budget ≤2 min for ~10-item playlists).
- [X] T005 Implement `classify_batch_candidates` and `validate_batch` in `backend/app/services/filler_reserve_service.py` — skip vs blocking rules per `data-model.md` (reserve, queue, unresolvable, capacity; blocking dupes + invalid format).
- [X] T006 Implement `append_reserve_entries` and `clear_reserve` in `backend/app/services/filler_reserve_service.py` (append after `max(position)`; clear all + `bump_revision`).
- [X] T007 Add foundational batch-classification tests in `backend/tests/test_filler_reserve.py` after T005–T006 — all `skipped_*` counts including `skipped_unresolvable` (mock metadata), blocking `duplicate in batch`, `add_count == 0` → `can_confirm: false`.

**Checkpoint**: Batch pipeline unit-testable without routes.

---

## Phase 3: Foundational — Shared batch preview UI (Blocking US2/US1 frontend)

**Purpose**: Single preview modal for CSV and playlist (FR-007, SC-006) **before** wiring either source — avoids rework between US2/US1/US4.

**⚠️ CRITICAL**: Complete before Phase 4 and Phase 5 frontend tasks.

- [X] T008 [P] Add shared batch preview modal markup in `frontend/src/app/admin/admin.component.html` — `add_count`, all four `skipped_*` lines, blocking errors table, confirm disabled when `!can_confirm`; append copy (not replace); no `will_clear_reserve` UI.
- [X] T009 Implement shared batch modal state in `frontend/src/app/admin/admin.component.ts` — `batchSource: 'csv' | 'playlist'`, `mapBatchError` (including `playlist unavailable`, `playlist empty`, `playlist too large`, `duplicate in batch`), confirm/cancel handlers; update `FillerReserveBatchValidation` types in `frontend/src/app/services/filler-reserve.service.ts`.

**Checkpoint**: Modal ready to wire; SC-006 UI structure in place (pending data from CSV/playlist flows).

---

## Phase 4: User Story 2 — Importar CSV añadiendo al final (Priority: P1)

**Goal**: CSV import **appends** to reserve end; empty CSV does not clear; skip counts in validation response.

**Independent Test**: Reserve with 2 songs → import CSV with 3 new URLs → reserve has 5 (original order preserved, new at end); empty CSV → `can_confirm: false`, reserve unchanged.

**Checkpoint scope**: Backend append + CSV wired to shared modal. SC-006 satisfied via Phase 3 modal + this phase's API data.

### Tests for US2 (write first, must fail) ⚠️

- [X] T010 [P] [US2] Extend `backend/tests/test_filler_reserve.py` — append preserves existing rows; skip `skipped_in_reserve`, `skipped_in_queue`, `skipped_unresolvable` (mock), `skipped_capacity`; blocking `duplicate in batch` / `duplicate in file`; empty file `can_confirm: false` (no clear); `GET /api/filler-reserve` list order after import without extra steps (FR-010 API); update/remove 018 replace and `will_clear_reserve` assertions.

### Implementation for US2

- [X] T011 [US2] Refactor `validate_import_file` and `commit_import_file` in `backend/app/services/filler_reserve_service.py` to use `validate_batch` + `append_reserve_entries` (remove `replace_reserve_from_import` from import path).
- [X] T012 [US2] Update `POST /api/filler-reserve/import/validate` and `POST /api/filler-reserve/import` in `backend/app/routers/filler_reserve.py` to return `FillerReserveBatchValidation`.
- [X] T013 [US2] Wire CSV file picker and `validateImport` / `importReserve` to shared batch modal in `frontend/src/app/admin/admin.component.ts` and `frontend/src/app/admin/admin.component.html` (depends on T008–T009); call `refreshReserve()` on success (FR-010).

**Checkpoint**: CSV append end-to-end with full preview counts; US2 tests green.

---

## Phase 5: User Story 1 — Añadir playlist de YouTube a la reserva (Priority: P1) 🎯 MVP

**Goal**: Operator pastes playlist URL (or single video URL) → validate → confirm → songs appended in playlist order.

**Independent Test**: Reserve with 3 items → add playlist of 5 → 8 items; originals first, playlist order after; single `watch?v=` URL adds 1 item.

**Checkpoint scope**: Playlist API + UI wired to shared modal from Phase 3.

### Tests for US1 (write first, must fail) ⚠️

- [X] T014 [P] [US1] Extend `backend/tests/test_filler_reserve.py` — playlist validate/commit happy path (mock `fetch_playlist_video_ids`); single-video URL as 1-item batch; blocking `playlist unavailable`, `playlist empty`, `playlist too large` (>500 items mock); blocking `duplicate in batch` within playlist; participant 401 on playlist routes.

### Implementation for US1

- [X] T015 [US1] Implement `validate_playlist_url` and `commit_playlist_url` in `backend/app/services/filler_reserve_service.py` (resolve ids → `validate_batch` → append).
- [X] T016 [US1] Add `POST /api/filler-reserve/playlist/validate` and `POST /api/filler-reserve/playlist` in `backend/app/routers/filler_reserve.py` (JSON body, 422 on blocking errors).
- [X] T017 [P] [US1] Add `validatePlaylist` and `addPlaylist` in `frontend/src/app/services/filler-reserve.service.ts`.
- [X] T018 [US1] Add playlist URL input and **Añadir playlist** button; wire validate → shared batch modal (`batchSource='playlist'`) → commit in `frontend/src/app/admin/admin.component.ts` and `frontend/src/app/admin/admin.component.html` (depends on T008–T009); call `refreshReserve()` on success (FR-010).

**Checkpoint**: Playlist append end-to-end with full preview counts; US1 tests green.

---

## Phase 6: User Story 3 — Vaciar la reserva (Priority: P2)

**Goal**: Operator clears entire reserve with explicit confirmation; only path to empty reserve.

**Independent Test**: Reserve with items → **Vaciar** → confirm → empty; cancel → unchanged; button disabled when empty.

### Tests for US3 (write first, must fail) ⚠️

- [X] T019 [P] [US3] Extend `backend/tests/test_filler_reserve.py` — `DELETE /api/filler-reserve` clears all entries, `bump_revision`, participant 401, per-item `DELETE /{id}` still works.

### Implementation for US3

- [X] T020 [US3] Add `DELETE /api/filler-reserve` (collection clear, 204) **before** `DELETE /{entry_id}` in `backend/app/routers/filler_reserve.py` calling `clear_reserve`.
- [X] T021 [P] [US3] Add `clearReserve()` in `frontend/src/app/services/filler-reserve.service.ts`.
- [X] T022 [US3] Add **Vaciar** button with `confirm()` dialog, disabled when reserve empty, and `refreshReserve()` on success in `frontend/src/app/admin/admin.component.ts` and `frontend/src/app/admin/admin.component.html` (FR-010).

**Checkpoint**: Vaciar end-to-end; US3 tests green.

---

## Phase 7: User Story 4 — Vista previa y confirmación (Priority: P2)

**Goal**: Verify shared preview modal meets SC-006 for **both** CSV and playlist; no duplicate modal implementation.

**Independent Test**: Select CSV or playlist → preview shows new + all omitted breakdown → `add_count: 0` blocks confirm → cancel leaves reserve unchanged → list refreshes without page reload after confirm.

### Tests for US4 (write first, must fail) ⚠️

- [X] T023 [P] [US4] Extend `backend/tests/test_filler_reserve.py` — validate response includes all five counters (`add_count` + four `skipped_*`); `can_confirm: false` when `add_count == 0` without blocking errors (empty CSV); commit endpoints re-validate on commit.

### Verification for US4 (manual + automated)

- [X] T024 [US4] Document and execute SC-006 + FR-010 UI checks in `specs/019-filler-reserve-playlist/quickstart.md` Phase 7 — preview skip breakdown for CSV and playlist; confirm reserve list updates without page reload after import, playlist add, and vaciar.

**Checkpoint**: SC-006 and FR-010 verified for both batch sources.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Regression, SDD closure, validation gates.

- [X] T025 [P] Finalize contract merge status and set `019-filler-reserve-playlist` to `implemented` in `specs/manifest.yml`; update `AGENTS.md` active change note.
- [X] T026 Run `specs/019-filler-reserve-playlist/quickstart.md` Phases 1–7 — SC-001, SC-002, SC-003, SC-004, SC-006, FR-010.
- [X] T027 [P] Run `pytest backend/tests/test_filler_reserve.py` and `npm --prefix frontend run build` (includes 018 export regression).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational backend (Phase 2)**: Depends on Phase 1 — blocks all user story **backend** work.
- **Shared preview UI (Phase 3)**: Depends on T003 (types) — blocks US2/US1 **frontend** wiring.
- **US2 (Phase 4)**: Depends on Phase 2; frontend depends on Phase 3.
- **US1 (Phase 5)**: Depends on Phase 2; frontend depends on Phase 3; parallel with US2 after Phase 3.
- **US3 (Phase 6)**: Depends on Phase 2 (`clear_reserve`) only.
- **US4 (Phase 7)**: Depends on Phase 4 + Phase 5 complete (both sources wired).
- **Polish (Phase 8)**: Depends on Phases 4–7.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US2 CSV append | Phase 2 + Phase 3 (UI) | Append CSV with full preview |
| US1 Playlist | Phase 2 + Phase 3 (UI) | Playlist API + UI |
| US3 Vaciar | Phase 2 | Clear button only |
| US4 Preview verify | US2 + US1 wired | SC-006 + FR-010 both sources |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **Phase 2**: T003 ∥ T004; then T005 → T006 → T007 sequential
- **Phase 3**: T008 ∥ T009 (T009 includes service types)
- **After Phase 3**: US2 backend (T010–T012) ∥ US1 backend (T014–T016) ∥ US3 (T019–T022)
- **Polish**: T025 ∥ T027

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2 + **Phase 3** (shared modal)
2. Phase 5 US1 Playlist **or** Phase 4 US2 CSV (recommend both in same release)
3. STOP and validate per quickstart
4. US3 Vaciar + US4 verification + Polish

### Suggested release scope

Phase 1–3 + Phase 4 + Phase 5 minimum — changes 018 CSV semantics and adds playlist; include Phase 6–8 before merge.

---

## Notes

- Export (`GET /api/filler-reserve/export`) unchanged from 018 — regression in T027.
- Remove `replace_reserve_from_import` from import path after T011.
- Register `DELETE /api/filler-reserve` **before** `DELETE /{entry_id}` in router.
- Total tasks: **27** (T001–T027).
