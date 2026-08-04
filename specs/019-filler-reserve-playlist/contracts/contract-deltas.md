# Contract Deltas: 019-filler-reserve-playlist

**Status**: draft — merge into active contracts at implementation.

Modifies: `backend-api`, `app-core`. Builds on 017 filler reserve + 018 CSV export. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### Filler reserve CSV import (changed from 018)

**Paths unchanged**: `POST /api/filler-reserve/import/validate`, `POST /api/filler-reserve/import`

**Behavior change**:

- Import **appends** validated entries to end of reserve (`position` continues after current max).
- Does **not** replace or clear reserve.
- Empty file or zero addable entries → `can_confirm: false`; commit returns **422**; reserve unchanged.

**Response schema change** — `FillerReserveBatchValidation` (replaces `FillerReserveImportValidation`):

```json
{
  "add_count": 3,
  "skipped_in_reserve": 1,
  "skipped_in_queue": 0,
  "skipped_unresolvable": 0,
  "skipped_capacity": 2,
  "can_confirm": true,
  "errors": []
}
```

| Field | Meaning |
|-------|---------|
| `add_count` | Entries that will be appended on confirm |
| `skipped_in_reserve` | Duplicates already in reserve (omitted) |
| `skipped_in_queue` | In active queue / pending review (omitted) |
| `skipped_unresolvable` | Metadata unavailable (omitted) |
| `skipped_capacity` | Excess over max 50 (omitted) |
| `can_confirm` | `false` when blocking `errors` non-empty OR `add_count == 0` |
| `errors` | Blocking only: `{ "line": int, "detail": string }` |

**Removed**: `valid_count`, `will_clear_reserve`.

**Validation** (both validate and commit):

- Line-oriented CSV parsing unchanged (018).
- Within-file duplicate `youtube_video_id` → blocking.
- Invalid reference format → blocking.
- Rows already in reserve → skip (not error).
- Rows in active queue → skip (not error).
- Unresolvable metadata → skip.
- Append would exceed 50 total → skip excess in order.

**Import `errors[].detail` codes** (stable):

| `detail` | Meaning |
|----------|---------|
| `invalid youtube reference` | Line not valid YouTube URL/id |
| `duplicate in file` | Same video id earlier in CSV file (stable 018 alias) |
| `duplicate in batch` | Same video id earlier in playlist or CSV batch (canonical) |
| `playlist too large` | Playlist exceeds 500-item processing cap |
| `filler reserve is full` | **Removed** as blocking — use `skipped_capacity` instead |

Participant → **401**.

### Filler reserve playlist (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/filler-reserve/playlist/validate` | operator | 200 `FillerReserveBatchValidation` |
| POST | `/api/filler-reserve/playlist` | operator | 200 `FillerReserveListResponse` |

**Request body** (`application/json`):

```json
{ "youtube_playlist_url": "https://www.youtube.com/playlist?list=PL..." }
```

**Accepted URL formats** (`youtube_playlist_url`):

- `https://www.youtube.com/playlist?list=PL…`
- `https://www.youtube.com/watch?v=…&list=PL…`
- `https://youtu.be/…` with `list=PL…` query param when present
- Single video (no `list` param): `https://www.youtube.com/watch?v=…`, `https://youtu.be/…`, `https://www.youtube.com/shorts/…` → batch of 1 video (FR-009)

**Behavior**:

1. Parse playlist id from URL; if no playlist id but single video id present → batch of 1 video.
2. Fetch ordered video ids via YouTube `playlistItems.list` (paginated, 50 per page; max 500 items processed).
3. Run same batch validation / classification as CSV import (`line` = 1-based playlist index).
4. Validate: no DB writes. Commit: re-validate → append addable entries.

| Case | Status | Notes |
|------|--------|-------|
| Playlist unavailable | 422 / `errors` | `detail: playlist unavailable` |
| Playlist empty | 422 | `detail: playlist empty` |
| Playlist >500 items | 422 | `detail: playlist too large` |
| Zero addable after skips | 422 | `can_confirm: false`, `add_count: 0` |
| Success commit | 200 | Full reserve list |

Participant → **401**.

### Filler reserve clear (new)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| DELETE | `/api/filler-reserve` | operator | **204** No Content |

Deletes all `filler_reserve_entries`; `bump_revision`. Does not affect active queue or playback.

Participant → **401**.

### Export (unchanged from 018)

`GET /api/filler-reserve/export` — no change.

### Tests (constitution V)

Extend `backend/tests/test_filler_reserve.py`:

- CSV append: existing reserve preserved; new rows at end
- Skip counts: in reserve, in queue, unresolvable (mock), capacity partial
- CSV empty → `can_confirm: false`; reserve unchanged
- CSV duplicate in file → blocking; no mutation
- Playlist validate/commit: happy path, single-video URL, skip scenarios, `duplicate in batch`, `playlist too large` (>500 mock)
- `skipped_unresolvable` via metadata mock
- `GET /api/filler-reserve` list order after import/playlist commit (FR-010 API)
- `DELETE /api/filler-reserve` clear; 401 participant
- Update/remove 018 replace and `will_clear_reserve` assertions

---

## app-core

### Admin `/admin` — Reserva de relleno (changed)

| Control | Action |
|---------|--------|
| **Exportar CSV** | unchanged (018) |
| **Importar CSV** | validate → modal → append (not replace) |
| **Añadir playlist** (new) | URL input → validate → shared preview modal → commit |
| **Vaciar** (new) | confirm dialog → `DELETE /api/filler-reserve` |

**Import / playlist preview modal** (Spanish):

- «Se añadirán {add_count} canciones al final de la reserva»
- Omit summary: en reserva, en cola, no resolubles, por capacidad
- Blocking errors table; confirm disabled when `!can_confirm`
- No «sustituirá la reserva» / no «quedará vacía» on CSV

**Vaciar confirm**: «¿Vaciar toda la reserva de relleno? Esta acción no se puede deshacer.»

Extend `FillerReserveService`: `validatePlaylist`, `addPlaylist`, `clearReserve`; update `FillerReserveBatchValidation` type.

### Participar / kiosk

No changes.

---

## ops-platform

No topology changes. Playlist fetch uses existing `JUKEBOX_YOUTUBE_API_KEYS` quota.
