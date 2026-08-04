# Contract Deltas: 018-filler-reserve-csv

**Status**: draft — merge into active contracts at implementation.

Modifies: `backend-api`, `app-core`. Builds on 017 filler reserve. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### Filler reserve export (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/filler-reserve/export` | operator session | 200 `text/csv` attachment |

**Response body** (UTF-8 with BOM):

- Line 1: `url`
- Lines 2..N+1: `https://www.youtube.com/watch?v={VIDEO_ID}` in reserve `position` order
- Empty reserve: only `url` header line

**Headers**: `Content-Disposition: attachment; filename="filler-reserve-YYYY-MM-DD.csv"` (date = server UTC date).

Participant → **401**.

### Filler reserve import validate (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/filler-reserve/import/validate` | operator session | 200 `FillerReserveImportValidation` |

**Request**: `multipart/form-data` field `file` (`.csv` or plain text).

**Parsing**:

- UTF-8 / UTF-8-sig
- One URL per non-empty line; skip first line if `url` (case-insensitive)
- Accept full YouTube URL or 11-char video id

**Validation** (no DB writes): metadata resolvable, ≤50 rows, no duplicate video ids **within file**, no conflict with **active queue only** (`pending_review`, `queued`, `playing`). Rows matching videos already in the **current reserve** are allowed (import replaces reserve).

**Import `errors[].detail` codes** (stable; map to Spanish in Admin):

| `detail` | Meaning |
|----------|---------|
| `invalid youtube reference` | Line is not a valid YouTube URL/id or metadata unavailable |
| `duplicate in file` | Same `youtube_video_id` appears on an earlier line |
| `video already in queue` | Video exists in active queue (`pending_review`, `queued`, `playing`) |
| `filler reserve is full` | More than 50 valid lines after parsing |

**Response**:

```json
{
  "valid_count": 3,
  "will_clear_reserve": false,
  "can_confirm": true,
  "errors": []
}
```

| Field | Meaning |
|-------|---------|
| `valid_count` | Entries that will exist after import |
| `will_clear_reserve` | `true` when `valid_count == 0` |
| `can_confirm` | `false` when `errors` non-empty |
| `errors` | `{ "line": int, "detail": string }[]` — 1-based line numbers |

Participant → **401**.

### Filler reserve import commit (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/filler-reserve/import` | operator session | 200 `FillerReserveListResponse` |

**Request**: same `multipart/form-data` `file` as validate.

**Behavior**:

1. Re-run identical validation; if `can_confirm` is false → **422** with `errors` payload (no mutation).
2. Atomically **replace** entire reserve: delete all `filler_reserve_entries`, insert validated rows with `position` 1..N in file order.
3. `bump_revision` + SSE `state` (reserve not in public queue strip; revision bump for admin consistency).

Empty valid import (`valid_count == 0`) → reserve empty; **200** with `entries: []`.

| Case | Status | `detail` / body |
|------|--------|-----------------|
| Not authenticated | 401 | `not authenticated` |
| Validation errors | 422 | `errors` array in body |
| Success | 200 | `FillerReserveListResponse` |

Participant → **401**.

### Tests (constitution V)

- Extend `backend/tests/test_filler_reserve.py`:
  - Export order + header + canonical URL + UTF-8 BOM + empty reserve
  - Import validate: happy path, duplicate in file, queue conflict, **row matching current reserve allowed**, invalid URL, >50 rows, **`can_confirm` false + errors** (SC-006 API contract)
  - Import commit: atomic replace, re-validate on commit, empty clear, 401 participant, **GET list reflects new order without extra steps** (FR-011)
  - Round-trip export → import preserves order (SC-005)
- Frontend: optional service spec; `npm run build` required

---

## app-core

### Admin `/admin` — Reserva de relleno (changed)

Add to existing **Reserva de relleno** section (017):

| Control | Action |
|---------|--------|
| **Exportar CSV** | `GET /api/filler-reserve/export` → browser download |
| **Importar CSV** | file picker → validate → modal preview → confirm → `POST /api/filler-reserve/import` |

**Import modal** (Spanish):

- Shows `valid_count` and warning that current reserve will be **replaced**
- If `will_clear_reserve`: explicit «La reserva quedará vacía» + confirm
- If `errors.length > 0`: table (línea, motivo); confirm disabled
- Cancel leaves reserve unchanged

Extend `FillerReserveService` with `exportCsv`, `validateImport`, `importReserve`.

### Participar / kiosk

No changes.

---

## ops-platform

No topology changes.
