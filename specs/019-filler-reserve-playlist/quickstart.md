# Quickstart: 019-filler-reserve-playlist

Validation after implementation. Requires **017** filler reserve + **018** CSV export.

## Prerequisites

- Branch `019-filler-reserve-playlist`
- Operator session on `/admin`
- `JUKEBOX_YOUTUBE_API_KEYS` configured (playlist + metadata)
- Public YouTube playlist URL for manual test (5–10 items)

## Phase 1 — CSV append (US2)

1. Add 2 songs to reserve manually
2. Create CSV with 3 new URLs (different from existing)
3. **Importar CSV** → preview shows `add_count: 3`, append warning (not replace)
4. Confirm → reserve has 5 items; original 2 unchanged at top
5. Re-import CSV with 1 URL already in reserve → preview shows `skipped_in_reserve: 1`; confirm → no duplicate

## Phase 2 — CSV edge cases

1. Empty CSV (only `url` header) → `can_confirm: false`; reserve unchanged
2. Duplicate same video on two lines → blocking errors; reserve unchanged
3. Reserve at 48 items, import 5 new → preview `add_count: 2`, `skipped_capacity: 3`
4. Video in active queue in CSV → `skipped_in_queue`; others added

## Phase 3 — Playlist (US1)

1. Reserve with 3 items → paste playlist URL (5 videos) → **Añadir playlist**
2. Preview: `add_count: 5` (or skips if overlap)
3. Confirm → 8 items; playlist order after original 3
4. Paste single `watch?v=` URL → adds 1 video (or skips if duplicate)

## Phase 4 — Vaciar (US3)

1. Reserve with items → **Vaciar** → confirm → empty list
2. Cancel on confirm → unchanged
3. Empty reserve → **Vaciar** disabled

## Phase 5 — Export unchanged

1. Export after append → CSV order matches Admin UI
2. Round-trip: export → append import second file → combined order preserved

## Phase 6 — Preview + UI refresh (US4 / SC-006 / FR-010)

1. Import CSV with mixed skips → preview shows `add_count` and all four `skipped_*` counts before confirm
2. Add playlist with overlapping reserve entries → same skip breakdown visible
3. `add_count: 0` (e.g. empty CSV) → confirm disabled
4. After confirming CSV import, playlist add, or **Vaciar** → reserve list in Admin updates **without reloading the page** (FR-010)

## Phase 7 — Automated

```bash
pytest backend/tests/test_filler_reserve.py -k "import or playlist or clear or append"
npm --prefix frontend run build
```

## Manual API probe

```bash
# Validate playlist
curl -s -b operator.txt -H 'Content-Type: application/json' \
  -d '{"youtube_playlist_url":"https://www.youtube.com/playlist?list=PL..."}' \
  http://localhost:8000/api/filler-reserve/playlist/validate | jq

# Commit playlist
curl -s -b operator.txt -H 'Content-Type: application/json' \
  -d '{"youtube_playlist_url":"https://www.youtube.com/playlist?list=PL..."}' \
  http://localhost:8000/api/filler-reserve/playlist | jq

# Clear reserve
curl -s -b operator.txt -X DELETE http://localhost:8000/api/filler-reserve -w '%{http_code}\n'
```

## SC gates

| ID | Gate |
|----|------|
| SC-001 | Playlist 10 + reserve 5 → 15 items in order, < 2 min |
| SC-002 | Two CSV appends build combined list, < 5 min |
| SC-003 | Blocking error → reserve unchanged |
| SC-004 | Vaciar 20 items < 30 s |
| SC-006 | Preview shows add + all skip counts (CSV and playlist) |
| FR-010 | Reserve list refreshes without page reload after import, playlist, vaciar |

Document results in PR notes.
