# Contract Deltas: 020-fill-queue-from-reserve

**Status**: implemented — merged into active contracts.

Modifies: `backend-api`, `app-core`. Builds on 017 auto-inject + 019 reserve management. Unless **changed**, prior contract behavior is unchanged.

---

## backend-api

### Auto-inject (changed from 017)

**Paths unchanged**. Toggle: `PUT /api/event-config/filler-auto-inject`.

**Behavior change**:

When `filler_auto_inject_enabled` and **zero** `queued` entries (regardless of whether `playing` exists):

1. Evaluate reserve in position order.
2. If candidate `youtube_video_id` is in active queue (`pending_review`, `queued`, `playing`) → **remove** that reserve row (no enqueue), continue with next position.
3. Otherwise transfer first valid candidate to queue as `queued`, `priority=low`, `source=auto_inject` (consume from reserve).
4. At most **one** successful inject per evaluation call.
5. Single `bump_revision` + SSE `state` per evaluation when reserve or queue changed (including duplicate-only removals with no inject).

**Idle path** (no `playing`, no `queued`): unchanged — inject then auto-start top `queued` per 014 (`_maybe_auto_start_playback` / `skip_or_advance`).

**Playing + empty queued**: inject only; do **not** interrupt `now_playing`.

**Triggers** (explicit mutations only; state GET does not inject):

- Queue lifecycle: `skip_or_advance`, `_maybe_auto_start_playback` when promotion leaves `playing` + 0 `queued`
- Reserve mutations (that do not enqueue): `add_to_reserve`, import/playlist commit, `reorder_reserve` (after persist)
- Config: `filler_auto_inject_enabled` set to `true` when previously `false`

**Not triggers**: `GET /api/state`; `reject_entry` (only `pending_review`); `transfer_to_queue` / manual reserve enqueue (adds to `queued` directly).

**Removed guard**: auto-inject no longer requires absence of `playing`.

### Tests (extend)

- `backend/tests/test_filler_reserve.py` — playing + empty queued inject, duplicate skip removes reserve row, toggle-on inject, GET state no side effect
- Regression: existing idle auto-inject tests pass

---

## app-core

### Kiosk display + participant queue (behavior note)

No API or component changes.

**Behavior**: When backend injects filler while a song is `playing`, kiosk queue strip and `/participar` queue list show the new `queued` entry on next SSE `state` merge (existing flow). No new admin UI.

### Admin (unchanged)

**Inyección automática** toggle semantics extended server-side; no label or binding changes.
