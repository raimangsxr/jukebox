# Context Pack: 022-limit-reset-countdown

**Change id**: `022-limit-reset-countdown`  
**Branch**: `022-limit-reset-countdown`  
**Status**: planned  
**Modifies**: `backend-api`, `app-core`  
**Depends on**: `016-participant-limits-ux` (limits ENV + participate labels)

## Read order

1. [spec.md](./spec.md) — requirements + clarifications (2026-08-04)
2. [plan.md](./plan.md) — implementation plan
3. [data-model.md](./data-model.md) — migration + window lifecycle
4. [contracts/contract-deltas.md](./contracts/contract-deltas.md) — API + UI deltas
5. [research.md](./research.md) — fixed window vs rolling, persistence

## Summary

**UX**: Live **MM:SS** countdown on `/participar` for votes (header) and searches (YouTube subsection) — «Cupo completo en MM:SS» from first consumption at full quota until window ends; auto-refresh at zero.

**Backend**: Replace rolling limits with **fixed 10-min windows**; `votes_quota_reset_at` / `searches_quota_reset_at` on `participants`; `participant_searches` table; extend `ParticipantStateResponse`.

## Key files (expected touch)

```text
backend/alembic/versions/*_limit_reset_windows.py
backend/app/models.py
backend/app/schemas.py
backend/app/services/limit_window_service.py
backend/app/services/vote_service.py
backend/app/services/search_rate_limiter.py   # DB-backed for participants
backend/app/services/state_service.py
backend/tests/test_limit_windows.py

frontend/src/app/models/jukebox-state.ts
frontend/src/app/limit-countdown.util.ts
frontend/src/app/participant-limits.util.ts
frontend/src/app/participate/participate.component.{ts,html,spec.ts}
frontend/src/app/services/participant-state.service.ts
```

## Clarifications locked

- Countdown from **first consume** even if quota partially left
- Placement: votes **header**, searches **Buscar en YouTube**
- Copy: «Cupo completo en MM:SS»; no «cada 10 min» when window inactive
- Searches show «X de Y búsquedas disponibles» persistently
- Auto `refresh()` at `00:00`
- SSE `state` → full `refresh()` for multi-tab (not partial merge)

## Constitution reminders

- Merge contract deltas before implement
- Set `active.change` in `specs/manifest.yml`
- Tests: `test_limit_windows.py`, `test_participant_submit.py`, FE util + participate specs, quickstart Phases 1–8
