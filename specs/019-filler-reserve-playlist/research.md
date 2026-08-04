# Research: 019-filler-reserve-playlist

**Date**: 2026-08-04

## R1 — YouTube playlist resolution

**Decision**: Add `parse_youtube_playlist_id(url) -> str | None` and `fetch_playlist_video_ids(playlist_id, db) -> list[str]` in `youtube_meta.py` using YouTube Data API v3 `playlistItems.list` (`part=contentDetails`, `maxResults=50`, paginate with `pageToken`). Extract `contentDetails.videoId` per item; preserve playlist order.

**Rationale**: Project already uses `youtube/v3/videos` with API key pool and quota handling. `playlistItems.list` costs 1 quota unit per page (50 items). Reuses existing key rotation and exhaustion patterns from `fetch_youtube_videos_details_batch`.

**URL patterns** (operator copy-paste):

- `https://www.youtube.com/playlist?list=PL…`
- `https://www.youtube.com/watch?v=…&list=PL…` (use `list` param when present)
- Single video URL without `list` param → treat as **1-item batch** (clarification Q5), not playlist fetch

**Alternatives considered**:

- oEmbed / scraping playlist HTML — fragile, no ordering guarantee; rejected.
- `youtube-dl` / `yt-dlp` — new dependency, ops burden; rejected.

**Failure modes**:

- Private / deleted playlist → HTTP 404/403 from API → blocking error `playlist unavailable` (Spanish: «Playlist no disponible»).
- Empty playlist → blocking error `playlist empty`.

## R2 — Shared batch-append validation pipeline

**Decision**: Refactor `filler_reserve_service.py` to a single pipeline used by **CSV import** and **playlist add**:

```text
parse sources → classify candidates → batch metadata → build FillerReserveBatchValidation → commit append
```

**Rationale**: CSV and playlist share identical omission rules (clarifications Q1–Q3). One implementation prevents drift between import and playlist flows.

**Classification per candidate** (in source order):

| Condition | Action |
|-----------|--------|
| Invalid reference format (CSV) | **Blocking** error on line |
| Duplicate within batch | **Blocking** error |
| Already in `filler_reserve_entries` | **Skip** (`skipped_in_reserve`) |
| In active queue (`pending_review`, `queued`, `playing`) | **Skip** (`skipped_in_queue`) |
| Metadata not resolvable | **Skip** (`skipped_unresolvable`) |
| Would exceed `MAX_FILLER_RESERVE_ENTRIES` | **Skip** (`skipped_capacity`) |
| Otherwise | **Add** (`add_count`) |

**Blocking** aborts entire operation (no DB writes). **Skip** continues.

**Alternatives considered**:

- Separate validators for CSV vs playlist — duplicated logic; rejected.
- Keep 018 replace semantics with a flag — contradicts spec FR-003; rejected.

## R3 — CSV import semantics change (018 → 019)

**Decision**:

- `POST /import` and `/import/validate` **append** to end of reserve (`position = max+1..`).
- Remove `will_clear_reserve`; empty / zero-addable file → `can_confirm: false`, `add_count: 0`, no mutation.
- Update tests that asserted replace and empty-clear via CSV.

**Rationale**: Clarifications Q4 — only «Vaciar» clears reserve.

## R4 — Metadata resolution in preview (validate step)

**Decision**: **Validate endpoint resolves YouTube metadata** (batch) so preview can report `skipped_unresolvable` accurately (FR-007, SC-006). Accept slower preview for playlists (paginated fetch + batch videos API).

**Rationale**: 018 deferred metadata to commit only; 019 clarifications require omit counts in preview. Re-validate on commit remains (same as 018 R2).

**Alternatives considered**:

- Show unresolvable only after commit — violates FR-007; rejected.
- Fast validate without API + resolve on confirm only — cannot show skip counts; rejected.

## R5 — Clear reserve endpoint

**Decision**: `DELETE /api/filler-reserve` (collection delete, operator-only) deletes all `filler_reserve_entries`, `bump_revision`, returns **204**. Register route **before** `DELETE /{entry_id}` to avoid path conflicts.

**Rationale**: RESTful bulk delete; distinct from per-item delete. No migration.

**Alternatives considered**:

- `POST /clear` — works but less conventional; rejected.
- Reuse empty CSV import — explicitly ruled out in spec.

## R6 — Playlist API shape

**Decision**: JSON body endpoints (not multipart):

| Method | Path | Body |
|--------|------|------|
| POST | `/api/filler-reserve/playlist/validate` | `{ "youtube_playlist_url": "..." }` |
| POST | `/api/filler-reserve/playlist` | same |

Response: `FillerReserveBatchValidation` (shared with import validate after schema update).

**Rationale**: No file upload; URL string only. Mirrors validate → confirm pattern from CSV.

## R7 — Frontend UX

**Decision**:

- **Importar CSV** modal: copy changes from «sustituirá» to «se añadirán al final»; show skip breakdown; remove empty-clear warning.
- **Añadir playlist** control: URL text input + «Validar» / shared preview modal pattern with CSV (reuse modal component state with `batchSource: 'csv' | 'playlist'`).
- **Vaciar** button: `confirm()` Spanish warning → `DELETE /api/filler-reserve` → `refreshReserve()`; disabled when reserve empty.

**Rationale**: Minimal new UI; reuse existing modal and error mapping.

## R8 — Performance bounds

**Decision**: No hard timeout in v1; paginate playlist fetch until exhausted or API error. Document in quickstart that playlists >100 items may take several seconds on validate. Cap processing at first **500** playlist items for v1 with blocking error `playlist too large` if exceeded (defensive; typical operator playlists << 500).

**Rationale**: Spec SC-001 allows 2 min for 10-item playlist; very large playlists are edge case. 500 >> 50 reserve limit but allows skip classification.

**Alternatives considered**:

- No cap — risk of quota burn on 1000+ item playlists; soft cap preferred.

## R9 — Auth, contracts, tests

**Decision**: Operator session only; merge `contracts/contract-deltas.md` into active contracts before implement; extend `test_filler_reserve.py` for append, skip counts, playlist validate/commit (mock playlist API), clear, single-video URL; update 018 tests that assumed replace/clear.

**Rationale**: Constitution I, IV, V.
