# Implementation Plan: Paneles plegables y reinicio de historial

**Branch**: `021-collapsible-panels-reset` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/021-collapsible-panels-reset/spec.md`

## Summary

Reduce scroll fatigue in **Admin** and **Participate** with reusable **collapsible section** panels (default states per spec/clarifications). Reorder participant view: **Sonando ahora** (fixed strip) → **votos** → **enviar canciones** → **mis canciones**. Add operator action **Vaciar historial** via `DELETE /api/queue/history` (all `played` + `rejected` rows); SSE `state` propagates deletions to participant «Mis canciones». No migration.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, existing SSE/`bump_revision`, TailwindCSS, Angular standalone components

**Storage**: PostgreSQL `queue_entries` + `votes` (CASCADE); **no migration**

**Testing**: `backend/tests/test_queue_history.py` (clear history incl. filter scenario); `collapsible-section.component.spec.ts`; `participate.component.spec.ts` smoke; manual quickstart Phases 1–6; `npm --prefix frontend run build`

**Target Platform**: Docker Compose / K8s; operator `/admin`, participant `/participar`

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Panel toggle instant (client-only); history clear + SSE visible to participants within existing revision latency (< 3s typical)

**Constraints**: Spanish UI; `/api/*`; operator-only DELETE; modal confirm for vaciar historial; no localStorage for panel state; badges only on Moderación + Historial

**Scale/Scope**: ~1 new shared component; Admin + Participate template refactor; 1 new endpoint; ~150–250 LOC total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted for `backend-api`, `app-core` |
| V. Tests for changed behavior | Pass | `test_queue_history.py` + FE build/smoke |
| VI. Sibling conventions | Pass | `/api/*`, operator session, SSE `state`, Spanish UI |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/021-collapsible-panels-reset/
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
│   ├── routers/queue.py              # DELETE /history
│   └── services/queue_service.py     # clear_history()
└── tests/test_queue_history.py

frontend/
├── src/app/
│   ├── components/collapsible-section/
│   ├── admin/admin.component.{ts,html}
│   ├── participate/participate.component.{ts,html}
│   └── services/queue-admin.service.ts
```

**Structure Decision**: Shared UI primitive + layout refactor in two route components; single backend service function + router endpoint mirroring `DELETE /api/filler-reserve`.

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- `CollapsibleSectionComponent` (button + ARIA, not native `<details>`)
- In-memory panel state; no persistence
- `DELETE /api/queue/history` → 204 + `bump_revision`
- Modal confirm for vaciar historial
- Badges from `pending().length` and `historyTotal`
- SSE propagation via existing `state` handler + `refreshSubmissions()`

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`queue_service.clear_history(db) -> None`**

   ```python
   def clear_history(db: Session) -> None:
       db.execute(delete(QueueEntry).where(QueueEntry.status.in_(TERMINAL_STATUSES)))
       db.commit()
       bump_revision(db)
   ```

2. **`queue.py`**

   ```python
   @router.delete("/history", status_code=204)
   def clear_queue_history(_user: CurrentUser, db: Session = Depends(get_db)) -> None:
       queue_service.clear_history(db)
   ```

3. **Tests** (`test_queue_history.py`):
   - Operator → 204, terminal rows gone, active rows remain
   - Participant → 401
   - Idempotent second DELETE
   - Participant submissions list excludes deleted terminal entries

### Frontend design

1. **`CollapsibleSectionComponent`**
   - `@Input() title`, `expanded`, `badge?`
   - `@Output() expandedChange`
   - Header button toggles; content hidden when collapsed (`@if` or `[hidden]`)

2. **Admin**
   - Wrap each `<section>` in `app-collapsible-section`
   - Default map: `{ moderation: true, history: false, ... }`
   - Badges: `{{ pending().length }} pendiente(s)`, `{{ historyTotalAll }} entrada(s)` (unfiltered)
   - `displayState.state$` → `refreshPending()` + `refreshHistory()` + `historyTotalAll`
   - `pendingClearHistory` modal + `clearHistory()` → `QueueAdminService.clearHistory()`
   - Do not auto-expand moderation on SSE pending updates

3. **Participate**
   - Move `now_playing` block above votes, outside panels
   - Three panels with defaults per data-model.md
   - Merge submit sections + footer into «Enviar canciones» panel

4. **`QueueAdminService`**

   ```typescript
   clearHistory(): Observable<void> {
     return this.http.delete<void>(`${this.baseUrl}/queue/history`);
   }
   ```

## Phase 2 — Tasks (deferred)

Generated by `/speckit-tasks`. Suggested order:

1. Contract merge + manifest `active.change`
2. Backend `clear_history` + tests
3. `CollapsibleSectionComponent`
4. Admin panels + vaciar historial modal
5. Participate reorder + panels
6. `quickstart.md` manual validation

## Complexity Tracking

> No violations requiring justification.
