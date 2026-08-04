# Context Pack: 024-admin-queue-control

**Change id**: `024-admin-queue-control`  
**Branch**: `024-admin-queue-control`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `021-collapsible-panels-reset`, `017-admin-queue-history-filler` (queue ordering, skip), existing SSE

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — deletes vs played transitions
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — new queue admin routes + UI
5. [research.md](./research.md) — endpoint design, no auto-inject on vaciar

## Summary

**UX**: New **Cola de reproducción** panel after Moderación: full active queue list, **Iniciar/Saltar moved here**, vaciar, force play, edit votes, delete entry. Moderación = mode + pending only.

**Backend**: `GET/DELETE /api/queue/active`, `DELETE /api/queue/active/{id}`, `POST /api/queue/{id}/play-now`, `PATCH /api/queue/{id}/vote-count`. Hard delete for eliminar/vaciar; force-play interrupt → `played`. **No migration.**

## Key files (expected touch)

```text
backend/app/schemas.py                         # ActiveQueue*, VoteCountUpdateRequest
backend/app/services/queue_service.py          # list_active, clear_active, delete_active, play_now, set_vote_count
backend/app/routers/queue.py                   # new routes (order before /{id}/approve)
backend/tests/test_admin_queue_control.py      # NEW

frontend/src/app/models/jukebox-state.ts       # ActiveQueue types (or admin-queue.ts)
frontend/src/app/services/queue-admin.service.ts # new methods
frontend/src/app/admin/admin.component.{ts,html} # panel + move playback UI
frontend/src/app/admin/admin-queue.util.ts     # optional labels for source/status
```

## Contracts to merge at implement

- `specs/contracts/backend-api/contract.md` — active queue endpoints
- `specs/contracts/app-core/contract.md` — Cola de reproducción panel + Moderación trim

## Test focus

- Permanent delete removes submissions from stats/submissions list
- Force play marks interrupted as `played`, not deleted
- Vaciar does not trigger filler inject
- Skip/start only in queue panel HTML
