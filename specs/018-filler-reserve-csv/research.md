# Research: 018-filler-reserve-csv

**Date**: 2026-08-04

## R1 — Export delivery mechanism

**Decision**: `GET /api/filler-reserve/export` returns `text/csv; charset=utf-8` with `Content-Disposition: attachment` and UTF-8 BOM prefix (`\ufeff`) for Excel compatibility.

**Rationale**: Matches existing operator-authenticated JSON APIs; browser download via `HttpClient` `responseType: 'blob'` or `window.open` with session cookie. No new storage; stream from ordered `list_reserve()`.

**Alternatives considered**:
- Client-side CSV from `GET /api/filler-reserve` JSON — duplicates export format logic in Angular; rejected.
- JSON export — out of spec non-goals.

## R2 — Import: validate then commit (two steps)

**Decision**: Two operator endpoints on the same router:
1. `POST /api/filler-reserve/import/validate` — multipart file upload; full validation; no DB mutation.
2. `POST /api/filler-reserve/import` — same file upload; re-run identical validation; on success atomically replace reserve.

**Rationale**: Spec requires full preview validation (clarification Q5) and atomic apply (FR-006). Re-validation on commit avoids server-side preview tokens/TTL and guarantees commit matches latest queue/reserve state. Max 50 rows keeps double-validation acceptable (< SC-002 3 min budget).

**Alternatives considered**:
- Single-step import without preview — violates US3.
- Validate returns opaque `import_token` cached server-side — extra state, expiry edge cases; rejected for v1.

## R3 — Line-oriented file parsing (not strict CSV)

**Decision**: Parse upload as UTF-8 (with `utf-8-sig` for BOM). Split on `\n`/`\r\n`. Strip each line. Skip line 1 if trimmed lowercase equals `url`. Skip empty lines. Each remaining line is one `youtube_url_or_id` reference.

**Rationale**: Clarification Q4 — one URL per line; tolerant of Excel regional saves and plain-text editors.

**Alternatives considered**:
- `csv` module with comma delimiter — fails EU semicolon exports when URL is sole column anyway; unnecessary.
- Strict RFC 4180 — overkill for single-column URL list.

## R4 — Export URL canonical form

**Decision**: Always emit `https://www.youtube.com/watch?v={youtube_video_id}` from stored `FillerReserveEntry.youtube_video_id`.

**Rationale**: Clarification Q2; stable round-trip (SC-005).

## R5 — Empty import (clear reserve)

**Decision**: Validate returns `valid_count: 0`, `will_clear_reserve: true`, `can_confirm: true` when file has no data rows after parsing. Commit with zero rows deletes all reserve entries and returns empty list.

**Rationale**: Clarification Q1 — explicit operator confirmation to empty reserve.

## R6 — Replace semantics implementation

**Decision**: In one DB transaction: `DELETE FROM filler_reserve_entries`; insert new rows with `position` 1..N in file order; `bump_revision` once after commit.

**Rationale**: FR-005 replace-not-merge; simpler than diffing existing rows. Import does not touch active queue.

**Alternatives considered**:
- Upsert by video id — breaks explicit order replacement semantics.

## R7 — Validation reuse

**Decision**: Extract shared helpers in `filler_reserve_service.py`; reuse `_resolve_youtube_entry_fields` and active-queue conflict check (not `_has_video_conflict` as-is, which includes reserve table — use queue-only variant for import).

**Rationale**: FR-007 after analyze remediation: import replaces reserve; only within-file dupes and active queue matter.

## R8 — Frontend import UX

**Decision**: Hidden `<input type="file" accept=".csv,text/csv,text/plain">` in Admin reserve section. On select → `validateImport(file)` → modal with count, errors table (line + Spanish message), confirm/cancel. Confirm → `importReserve(file)` → refresh list via existing `refreshReserve()`.

**Rationale**: Fits existing Admin patterns (confirm dialogs for requeue, queue mode). No new routes.

## R9 — Error reporting

**Decision**: Validation errors return `{ line: number, detail: string }[]` using 1-based line numbers in original file. Map `detail` to Spanish in frontend for known codes (`invalid youtube reference`, `video already in queue`, `filler reserve is full`, duplicate in file).

**Rationale**: FR-009; aligns with existing `mapQueueError` pattern in admin component.

## R10 — Auth & scope

**Decision**: Operator session only (`CurrentUser`); participant → 401. No migration; no new tables.

**Rationale**: Extends 017 filler reserve; constitution VI `/api/*` prefix.
