# Data Model: 019-filler-reserve-playlist

**Feature**: Incremental reserve build (playlist + CSV append + clear)  
**Depends on**: 017 `filler_reserve_entries`, 018 CSV export (unchanged export format)  
**Migration**: None

## Persistent entities (unchanged)

### `filler_reserve_entries` (017)

| Column | Notes |
|--------|-------|
| `id` | UUID PK |
| `youtube_video_id` | 11 chars; unique |
| `title`, `thumbnail_url`, `duration_sec` | From YouTube metadata on add/import/playlist |
| `original_query` | Source URL or line text |
| `position` | 1..N; **append assigns max(position)+1..** |
| `created_at` | Set on insert |

**Append**: insert new rows after `max(position)`; existing rows untouched.

**Clear**: delete all rows (`DELETE /api/filler-reserve`).

**Export** (018, unchanged): `ORDER BY position ASC` → CSV with `url` header.

## Transient / API DTOs

### `BatchCandidate` (internal)

| Field | Type | Description |
|-------|------|-------------|
| `index` | int | 1-based position in source (CSV line or playlist order) |
| `raw` | str | Original reference string |
| `video_id` | str \| null | Parsed id after format step |

### `FillerReserveBatchValidation` (replaces extended import validation)

| Field | Type | Description |
|-------|------|-------------|
| `add_count` | int | New entries that will be appended |
| `skipped_in_reserve` | int | Already in reserve |
| `skipped_in_queue` | int | In active queue / pending review |
| `skipped_unresolvable` | int | Valid format but metadata missing |
| `skipped_capacity` | int | Would exceed max 50 |
| `can_confirm` | bool | `false` if blocking errors OR `add_count == 0` |
| `errors` | list[FillerReserveBatchLineError] | Blocking errors only |

> **Breaking change from 018**: `valid_count` → `add_count`; remove `will_clear_reserve`.

### `FillerReserveBatchLineError`

| Field | Type | Description |
|-------|------|-------------|
| `line` | int | 1-based index in CSV file or playlist order |
| `detail` | str | Machine code (Spanish mapping in Admin) |

**New `detail` codes**:

| `detail` | Meaning |
|----------|---------|
| `playlist unavailable` | Playlist id invalid or API cannot access |
| `playlist empty` | Playlist has zero items |
| `playlist too large` | Exceeds v1 processing cap (500 items) |

Blocking duplicate code: **`duplicate in batch`** (canonical for CSV and playlist). CSV API may also emit stable 018 alias **`duplicate in file`** for the same condition.

### `FillerReservePlaylistRequest`

| Field | Type | Description |
|-------|------|-------------|
| `youtube_playlist_url` | str | Playlist or single-video URL (max 500 chars) |

## Validation rules (batch append)

Applied in **source order** (CSV lines or playlist items):

1. **Format**: CSV line must parse to video id; playlist URL must parse to playlist id OR single video id.
2. **Within batch**: duplicate `youtube_video_id` → blocking error on later index (`duplicate in batch`; CSV may also emit `duplicate in file`).
3. **Reserve**: id in `filler_reserve_entries` → skip (`skipped_in_reserve`).
4. **Active queue**: id in `pending_review` \| `queued` \| `playing` → skip (`skipped_in_queue`).
5. **Metadata**: batch `fetch_youtube_videos_details_batch`; missing id → skip (`skipped_unresolvable`).
6. **Capacity**: if `current_count + addable_so_far >= 50` → skip (`skipped_capacity`).
7. **Zero addable** after classification → `can_confirm: false` (not blocking error list unless also format errors).

**Blocking** (no DB write): steps 1–2 failures; playlist inaccessible/empty/too large.

## State transitions

```text
[Reserve N items]
  --playlist/CSV validate--> BatchValidation (no DB change)
  --playlist/CSV commit (can_confirm)--> [Reserve N+add_count items]
  --blocking error--> [Reserve N items] unchanged
  --DELETE clear--> [Reserve 0 items]
```

```text
CSV file --import (018)--> REPLACE reserve
CSV file --import (019)--> APPEND to reserve
```

## Frontend models

Extend `filler-reserve.service.ts`:

- `FillerReserveBatchValidation` (updated fields)
- `validatePlaylist(url): Observable<FillerReserveBatchValidation>`
- `addPlaylist(url): Observable<FillerReserveListResponse>`
- `clearReserve(): Observable<void>`

Admin modal state: `batchSource: 'csv' | 'playlist'`, shared preview UI.
