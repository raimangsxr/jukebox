---
description: "Task list for 018-filler-reserve-csv"
---

# Tasks: Exportar e importar reserva de relleno (CSV)

**Input**: Design documents from `specs/018-filler-reserve-csv/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/contract-deltas.md](./contracts/contract-deltas.md), [research.md](./research.md)

**Tests**: Included — constitution principle V and plan require extending `test_filler_reserve.py`.

**Organization**: Grouped by user story (US1–US3). US1/US2 = P1, US3 = P2. Depends on **017** filler reserve.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: owning user story (US1…US3)
- Paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: SDD scaffolding before code changes.

- [x] T001 [P] Merge `specs/018-filler-reserve-csv/contracts/contract-deltas.md` into `specs/contracts/backend-api/contract.md` and `specs/contracts/app-core/contract.md` (draft sections; finalize status in Polish).
- [x] T002 [P] Add change entry `018-filler-reserve-csv` to `specs/manifest.yml` with `status: draft`, `modifies: [backend-api, app-core]`, and set `active.change` + `active.context_pack` to this feature.

---

## Phase 2: User Story 1 — Exportar reserva a CSV (Priority: P1) 🎯 MVP

**Goal**: Operator downloads current filler reserve as CSV (`url` header + canonical watch URLs in position order).

**Independent Test**: Add 3 songs to reserve → **Exportar CSV** → file has header `url`, UTF-8 BOM, and URLs in same order as Admin; empty reserve exports header-only file.

> **Note**: US1 depends only on Phase 1 + **017** reserve — not on import foundational work (Phase 3).

### Tests for US1 (write first, must fail) ⚠️

- [x] T007 [P] [US1] Extend `backend/tests/test_filler_reserve.py` with export cases — header `url`, **UTF-8 BOM prefix**, canonical watch URLs in order, empty reserve header-only, `Content-Disposition` filename `filler-reserve-YYYY-MM-DD.csv`, operator auth required, participant 401 on `GET /api/filler-reserve/export`.

### Implementation for US1

- [x] T008 [US1] Implement `export_reserve_csv` (UTF-8 BOM + `url\n` + ordered watch URLs) in `backend/app/services/filler_reserve_service.py`.
- [x] T009 [US1] Add `GET /api/filler-reserve/export` (`text/csv`, `Content-Disposition: attachment; filename="filler-reserve-{UTC-date}.csv"`) in `backend/app/routers/filler_reserve.py`.
- [x] T010 [US1] Add `exportCsv()` in `frontend/src/app/services/filler-reserve.service.ts` and **Exportar CSV** button with blob download in `frontend/src/app/admin/admin.component.ts` and `frontend/src/app/admin/admin.component.html` (depends on T009).

**Checkpoint**: Export end-to-end; US1 export tests green.

---

## Phase 3: Foundational — Import shared logic (Blocking US2/US3)

**Purpose**: Parse, validate, and replace logic for import — **not required for US1 export**.

**⚠️ CRITICAL**: Complete before US2/US3 implementation.

- [x] T003 [P] Add `FillerReserveImportLineError`, `FillerReserveImportValidation` (and related response types) in `backend/app/schemas.py`.
- [x] T004 Implement `parse_import_file` (UTF-8-sig, one URL per line, skip `url` header, skip blanks) in `backend/app/services/filler_reserve_service.py`.
- [x] T005 Implement `validate_import_lines` in `backend/app/services/filler_reserve_service.py` — full metadata resolution, **duplicate-within-file** (`duplicate in file`), max 50 (`filler reserve is full`), **active-queue-only** conflict (`video already in queue`; **do not** reject rows matching current reserve DB rows), `will_clear_reserve` / `can_confirm` / `errors[]` with 1-based line numbers and stable `detail` codes per contract deltas.
- [x] T006 Implement `replace_reserve_from_import` in `backend/app/services/filler_reserve_service.py` — transactional delete-all + ordered insert, `bump_revision`.

**Checkpoint**: Parse/validate/replace unit-testable without routes.

---

## Phase 4: User Story 2 — Importar CSV a la reserva (Priority: P1)

**Goal**: Operator uploads CSV; system validates and atomically replaces reserve preserving file row order.

**Independent Test**: Export reserve → reorder lines in file → import via API → reserve order matches file; invalid row blocks import; row matching **previous** reserve content still allowed.

### Tests for US2 (write first, must fail) ⚠️

- [x] T011 [P] [US2] Extend `backend/tests/test_filler_reserve.py` with import cases — validate happy path, duplicate in file, queue conflict, **import row matching current reserve succeeds**, invalid URL, >50 rows, validate returns `can_confirm: false` + line errors (SC-006 API), atomic replace on failure, empty file clears reserve on commit, re-validate on commit (422 if invalid), participant 401 on import routes, **GET /api/filler-reserve list order after import** (FR-011 API), round-trip export→import order (SC-005).

### Implementation for US2

- [x] T012 [US2] Add `POST /api/filler-reserve/import/validate` (multipart `file`) in `backend/app/routers/filler_reserve.py`.
- [x] T013 [US2] Add `POST /api/filler-reserve/import` (multipart `file`, re-validate, replace or 422 with `errors` body) in `backend/app/routers/filler_reserve.py`.
- [x] T014 [P] [US2] Add `validateImport(file)` and `importReserve(file)` in `frontend/src/app/services/filler-reserve.service.ts`.

**Checkpoint**: Import API complete; US2 tests green.

---

## Phase 5: User Story 3 — Vista previa y confirmación (Priority: P2)

**Goal**: Operator sees validation summary, replacement warning, and line errors before confirming import.

**Independent Test**: Select file → preview shows `valid_count` and replace warning → invalid file shows errors with confirm disabled → cancel leaves reserve unchanged → confirm applies import and **reserve list updates without page reload** (FR-011).

### Tests for US3 (write first, must fail) ⚠️

- [x] T015a [P] [US3] Extend `backend/tests/test_filler_reserve.py` — validate endpoint returns all four `detail` codes with correct line numbers; `mapImportError` mapping covered via documented codes in `admin.component.ts` (manual UI check in T018 for SC-006).

### Implementation for US3

- [x] T015 [US3] Add import flow state (selected file, validation result, busy flags, confirm/cancel), `mapImportError` for all contract `detail` codes, and post-import `refreshReserve()` without full page reload in `frontend/src/app/admin/admin.component.ts`.
- [x] T016 [US3] Add hidden file input, **Importar CSV** button, and import preview/confirm modal (count, replace warning, `will_clear_reserve` empty warning, errors table, confirm disabled when `!can_confirm`) in `frontend/src/app/admin/admin.component.html`; wire to `validateImport` / `importReserve` and `refreshReserve()`.

**Checkpoint**: Full validate → confirm → import UX; SC-006 verified in quickstart Phase 2.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression, SDD closure, validation gates.

- [x] T017 [P] Finalize contract merge status and set `018-filler-reserve-csv` to `implemented` in `specs/manifest.yml`; clear or update `active.change`.
- [x] T018 Run `specs/018-filler-reserve-csv/quickstart.md` phases — include SC-001, SC-003, SC-005, **SC-006** (preview blocks confirm), **FR-011** (UI list refresh after import).
- [x] T019 [P] Run `pytest backend/tests/test_filler_reserve.py` and `npm --prefix frontend run build`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **US1 Export (Phase 2)**: Depends on Phase 1 + **017** only — **does not** wait for Phase 3.
- **Foundational Import (Phase 3)**: Depends on Phase 1 — blocks US2/US3 only.
- **US2 Import API (Phase 4)**: Depends on Phase 3.
- **US3 Preview UI (Phase 5)**: Depends on Phase 4 (validate/import endpoints + service client).
- **Polish (Phase 6)**: After desired user stories.

### User Story Dependencies

| Story | Depends on | Independent test |
|-------|------------|------------------|
| US1 Export | Phase 1 + 017 | Download CSV without import code |
| US2 Import | Phase 3 | API import via curl without modal |
| US3 Preview | Phase 4 | File picker + modal + confirm |

### Parallel Opportunities

- **Phase 1**: T001 ∥ T002
- **After Phase 1**: **US1 (Phase 2)** ∥ **Foundational import (Phase 3)** on different developers/files
- **Phase 3**: T003 ∥ T004; then T005 → T006 sequential
- **Phase 4**: T011 before T012–T013; T014 ∥ T012 after T011 contract known
- **Phase 5**: T015a ∥ T015 (different files)

### Parallel Example: After Phase 1

```bash
# Developer A — US1 export (MVP)
T007 → T008 → T009 → T010

# Developer B — import foundation (parallel)
T003 → T004 → T005 → T006
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2 (US1 export)
2. **STOP and VALIDATE** — export round-trip manually
3. Demo backup workflow; import can follow in Phase 3–5

### Incremental Delivery

1. Setup → US1 export (MVP)
2. Foundational import → US2 API
3. US3 preview modal
4. Polish

### Suggested MVP Scope

**Phases 1–2 only** — export CSV without import.

---

## Notes

- No Alembic migration — reuses `filler_reserve_entries` from 017.
- Import **replaces** entire reserve; empty file clears reserve only after explicit confirm.
- Validate **does not** reject rows because they exist in current reserve (FR-007).
- Total tasks: **20** (T001–T019, T015a).
