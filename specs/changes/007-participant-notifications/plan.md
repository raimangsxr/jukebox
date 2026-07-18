# Implementation Plan: Participant In-App Notifications

**Branch**: `004-participant-notifications` (git) | **Change id**: `007-participant-notifications` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/changes/007-participant-notifications/spec.md`

## Summary

Emit targeted `song.approved` and `song.up_next` events over the existing participant SSE stream (`/api/events/stream`), with Angular toast UI on `/participar` (bottom-fixed, Spanish, FIFO queue, 8s auto-dismiss, session dedupe). Backend hooks: moderator **approve** and **skip/advance** in `queue_service`; no DB migration. Client filters notifications by current `participant_id`.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript / Angular 22 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (existing); Angular standalone, RxJS, TailwindCSS; existing `sse_hub` broadcast

**Storage**: No new tables — ephemeral `notification_event` on SSE wire only

**Testing**: pytest (`test_notifications.py`, SSE event shape, targeting, no up_next on vote reorder, 005/006 regression); `npm run build`; manual quickstart

**Target Platform**: Docker Compose / K8s; mobile `/participar` via QR

**Project Type**: Web application (FastAPI API + Angular SPA monorepo)

**Performance Goals**: Approval toast &lt; 5s (SC-001); up-next toast &lt; 3s (SC-002)

**Constraints**: Same SSE channel as 005; client-side filter by `participant_id`; no Web Push; no retroactive toasts; vote reorder must not emit `up_next`

**Scale/Scope**: ~2 emit points in `queue_service`; extend `sse_hub`; 1 notification schema; toast component/service on `/participar`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Action |
|-----------|--------|--------|
| I. Active contracts source of truth | Pass | Merge `contracts/contract-deltas.md` at implement start |
| IV. Contract updates before implementation | Pass | Deltas drafted |
| V. Tests for changed behavior | Pass | `test_notifications.py` + regression |
| VI. Sibling conventions | Pass | `/api/*`, SSE on existing stream, Spanish UI |

**Post-design re-check**: All gates pass. No Complexity Tracking violations.

## Project Structure

### Documentation (this feature)

```text
specs/changes/007-participant-notifications/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── context-pack.md
├── contracts/contract-deltas.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── schemas.py                         # + NotificationEventRead
│   ├── services/
│   │   ├── sse_hub.py                     # + format/broadcast notification event
│   │   ├── notification_service.py        # emit approved / up_next helpers
│   │   └── queue_service.py               # hook approve + skip_or_advance
│   └── routers/
│       └── state.py                       # (unchanged route; new event type on wire)
└── tests/
    └── test_notifications.py

frontend/src/app/
├── participate/
│   ├── participate.component.*            # mount toast region
│   └── notification-toast.component.*     # bottom toast UI (new)
└── services/
    ├── participant-state.service.ts       # listen for SSE `notification` events
    └── notification-toast.service.ts      # FIFO queue, dedupe, 8s timer (new)
```

**Structure Decision**: Extend 005 SSE hub with a second event type; participant client filters; kiosk/display ignore `notification` events.

## Phase 0 — Research

See [research.md](./research.md). Resolved: SSE `notification` event, emit points, client filter, toast UX rules.

## Phase 1 — Design

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| Contract deltas | [contracts/contract-deltas.md](./contracts/contract-deltas.md) |
| Validation guide | [quickstart.md](./quickstart.md) |
| Agent context | [context-pack.md](./context-pack.md) |

### Backend design

1. **`NotificationEventRead`**: `{ type, queue_entry_id, participant_id, title }`
2. **`sse_hub`**: `format_notification_event()`, `broadcast_notification()` — `event: notification`
3. **`notification_service.emit_*`**: guard `submitted_by_participant_id`; call broadcast after DB commit
4. **`approve_entry`**: after success → `song.approved` if owner present
5. **`skip_or_advance`**: before promoting next `queued` → `playing` → `song.up_next` for that entry's owner
6. **No emit** on `reject_entry`, `_recompute_positions`, or `vote_service`

### Frontend design

1. **`ParticipantStateService`**: add `notification` EventSource listener; expose `notification$`
2. **`NotificationToastService`**: FIFO queue, dedupe `Set<type:entryId>`, 8s auto-dismiss, manual dismiss
3. **`NotificationToastComponent`**: fixed bottom, Spanish copy templates, non-blocking
4. **Display/kiosk**: ignore unknown SSE event types (already only handles `state`)

## Phase 2 — Implementation phases (reference for tasks)

### Phase A — Contracts + manifest

Register 007; merge contract deltas.

### Phase B — Backend notification emit

`sse_hub`, `notification_service`, `queue_service` hooks, schema, tests.

### Phase C — Frontend toast

Toast service/component, participate integration, dedupe + queue UX.

### Phase D — Regression + closure

Full pytest, build, quickstart, manifest `implemented`.

## Risks

| Risk | Mitigation |
|------|------------|
| Broadcast leaks event to all SSE clients | Payload includes `participant_id`; only `/participar` acts; display ignores |
| Duplicate toasts on reconnect | Client dedupe per spec; tests |
| up_next on wrong transition | Emit only in `skip_or_advance` pre-play hook; negative test on vote reorder |
| approved + up_next burst | FIFO toast queue (clarify session) |

## Complexity Tracking

> No violations.
