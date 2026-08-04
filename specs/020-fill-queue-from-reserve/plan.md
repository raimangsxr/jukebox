# Implementation Plan: Rellenar cola visible desde reserva

**Branch**: `020-fill-queue-from-reserve` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-fill-queue-from-reserve/spec.md`

## Summary

Extend **auto-inject from filler reserve** (017) so it runs whenever **`queued` count is zero**, including while a song is **`playing`**. Injected entries stay in `queued` (visible strip / participant list) without interrupting playback. Active duplicates at the front of reserve are **removed** from reserve and skipped. Evaluation is **event-driven** on queue mutations, reserve mutations, and enabling the auto-inject toggle — not on passive state GET. Backend-only change; no migration; extend `test_filler_reserve.py`.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: Existing `filler_reserve_service`, `queue_service`, `state_service`, `_has_active_duplicate`, `bump_revision`, SSE

**Storage**: Reuses 017 tables; **no migration**

**Testing**: Extend `backend/tests/test_filler_reserve.py`; regression `test_queue.py`, `test_state.py`; `npm --prefix frontend run build` (no FE changes)

**Target Platform**: Docker Compose / K8s; kiosk `/`, participant `/participar`, operator `/admin`

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Injected `queued` entry visible via SSE within SC-001 (< 3s from triggering mutation)

**Constraints**: Spanish UI unchanged; `/api/*`; reuse `filler_auto_inject_enabled` toggle; max 1 inject per evaluation; no inject on GET state

**Scale/Scope**: ~80 LOC backend refactor + hook calls; 0 frontend; contract delta for auto-inject section only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted for `backend-api`, `app-core` |
| V. Tests for changed behavior | Pass | Extend `test_filler_reserve.py` + idle regression |
| VI. Sibling conventions | Pass | `/api/*`, SSE `state`, no new endpoints |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/020-fill-queue-from-reserve/
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
│   ├── routers/
│   │   └── event_config.py                # inject on filler-auto-inject false→true
│   └── services/
│       ├── filler_reserve_service.py      # maybe_inject_from_reserve (rename/refactor)
│       └── queue_service.py               # post-mutation hooks
└── tests/
    └── test_filler_reserve.py             # playing+empty queued, duplicate skip, toggle, GET noop

frontend/                                  # no changes
```

**Structure Decision**: Single behavioral change in `filler_reserve_service` with hook calls from `queue_service` and `event_config`; reserve router may call shared helper after append/reorder if not already covered by service layer.

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- Remove `playing` guard from inject helper
- Duplicate loop: delete from reserve + continue
- Event-driven hook inventory (queue, reserve, toggle-on)
- No GET-side effects
- No frontend / migration

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`filler_reserve_service.py` — refactor inject**

   Rename `inject_next_if_idle` → `maybe_inject_from_reserve(db) -> QueueEntry | None`:

   ```python
   def maybe_inject_from_reserve(db: Session) -> QueueEntry | None:
       if not config.filler_auto_inject_enabled: return None
       if _count_queued(db) > 0: return None
       changed = False
       while True:
           reserve_entry = first_by_position()
           if reserve_entry is None:
               if changed: bump_revision(db)
               return None
           if _has_active_duplicate(db, reserve_entry.youtube_video_id):
               db.delete(reserve_entry); renumber; changed = True; continue
           # transfer one, enqueue; changed = True; bump_revision once; return entry
   ```

   Keep thin alias `inject_next_if_idle = maybe_inject_from_reserve` temporarily if needed for minimal diff, or update all call sites.

2. **`queue_service.py` — hooks**

   - `_maybe_auto_start_playback`: after promoting to `playing`, if `_count_queued() == 0`, call `maybe_inject_from_reserve` (does not auto-start injected row while another plays).
   - `skip_or_advance`: after promoting next to `playing`, if `_count_queued() == 0`, call `maybe_inject_from_reserve`.
   - Idle path unchanged: inject then promote when no `playing`.
   - No hook on `reject_entry` (only `pending_review`; no dequeue API for `queued`).

3. **`filler_reserve_service.py` — reserve mutations**

   At end of `add_to_reserve`, `append_reserve_entries`, `reorder_reserve`, import/playlist commit wrappers: call `maybe_inject_from_reserve` if `get_now_playing()` and zero queued. Skip `transfer_to_queue` (manual enqueue fills `queued` directly).

4. **`event_config.py`**

   In `update_filler_auto_inject`: if `payload.filler_auto_inject_enabled` and was previously `False`, call `maybe_inject_from_reserve(db)` before/after `bump_revision` (single revision bump).

5. **Explicit non-triggers**

   Do not call from `build_state_response`, `get_event_config`, or read-only routes.

### Frontend design

No changes. Existing SSE merge surfaces new `queued` entries on kiosk and `/participar`.

### Test plan

| Test | Assert |
|------|--------|
| `test_inject_while_playing_empty_queued` | playing + reserve → mutation → 1 `queued` auto_inject |
| `test_inject_skips_duplicate_removes_reserve` | reserve[1]=playing video → removed; reserve[2] injected |
| `test_inject_on_toggle_enable` | PUT filler-auto-inject true → queued populated |
| `test_get_state_does_not_inject` | GET /api/state count unchanged without mutation |
| `test_auto_inject_on_idle_skip` | existing — still passes |

## Phase 2 — Tasks

See [tasks.md](./tasks.md) (17 tasks; analysis remediation applied 2026-08-04).

## Complexity Tracking

> No violations.
