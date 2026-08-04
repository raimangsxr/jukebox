# Implementation Plan: Exportar e importar reserva de relleno (CSV)

**Branch**: `018-filler-reserve-csv` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-filler-reserve-csv/spec.md`

## Summary

Extend operator **filler reserve** (017) with **CSV export** and **import** (validate → confirm → atomic replace). Export: UTF-8 CSV with header `url` and canonical `https://www.youtube.com/watch?v=…` rows in position order. Import: line-oriented parsing (one URL per line), full validation in preview (YouTube metadata, duplicates, queue conflicts, max 50), then replace entire reserve on commit. Empty file clears reserve only after explicit confirmation. No DB migration.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x; existing `filler_reserve_service`, `queue_service._resolve_youtube_entry_fields`, `queue_service._has_video_conflict`, `bump_revision`

**Storage**: Reuses `filler_reserve_entries` (017); no migration

**Testing**: Extend `backend/tests/test_filler_reserve.py` (export, validate, import, round-trip); `npm --prefix frontend run build`

**Target Platform**: Docker Compose / K8s; operator `/admin` only

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Export instant for ≤50 rows; validate+import ≤50 URLs within SC-002 (3 min including UI); preview validation may take seconds due to YouTube metadata fan-out

**Constraints**: Spanish admin UI; `/api/*` prefix; operator-only; atomic replace; re-validate on commit; UTF-8 BOM on export for Excel

**Scale/Scope**: 3 new endpoints on existing router; ~200 LOC service + ~100 LOC frontend; no schema change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted for `backend-api`, `app-core` |
| V. Tests for changed behavior | Pass | Extend `test_filler_reserve.py` |
| VI. Sibling conventions | Pass | `/api/*`, operator session, Spanish UI |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/018-filler-reserve-csv/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── contracts/contract-deltas.md
└── tasks.md                    # Phase 2 — /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── schemas.py                         # FillerReserveImportValidation, errors
│   ├── routers/
│   │   └── filler_reserve.py            # GET export, POST import/validate, POST import
│   └── services/
│       └── filler_reserve_service.py      # parse_import_file, validate, replace, export_csv
└── tests/
    └── test_filler_reserve.py             # export/import/round-trip cases

frontend/src/app/
├── admin/
│   ├── admin.component.ts                 # export button, import modal
│   └── admin.component.html
└── services/
    └── filler-reserve.service.ts          # exportCsv, validateImport, importReserve
```

**Structure Decision**: Extend existing `filler_reserve` router/service from 017; no new tables or routers.

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- GET CSV export with BOM + attachment disposition
- Two-step validate/commit with re-validation on commit
- Line-oriented parser (not strict CSV)
- Canonical watch URL on export
- Transactional delete-all + insert ordered rows on import
- Shared validation with 017 add-to-reserve rules

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`parse_import_file(content: bytes) -> list[ParsedImportLine]`**
   - `utf-8-sig` decode; split lines; strip; skip header `url`; skip blanks

2. **`validate_import_lines(db, lines) -> FillerReserveImportValidation`**
   - For each line in order: parse video id → resolve metadata → track seen ids (dup in file → `duplicate in file`) → check active queue only (`video already in queue`)
   - **Do not** reject rows matching current `filler_reserve_entries` (replace semantics)
   - Count ≤ 50; collect errors with 1-based line numbers
   - Set `will_clear_reserve`, `can_confirm`

3. **`replace_reserve_from_import(db, resolved: list[ResolvedImportEntry])`**
   - Transaction: delete all `FillerReserveEntry`; insert with positions 1..N; `bump_revision`

4. **`export_reserve_csv(db) -> bytes`**
   - BOM + `url\n` + `\n`.join(watch URLs from `list_reserve()`)

5. **Routes** (`filler_reserve.py`):
   - `GET /export` → `Response(content=..., media_type="text/csv", headers=Content-Disposition: attachment; filename="filler-reserve-{UTC-date}.csv")`
   - `POST /import/validate` → `UploadFile`
   - `POST /import` → `UploadFile` → validate → replace or 422

### Frontend design

1. **Export**: `exportCsv()` → blob download via temporary `<a download>` or `HttpClient` blob + `URL.createObjectURL`
2. **Import**: hidden file input → `validateImport(file)` → modal:
   - Success: show count + replace warning (+ empty warning if `will_clear_reserve`)
   - Errors: table line/motivo; disable confirm
3. **Confirm**: `importReserve(file)` → `refreshReserve()`; close modal
4. Spanish labels: «Exportar CSV», «Importar CSV», modal copy per contract deltas

### Error mapping (admin)

| `detail` | Spanish |
|----------|---------|
| `invalid youtube reference` | Referencia de YouTube no válida |
| `video already in queue` | Ese vídeo ya está en la cola activa |
| `duplicate in file` | Vídeo duplicado en el fichero |
| `filler reserve is full` | El fichero supera el máximo de 50 canciones |

## Phase 2 — Tasks

See [tasks.md](./tasks.md). MVP = **Phases 1–2** (export only); import foundation (Phase 3) parallelizable with US1.

Suggested task groups:

1. **Setup**: contract merge, manifest `active.change`
2. **US1 Export**: export service, route, frontend button (no import deps)
3. **Import foundation**: parse, validate, replace
4. **US2/US3**: import API + preview modal
5. **Polish**: quickstart + manifest `implemented`

## Complexity Tracking

> No violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
