# Implementation Plan: Selector de modo de cola (Moderado / Libre)

**Branch**: `013-queue-approval-mode` | **Change id**: `013-queue-approval-mode` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/013-queue-approval-mode/spec.md`

## Summary

Add operator-selectable **Moderado** / **Libre** queue mode persisted on the `event_config` singleton. In **Libre**, participant submits enqueue directly (`queued`) with immediate `song.approved` notification and the same per-participant numeric cap applied to `queued` rows. In **Moderado**, behavior is unchanged (`pending_review` → approve/reject). Admin UI: mode selector above the pending table in **Moderación**, with confirmation dialog before `PUT /api/event-config/queue-mode`.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL; Angular standalone, TailwindCSS; existing `queue_service`, `notification_service`, `event_config` router, SSE `bump_revision`

**Storage**: `event_config.queue_mode` column (Alembic `0009`); values `moderated` | `free`, default `moderated`

**Testing**: pytest `test_queue_approval_mode.py` (new); extend `test_participant_submit.py`, `test_notifications.py`; admin component tests optional; regression `test_queue.py`

**Target Platform**: Docker Compose / K8s; operator `/admin`, participant `/participar`, kiosk `/`

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Libre submit → kiosk queue visible within **5s** (SC-002); mode change reflected on next submit without page reload (SC-004)

**Constraints**: Spanish admin labels; English API enum; operator-only mode change; no participant mode UI; no change to `EventConfigSummary` on public state; constitution IV contract deltas before implement

**Scale/Scope**: 1 migration; 1 new endpoint; `queue_service` branch + refactor; `EventConfigRead` + admin moderation UI; contract deltas `backend-api` + `app-core`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted |
| V. Tests for changed behavior | Pass | `test_queue_approval_mode.py` + notification/submit extensions |
| VI. Sibling conventions | Pass | `/api/*` prefix, operator session, Spanish UI, SSE `state` + `notification` |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/changes/013-queue-approval-mode/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── analyze.md
├── contracts/contract-deltas.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 0009_event_config_queue_mode.py          # new
├── app/
│   ├── models.py                                # QueueMode enum, EventConfig.queue_mode
│   ├── schemas.py                               # queue_mode on EventConfigRead, QueueModeUpdate
│   ├── bootstrap.py                             # default queue_mode on seed
│   ├── routers/
│   │   └── event_config.py                      # PUT /queue-mode
│   └── services/
│       └── queue_service.py                   # mode branch in submit_as_participant;
│                                                # _enqueue_entry helper; _count_participant_queued
└── tests/
    └── test_queue_approval_mode.py              # new

frontend/src/app/
├── admin/
│   ├── admin.component.ts                       # queueMode, confirm + PUT, libre banner
│   └── admin.component.html                     # selector above pending table
├── models/
│   └── event-config.ts                          # queue_mode, QueueModeUpdate
└── services/
    └── event-config.service.ts                  # updateQueueMode()
```

**Structure Decision**: Extend existing `event_config` and `queue_service`; no new routers beyond one endpoint on `event_config` router; admin reuses `EventConfigService` and existing SSE `DisplayStateService` for queue refresh after free submits.

## Phase 0 — Research

See [research.md](./research.md). Resolved: `event_config.queue_mode` column; dedicated `PUT /api/event-config/queue-mode`; submit branch; cap semantics; `queue_mode` omitted from `EventConfigSummary`; admin confirm dialog.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **Migration `0009`**: `ALTER TABLE event_config ADD COLUMN queue_mode VARCHAR(16) NOT NULL DEFAULT 'moderated'`.

2. **`QueueMode` enum** in `models.py`: `moderated`, `free`. Column on `EventConfig` with default.

3. **`queue_service` refactor**:
   - `get_queue_mode(db) -> QueueMode` — read singleton config
   - `_count_participant_queued(db, participant_id) -> int`
   - `_enqueue_entry(db, entry: QueueEntry) -> QueueEntry` — shared logic from `approve_entry` (queue full check, duplicate check, set `queued`, `approved_at`, position, recompute, `emit_song_approved`)
   - `submit_as_participant`:
     - read mode
     - **moderated**: existing pending path + `_count_participant_pending` limit
     - **free**: after validation/metadata, create entry with `status=queued`, call `_enqueue_entry` (or inline enqueue before commit), apply `_count_participant_queued` limit instead of pending limit
   - `approve_entry`: delegate enqueue body to `_enqueue_entry` after status check

4. **`event_config` router**:
   - `PUT /queue-mode` with `QueueModeUpdate`; validate enum; persist; `bump_revision(db)`
   - `EventConfigRead` includes `queue_mode` on GET

5. **Bootstrap**: `ensure_event_config` sets `queue_mode=moderated`.

### Frontend design

1. **`event-config.ts`**: add `queue_mode: 'moderated' | 'free'` to `EventConfigRead`; `QueueModeUpdate` interface.

2. **`EventConfigService.updateQueueMode(mode)`**: `PUT ${baseUrl}/event-config/queue-mode`.

3. **`admin.component`**:
   - Bind `queueMode` from `loadEventConfig()`
   - Above pending table: segmented control or radio **Moderado** / **Libre**
   - `onQueueModeChange(next)`: if `confirm('…')` then `updateQueueMode`; on error show `moderationError`; on cancel revert binding
   - `*ngIf="queueMode === 'free'"` info paragraph in Moderación section
   - Labels in Spanish; API values `moderated`/`free`

4. **Participar**: no template changes required if submit response `status` drives Mis canciones; verify toast fires on `song.approved` SSE (already wired in 007).

### Testing plan

| Area | Tests |
|------|-------|
| Moderated regression | submit → `pending_review`; approve unchanged |
| Free submit | submit → `queued`; not in `GET /pending`; notification emitted |
| Free cap | 3rd submit → 429 |
| Mode endpoint | 401 unauth; 422 invalid; 200 persists |
| Mode switch | legacy pending remains; reject legacy after switch to free; new submit follows new mode |
| Default | migration/bootstrap → `moderated` |

## Phase 2 — Tasks

See [tasks.md](./tasks.md) (28 tasks, US1–US4 + polish). Post-analyze remediation (2026-07-30): merged GET `queue_mode` into T005/T017, added FR-008/FR-013/FR-015 test coverage, documented US2 DB fixture and manual SC gates in quickstart.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
