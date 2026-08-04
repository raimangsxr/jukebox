# Context Pack: 021-collapsible-panels-reset

**Change id**: `021-collapsible-panels-reset`  
**Branch**: `021-collapsible-panels-reset`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `017-admin-queue-history-filler` (history API)

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — clear history + UI panel state
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — DELETE history + UI layout
5. [research.md](./research.md) — collapsible component + SSE propagation

## Summary

**UX**: Collapsible panels in Admin (only Moderación expanded by default; badges on Moderación + Historial) and Participate (votes → submit → mis canciones; Sonando ahora fixed strip). **Backend**: `DELETE /api/queue/history` wipes all terminal queue rows; `bump_revision` updates participants' Mis canciones via existing SSE.

## Key files (expected touch)

```text
backend/app/services/queue_service.py       # clear_history()
backend/app/routers/queue.py                  # DELETE /history
backend/tests/test_queue_history.py           # clear tests

frontend/src/app/components/collapsible-section/
frontend/src/app/admin/admin.component.{ts,html}   # panels, historyTotalAll, SSE refresh, vaciar modal
frontend/src/app/participate/participate.component.{ts,html}
frontend/src/app/services/queue-admin.service.ts
```

## Clarifications locked

- Clear history removes rows from participant «Mis canciones» too
- Sonando ahora: fixed strip before votes panel
- Badges: Moderación + Historial only
- No auto-expand Moderación on new pending
- Vaciar historial: modal confirm (not window.confirm)

## Constitution reminders

- Merge contract deltas before implement
- Set `active.change` in `specs/manifest.yml`
- Tests: `test_queue_history.py` + component smoke; no migration
