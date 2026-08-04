# Implementation Plan: Construir reserva de relleno (playlist, CSV incremental y vaciar)

**Branch**: `019-filler-reserve-playlist` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/019-filler-reserve-playlist/spec.md`

## Summary

Extend operator **filler reserve** with **incremental batch append**: change CSV import from replace → append; add **YouTube playlist** import (validate → confirm → append) including single-video URL fallback; add **Vaciar** (`DELETE /api/filler-reserve`). Shared batch validation classifies each candidate as add vs skip (reserve / queue / unresolvable / capacity) with blocking errors only for intra-batch dupes, invalid format, and inaccessible playlist. Preview resolves YouTube metadata. No DB migration.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x; existing `filler_reserve_service`, `youtube_meta` (extend with `playlistItems.list`), `fetch_youtube_videos_details_batch`, `bump_revision`

**Storage**: Reuses `filler_reserve_entries` (017); no migration

**Testing**: Extend `backend/tests/test_filler_reserve.py` (append, skips, playlist mock, clear); update 018 replace/clear tests; `npm --prefix frontend run build`

**Target Platform**: Docker Compose / K8s; operator `/admin` only

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Playlist validate ≤ SC-001 (2 min for ~10 items); paginated playlist fetch; batch metadata in chunks of 50 video ids; soft cap 500 playlist items processed

**Constraints**: Spanish admin UI; `/api/*` prefix; operator-only; re-validate on commit; export CSV unchanged (018)

**Scale/Scope**: 3 new/changed endpoint groups; ~350 LOC backend service + youtube_meta; ~150 LOC frontend; breaking change to import validation JSON schema

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted for `backend-api`, `app-core` |
| V. Tests for changed behavior | Pass | Extend `test_filler_reserve.py`; update 018 assertions |
| VI. Sibling conventions | Pass | `/api/*`, operator session, Spanish UI |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/019-filler-reserve-playlist/
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
│   ├── schemas.py                         # FillerReserveBatchValidation, PlaylistRequest
│   ├── routers/
│   │   └── filler_reserve.py              # DELETE clear, playlist validate/commit
│   └── services/
│       ├── youtube_meta.py                # parse_playlist_id, fetch_playlist_video_ids
│       └── filler_reserve_service.py      # batch pipeline, append_reserve, clear_reserve
└── tests/
    └── test_filler_reserve.py               # append, playlist, clear, skip counts

frontend/src/app/
├── admin/
│   ├── admin.component.ts                 # playlist URL, vaciar, updated import modal
│   └── admin.component.html
└── services/
    └── filler-reserve.service.ts          # batch types, playlist, clearReserve
```

**Structure Decision**: Extend existing `filler_reserve` router/service; no new tables.

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- YouTube `playlistItems.list` pagination for ordered video ids
- Single-video URL → 1-item batch
- Shared batch validation with skip vs blocking classification
- CSV append replaces 018 replace semantics
- Metadata on validate for skip counts
- `DELETE /api/filler-reserve` for clear
- JSON playlist endpoints (validate + commit)

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`youtube_meta.py`**
   - `parse_youtube_playlist_id(url) -> str | None` — `list=PL…` param; ignore when only video without list
   - `resolve_playlist_or_video_ids(url) -> list[tuple[int, str, str]]` — `(index, video_id, raw)`; single video → `[(1, id, url)]`
   - `fetch_playlist_video_ids(playlist_id, db) -> list[str]` — paginate `playlistItems.list`

2. **`filler_reserve_service.py` — batch pipeline**
   - `classify_batch_candidates(db, candidates) -> BatchClassificationResult`
   - `validate_batch(db, candidates) -> FillerReserveBatchValidation` — includes metadata fetch
   - `append_reserve_entries(db, resolved: list[ResolvedImportEntry])` — positions after max
   - `clear_reserve(db)` — delete all + bump
   - Refactor `validate_import_file` / `commit_import_file` to use pipeline
   - `validate_playlist_url` / `commit_playlist_url`

3. **Routes** (`filler_reserve.py`) — order matters:
   - `DELETE ""` → clear (204)
   - `POST /playlist/validate` → JSON body
   - `POST /playlist` → validate + append or 422
   - Update import routes to return new validation schema

4. **Schema migration** (API only):
   - Replace `FillerReserveImportValidation` with `FillerReserveBatchValidation`
   - Add `FillerReservePlaylistRequest`

### Frontend design

1. **Types**: update `FillerReserveImportValidation` → `FillerReserveBatchValidation` with skip fields
2. **Import modal**: append copy; skip summary lines; remove `will_clear_reserve` UI
3. **Shared batch preview modal** (Phase 3 in tasks — before US2/US1 wiring): skip counts, `batchSource`, `mapBatchError`; satisfies FR-007/SC-006 upfront
4. **Playlist**: URL input + button → `validatePlaylist` → shared modal → `addPlaylist`
5. **Vaciar**: confirm → `clearReserve()` → `refreshReserve()`; disabled when `reserveEntries.length === 0`
6. **Error mapping**: add Spanish for `playlist unavailable`, `playlist empty`, `playlist too large`, `duplicate in batch`

### Error mapping (admin)

| `detail` | Spanish |
|----------|---------|
| `playlist unavailable` | Playlist no disponible |
| `playlist empty` | La playlist no tiene vídeos |
| `playlist too large` | La playlist supera el tamaño máximo procesable |
| (existing 018 codes) | unchanged |

## Phase 2 — Tasks

See [tasks.md](./tasks.md) — generate via `/speckit-tasks`.

Suggested task groups:

1. **Setup**: contract merge, manifest `active.change`
2. **Backend foundation**: youtube playlist fetch + batch pipeline + schemas
3. **Shared preview UI**: modal + skip counts before wiring CSV/playlist (FR-007, SC-006)
4. **US2 CSV append**: refactor import validate/commit + wire to modal
5. **US1 Playlist**: playlist endpoints + wire to modal
6. **US3 Vaciar**: DELETE clear + frontend button
7. **US4 Verify**: SC-006 + FR-010 checks (no duplicate modal work)
8. **Polish**: quickstart + manifest `implemented`

**Note**: Tasks implement US2 before US1 despite spec story order — CSV refactor validates the shared pipeline first; both are P1.

## Complexity Tracking

> No violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
