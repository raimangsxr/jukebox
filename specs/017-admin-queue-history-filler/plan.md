# Implementation Plan: Historial de cola y canciones de relleno en Admin

**Branch**: `017-admin-queue-history-filler` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-admin-queue-history-filler/spec.md`

## Summary

Add operator **queue history** (`played` / `rejected`) with one-click **re-queue**, a separate **filler reserve** with manual reorder and consume-on-transfer, and **auto-inject** when playback is idle and the active queue is empty. Extend `queue_entries` with `priority`, `source`, and `finished_at`; update queue ordering to prefer `normal` over `low` on vote ties. Admin UI: new **Historial** and **Reserva de relleno** sections plus auto-inject toggle. Participants see filler only once in the public queue (no badge); filler entries remain votable.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL; Angular standalone, TailwindCSS; existing `queue_service`, `state_service`, `event_config` router, SSE `bump_revision`, YouTube search/metadata

**Storage**: Migration `0010` — `queue_entries` columns + `filler_reserve_entries` table + `event_config.filler_auto_inject_enabled`

**Testing**: pytest `test_queue_history.py`, `test_filler_reserve.py`; extend `test_queue.py`, `test_votes.py`, `test_state.py`; frontend build

**Target Platform**: Docker Compose / K8s; operator `/admin`, participant `/participar`, kiosk `/`

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Re-queue / inject visible < 3s (SC-004); auto-inject after idle < 5s (SC-002); history page load usable with 200+ rows via pagination

**Constraints**: Spanish admin UI; `/api/*` prefix; operator-only history/reserve; constitution IV contract deltas before implement; single queue with priority tie-break; re-queue bypasses `pending_review`

**Scale/Scope**: 1 migration; ~6 new endpoints; 1 new router; queue ordering change; admin UI sections; YouTube search dual-auth for operator

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted for `backend-api`, `app-core` |
| V. Tests for changed behavior | Pass | New test modules + ordering regression |
| VI. Sibling conventions | Pass | `/api/*`, operator session, SSE `state`, Spanish UI |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/017-admin-queue-history-filler/
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
├── alembic/versions/
│   └── 0010_queue_history_filler.py
├── app/
│   ├── models.py                          # priority, source, finished_at; FillerReserveEntry
│   ├── schemas.py                         # history, reserve, EventConfigRead delta
│   ├── routers/
│   │   ├── queue.py                       # history + requeue + operator-submit routes
│   │   ├── filler_reserve.py              # new
│   │   ├── event_config.py                # filler-auto-inject PUT
│   │   └── youtube.py                     # operator search auth
│   └── services/
│       ├── queue_service.py               # finished_at, requeue, inject hook
│       ├── filler_reserve_service.py      # new
│       └── state_service.py               # priority sort
└── tests/
    ├── test_queue_history.py
    └── test_filler_reserve.py

frontend/src/app/
├── admin/
│   ├── admin.component.ts                 # history + reserve sections
│   └── admin.component.html
├── models/
│   ├── jukebox-state.ts                   # priority on QueueEntryRead
│   └── event-config.ts                    # filler_auto_inject_enabled
└── services/
    ├── queue-admin.service.ts             # history, requeue
    └── filler-reserve.service.ts          # new
```

**Structure Decision**: Extend queue and event_config surfaces; new `filler_reserve` router/service rather than overloading `queue_entries` with reserve state.

## Phase 0 — Research

See [research.md](./research.md). All technical unknowns resolved:

- Separate `filler_reserve_entries` table
- `priority` / `source` / `finished_at` on `queue_entries`
- Auto-inject hook in `skip_or_advance` + `_maybe_auto_start_playback`
- Operator access to YouTube search without participant rate limit
- Reserve reorder via full `ordered_ids` payload

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **Migration `0010`**:
   - `queue_entries`: `priority`, `source`, `finished_at` + index `(status, finished_at)`
   - `filler_reserve_entries` table
   - `event_config.filler_auto_inject_enabled` default `true`
   - Backfill terminal `finished_at` and defaults

2. **Enums** in `models.py`: `QueueEntryPriority`, `QueueEntrySource`; model `FillerReserveEntry`.

3. **`filler_reserve_service.py`**:
   - CRUD + reorder + duplicate checks (reserve + active queue)
   - `transfer_to_queue(db, ids, source)` — consume reserve rows, create entries, `_enqueue_entry`
   - `inject_next_if_idle(db)` — if auto-inject on and no playing/queued, transfer position-1

4. **`queue_service.py` deltas**:
   - Set `finished_at` on reject and when marking `played`
   - `list_history(db, status, page, page_size)` with participant display names
   - `requeue_from_history(db, entry_id)` — new row, priority rules, `_enqueue_entry`
   - `create_operator_queued_entry(db, youtube_url_or_id, search_query?)` — direct to `queued`, `priority=low`, `source=operator_direct`
   - Call `inject_next_if_idle` at end of `skip_or_advance` when no next queued; extend `_maybe_auto_start_playback` to inject before `_top_queued`
   - Participant submits: `priority=normal`, `source=participant` (set in `submit_as_participant` during foundational work)

5. **`state_service.py`**: update all `order_by` to include priority rank between votes and `created_at`.

6. **Routers**:
   - `queue.py`: `GET /history`, `POST /history/{id}/requeue`, `POST /operator-submit`
   - `filler_reserve.py`: reserve CRUD + enqueue + reorder
   - `event_config.py`: `PUT /filler-auto-inject`
   - `youtube.py`: accept `CurrentUser | CurrentParticipant`; skip rate limit for operator

### Frontend design

1. **`filler-reserve.service.ts`**: API client for reserve + reorder + enqueue batch.

2. **`queue-admin.service.ts`**: `getHistory(...)`, `requeue(id)`, `operatorSubmit(...)`.

3. **`event-config.ts` / `EventConfigService`**: `filler_auto_inject_enabled`, `updateFillerAutoInject()`.

4. **`admin.component`** — two new sections below Moderación:
   - **Historial**: paginated table (columns: title, thumbnail, video id, status, finished_at, source, participant, rejection reason), status filter, Re-encolar button, error handling
   - **Reserva de relleno**: list with reorder (CDK drag-drop or up/down), add form + search modal, **Añadir directo a cola**, delete, «Añadir a cola», toggle inyección automática
   - Spanish copy; mobile-friendly stacked rows (match 016 moderation pattern)

5. **Kiosk / participar**: no template changes required beyond consuming `priority` in models if needed for ordering display (order comes from server state).

### Testing plan

| Area | Tests |
|------|-------|
| History list | pagination, status filter, operator auth, participant 401 |
| Requeue | played/rejected → queued; moderated mode skip pending; duplicate 409 incl. reserve; revision bump |
| Operator direct | POST operator-submit → queued low priority; duplicate 409 |
| Reserve | add/delete/reorder/max 50; duplicate 409; participant 401 |
| Transfer | consume reserve; batch enqueue; queue full |
| Auto-inject | idle gap injects; toggle off blocks; reserve empty no-op; revision bump |
| Ordering | vote tie: normal before low; more votes wins |
| Votes | filler entry votable |
| Source audit | all five `source` values on creation paths (FR-017) |
| Regression | skip, approve, participant submit unchanged |

## Phase 2 — Tasks

Generated by `/speckit-tasks` (not in scope of this command).

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
