# Context Pack: 019-filler-reserve-playlist

**Change id**: `019-filler-reserve-playlist`  
**Branch**: `019-filler-reserve-playlist`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `017-admin-queue-history-filler`, `018-filler-reserve-csv`

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — batch validation DTOs
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — append import, playlist, clear
5. [research.md](./research.md) — playlist API, shared pipeline

## Summary

Operator can **build** filler reserve incrementally: **append** CSV imports (no longer replace), **add YouTube playlist** (or single video URL) with validate → preview → confirm, and **Vaciar** to clear all. Preview reports add count and skips (reserve, queue, unresolvable, capacity). Blocking errors: dupes in batch, invalid format, inaccessible playlist.

## Key files (expected touch)

```text
backend/app/schemas.py                           # BatchValidation, PlaylistRequest
backend/app/services/youtube_meta.py             # parse_playlist_id, fetch_playlist_video_ids
backend/app/services/filler_reserve_service.py   # batch pipeline, append, clear
backend/app/routers/filler_reserve.py            # playlist + DELETE clear; import behavior
backend/tests/test_filler_reserve.py             # append, playlist, clear tests

frontend/src/app/services/filler-reserve.service.ts
frontend/src/app/admin/admin.component.{ts,html}
```

## Clarifications locked

- Skip (not reject) for: in reserve, in queue, unresolvable, over capacity
- Append only what fits when over capacity
- Vaciar only via button; empty CSV does not clear
- Single video URL in playlist field → 1-item batch
- Blocking: dupes within batch (`duplicate in batch`), invalid format, bad playlist, >500 items

## Implementation notes

- Tasks implement US2 (CSV) before US1 (playlist) to validate shared batch pipeline first
- Shared batch preview modal (Phase 3 in tasks) built before wiring CSV/playlist
- Playlist fetch: paginate 50/page; cap 500 items; SC-001 budget ≤2 min for ~10 items

## Constitution reminders

- Merge contract deltas before implement
- Set `active.change` in `specs/manifest.yml`
- Extend `test_filler_reserve.py`; no new migration
