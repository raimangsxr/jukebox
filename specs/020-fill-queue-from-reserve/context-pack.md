# Context Pack: 020-fill-queue-from-reserve

**Change id**: `020-fill-queue-from-reserve`  
**Branch**: `020-fill-queue-from-reserve`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `017-admin-queue-history-filler`, `019-filler-reserve-playlist`

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — inject evaluation state machine
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — auto-inject behavior change
5. [research.md](./research.md) — refactor + hook inventory

## Summary

Extend **auto-inject from filler reserve** so when **`queued` is empty** (even if `playing`), the next valid reserve song is transferred to the active queue. Skip active duplicates by **removing** them from reserve. Triggers: queue mutations, reserve mutations, enabling auto-inject toggle — **not** passive state GET. No frontend changes; no migration.

## Key files (expected touch)

```text
backend/app/services/filler_reserve_service.py   # maybe_inject_from_reserve + duplicate loop
backend/app/services/queue_service.py            # hooks after skip/auto-start/reject
backend/app/routers/event_config.py              # inject on toggle false→true
backend/app/routers/filler_reserve.py            # inject after reserve commits (if needed)
backend/tests/test_filler_reserve.py             # new playing+empty scenarios
```

## Clarifications locked

- Duplicate in reserve → remove and try next position
- Triggers: `skip_or_advance`, `_maybe_auto_start_playback`, reserve add/import/reorder, toggle-on (not `reject_entry`, not manual `transfer_to_queue`, not GET state)
- No inject on GET state
- Toggle enable → immediate eval
- One song per evaluation; no fill to `queue_visible_count`

## Constitution reminders

- Merge contract deltas before implement
- Set `active.change` in `specs/manifest.yml`
- Extend `test_filler_reserve.py`; no migration
