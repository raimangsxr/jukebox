# Data Model: 018-filler-reserve-csv

**Feature**: Export/import filler reserve as CSV (URL-per-line)  
**Depends on**: 017 `filler_reserve_entries` (no schema migration)

## Persistent entities (unchanged)

### `filler_reserve_entries` (017)

| Column | Notes |
|--------|-------|
| `id` | UUID PK |
| `youtube_video_id` | 11 chars; unique |
| `title`, `thumbnail_url`, `duration_sec` | From YouTube metadata on import/add |
| `original_query` | Source reference string |
| `position` | 1..N order; **import sets positions from file row order** |
| `created_at` | Set on insert |

**Import replace**: delete all rows → insert N new rows with sequential `position`.

**Export read**: `ORDER BY position ASC` → emit canonical watch URL per row.

## Transient / API DTOs (new)

### `ParsedImportLine` (internal)

| Field | Type | Description |
|-------|------|-------------|
| `line_number` | int | 1-based line in uploaded file |
| `raw` | str | Trimmed line text |
| `video_id` | str \| null | Resolved after parse step |

### `FillerReserveImportLineError`

| Field | Type | Description |
|-------|------|-------------|
| `line` | int | 1-based file line |
| `detail` | str | Machine code (mapped to Spanish in UI) |

### `FillerReserveImportValidation` (response)

| Field | Type | Description |
|-------|------|-------------|
| `valid_count` | int | Rows that will be imported |
| `will_clear_reserve` | bool | `true` when `valid_count == 0` |
| `can_confirm` | bool | `true` when no errors (includes empty clear) |
| `errors` | list[FillerReserveImportLineError] | Blocking errors |

### `FillerReserveImportResult` (response)

| Field | Type | Description |
|-------|------|-------------|
| `entries` | list[FillerReserveEntryRead] | Reserve after replace |

## Validation rules (import)

Applied per line in file order (same as 017 single add):

1. Parse YouTube id from line (URL or bare id).
2. Fetch metadata (`_resolve_youtube_entry_fields`); fail line if unavailable.
3. **Within file**: duplicate `youtube_video_id` → error on later line.
4. **Against active queue only**: video id in `pending_review`, `queued`, or `playing` → error. **Do not** check existing `filler_reserve_entries` rows (import replaces reserve; a row matching current reserve content is allowed).
5. **Count**: total valid lines ≤ `MAX_FILLER_RESERVE_ENTRIES` (50).

> **Note**: During replace, reserve table is cleared on commit; validation checks queue conflicts against active queue states only, not old reserve rows.

## Export file format

```text
url
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=jNQXAC9IVRw
```

- Row 1: header `url` (always).
- Rows 2..N+1: canonical watch URLs in position order.
- Empty reserve: file contains only `url` header line.
- Encoding: UTF-8 with BOM on export; import accepts UTF-8 / UTF-8-sig.

## State transitions

```text
[Reserve state A] --export--> CSV file (read-only snapshot)
CSV file --validate--> ValidationResult (no DB change)
CSV file --import (valid)--> [Reserve state B]  (atomic replace)
CSV file --import (invalid)--> [Reserve state A] (unchanged)
Empty file --import (confirmed)--> [Empty reserve]
```

## Frontend models

Extend `filler-reserve.service.ts`:

- `exportCsv(): Observable<Blob>`
- `validateImport(file: File): Observable<FillerReserveImportValidation>`
- `importReserve(file: File): Observable<FillerReserveListResponse>`

No changes to `jukebox-state.ts` queue models.
