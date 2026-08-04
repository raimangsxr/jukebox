# Context Pack: 023-admin-stats-panel

**Change id**: `023-admin-stats-panel`  
**Branch**: `023-admin-stats-panel`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `021-collapsible-panels-reset` (admin accordion), existing `participants` / `queue_entries` / `votes`

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — derived aggregates (no migration)
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — `GET /api/admin/stats` + admin UI
5. [research.md](./research.md) — endpoint vs client aggregation, tie-break, refresh UX

## Summary

**UX**: New collapsed **Estadísticas** panel on `/admin` (after Historial): participation totals, queue status counts, top-10 submitters/voters/songs. Load on expand + **Actualizar**; no SSE/polling.

**Backend**: `GET /api/admin/stats` (operator-only) with `AdminStatsResponse`; `stats_service.py` SQL aggregates. **No migration.**

## Key files (expected touch)

```text
backend/app/schemas.py                    # AdminStatsResponse, ranking DTOs
backend/app/services/stats_service.py     # NEW aggregation logic
backend/app/routers/admin_stats.py        # NEW or queue router mount
backend/tests/test_admin_stats.py

frontend/src/app/models/admin-stats.ts    # NEW types
frontend/src/app/services/admin-stats.service.ts
frontend/src/app/admin/admin.component.{ts,html}
frontend/src/app/admin/admin-stats.util.ts  # optional format helpers + spec
```

## Contracts to merge at implement

- `specs/contracts/backend-api/contract.md` — admin stats endpoint
- `specs/contracts/app-core/contract.md` — Estadísticas panel layout

## Out of scope

- Charts, CSV export, participant-facing stats, historical multi-event analytics
