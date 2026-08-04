# Implementation Plan: Control de cola de reproducción en Admin

**Branch**: `024-admin-queue-control` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/024-admin-queue-control/spec.md`

## Summary

Add operator **Cola de reproducción** accordion on `/admin` (after Moderación, before Historial) with full active queue visibility and controls: **Iniciar reproducción** / **Saltar canción** (moved from Moderación), **Vaciar cola**, per-row **Forzar reproducir**, **Modificar votos**, **Eliminar**. Backend adds five operator routes under `/api/queue/*` for list/mutate active queue; eliminar/vaciar **hard-delete** rows; force-play interrupt marks previous **`played`**. List refreshes on expand + operator SSE `state`. **No Alembic migration**.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy, existing `CollapsibleSectionComponent`, `QueueAdminService`, `DisplayStateService` (SSE), TailwindCSS

**Storage**: PostgreSQL — existing `queue_entries`, `votes` (CASCADE), `jukebox_runtime`

**Testing**: `backend/tests/test_admin_queue_control.py`; manual [quickstart.md](./quickstart.md); `npm --prefix frontend run build`

**Target Platform**: Docker Compose / K8s; operator `/admin`

**Project Type**: Web application (FastAPI + Angular SPA)

**Performance Goals**: Mutations + UI update &lt; 5s (SC-002, SC-003); active list &lt; 100 queued rows typical

**Constraints**: Spanish UI; operator-only; confirm dialogs for eliminar + vaciar; permanent delete affects stats/submissions

**Scale/Scope**: ~5 new routes, ~6 service functions, 1 admin panel + Moderación trim; ~600–800 LOC; **no migration**

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | [contracts/contract-deltas.md](./contracts/contract-deltas.md); merge at implement |
| IV. Contract updates before implementation | Pass | Document new `/api/queue/active*` routes + admin panel layout |
| V. Tests for changed behavior | Pass | `test_admin_queue_control.py` + quickstart |
| VI. Sibling conventions | Pass | `/api/*`, operator session, Spanish UI, SSE `state` |

**Post-design re-check**: All gates pass. No migration; destructive deletes documented in contract.

## Project Structure

### Documentation (this feature)

```text
specs/024-admin-queue-control/
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
│   ├── schemas.py              # ActiveQueueListResponse, ActiveQueueEntryRead, VoteCountUpdateRequest
│   ├── services/queue_service.py  # list_active_queue, clear_active_queue, delete_active_entry,
│   │                              # force_play_entry, set_entry_vote_count
│   ├── routers/queue.py        # GET/DELETE /active, DELETE /active/{id}, play-now, vote-count
│   └── main.py                 # (no change if router already mounted)
└── tests/test_admin_queue_control.py

frontend/
├── src/app/
│   ├── models/jukebox-state.ts # or models/admin-queue.ts
│   ├── services/queue-admin.service.ts
│   └── admin/
│       ├── admin.component.{ts,html}   # new panel; remove playback from Moderación
│       └── admin-queue.util.ts          # optional source/status labels + spec
```

**Structure Decision**: Extend `queue_service` + `queue` router (same domain as skip/history); frontend extends existing `QueueAdminService` and admin accordion pattern from 021/023.

## Phase 0 — Research

See [research.md](./research.md). Resolved:

- `GET /api/queue/active` for full list (not `StateResponse` strip)
- Hard delete + vote CASCADE for eliminar/vaciar
- `play-now` → interrupt as `played`, not delete
- Admin `vote_count` PATCH without vote-limit / without new vote rows
- No filler auto-inject after vaciar
- SSE-driven refresh while panel expanded
- Playback buttons UI-only move; `POST /api/queue/skip` unchanged

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`queue_service.list_active_queue(db)` → `ActiveQueueListResponse`**
   - `now_playing` via `get_now_playing`
   - `queued` via `get_all_queued` (existing in `state_service`)
   - Map to `ActiveQueueEntryRead` with `_participant_display_names` + `source` from model

2. **`queue_service.clear_active_queue(db)`**
   - Collect ids `status IN (queued, playing)`
   - `runtime.now_playing_entry_id = None`
   - `delete(QueueEntry).where(id.in_(ids))` or status filter
   - `bump_revision` — **no** `maybe_inject_from_reserve`

3. **`queue_service.delete_active_entry(db, entry_id)`**
   - Validate `queued` or `playing`
   - If playing: clear runtime, after delete call shared `_promote_next_or_idle(db)` (reuse skip tail logic)
   - Hard delete row; `_recompute_positions` if needed

4. **`queue_service.force_play_entry(db, entry_id)`**
   - Target must be `queued`; if already playing same id → return state (no-op)
   - If other playing: mark `played` + `finished_at`
   - Promote target to `playing`, set runtime, `emit_song_up_next` when applicable
   - `_recompute_positions`, `bump_revision`

5. **`queue_service.set_entry_vote_count(db, entry_id, vote_count)`**
   - Validate ≥ 0, active status
   - `entry.vote_count = vote_count`; `_recompute_positions`; `bump_revision`

6. **`routers/queue.py`** — register `/active` routes before `/{entry_id}/approve`

### Frontend design

1. `AdminPanelId` add `'queue'`; `panelExpanded.queue = false`; insert panel **after** Moderación block, **before** Historial
2. Move HTML block (status + Iniciar + Saltar) from Moderación to Cola de reproducción
3. `QueueAdminService`: `getActiveQueue`, `clearActiveQueue`, `deleteActiveEntry`, `playNow`, `setVoteCount`
4. On `setPanelExpanded('queue', true)` → `loadActiveQueue()`; subscribe to `displayState.state$` while `panelExpanded.queue` → reload active list
5. Badge on header: `(now_playing ? 1 : 0) + queued.length` from active response or derived from SSE + last fetch
6. Confirm modals: eliminar (per row), vaciar cola (mirror historial vaciar pattern)
7. Vote edit: small modal or inline form per row
8. Row actions: Forzar reproducir (hide/disable if row is now_playing), Modificar votos, Eliminar

### User story mapping

| Story | Delivery |
|-------|----------|
| US1 Ver cola | `GET /api/queue/active` + panel list + SSE refresh |
| US1b Playback controls | Move UI; `skipOrStart()` in queue panel |
| US2 Vaciar cola | `DELETE /api/queue/active` + confirm |
| US3 Forzar reproducir | `POST play-now` |
| US4 Modificar votos | `PATCH vote-count` |
| US5 Eliminar | `DELETE active/{id}` + confirm |

## Complexity Tracking

No constitution violations.

## Next steps

1. `/speckit-tasks` — task breakdown
2. `/speckit-implement` — merge contracts, implement routes + panel, tests
