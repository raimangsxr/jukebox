# Context Pack: 017-admin-queue-history-filler

**Change id**: `017-admin-queue-history-filler`  
**Branch**: `017-admin-queue-history-filler`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`

## Read order

1. [spec.md](./spec.md) — requirements and clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — schema and DTOs
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — API/UI deltas
5. [research.md](./research.md) — design decisions
6. [analyze.md](./analyze.md) — remediation log (post-analyze)

## Summary

Admin gains **queue history** (played/rejected) with **re-queue**, plus a **filler reserve** (low-priority ambient tracks) with **auto-inject** on idle gaps and **operator direct enqueue** (bypass reserve). Single queue; sort: votes → priority (user before filler) → age. Re-queue always goes to `queued` (skips moderation).

## Key files (expected touch)

```text
backend/alembic/versions/0010_queue_history_filler.py
backend/app/models.py
backend/app/schemas.py
backend/app/services/queue_service.py
backend/app/services/filler_reserve_service.py   # new
backend/app/services/state_service.py
backend/app/routers/queue.py
backend/app/routers/filler_reserve.py            # new
backend/app/routers/event_config.py
backend/app/routers/youtube.py
backend/tests/test_queue_history.py
backend/tests/test_filler_reserve.py

frontend/src/app/admin/admin.component.{ts,html,css}
frontend/src/app/services/queue-admin.service.ts
frontend/src/app/services/filler-reserve.service.ts   # new
frontend/src/app/models/jukebox-state.ts
frontend/src/app/models/event-config.ts
```

## Clarifications locked

- Hybrid filler model (reserve + auto-inject + manual)
- Re-queue → `queued` always
- Reserve consume on transfer
- Filler votable in active queue
- Reserve manually reorderable

## Constitution reminders

- Update `specs/contracts/backend-api/contract.md` and `app-core` contract before implement
- Set `active.change` in `specs/manifest.yml` at implement start
- Tests required for history, reserve, priority order, auto-inject
