# Research: 007-participant-notifications

**Date**: 2026-07-18

## Decision: SSE `notification` event on existing stream

**Decision**: Add a second SSE event type on `GET /api/events/stream`:

```text
event: notification
data: {"type":"song.approved","queue_entry_id":"...","participant_id":"...","title":"..."}
```

Broadcast via extended `sse_hub` (same subscriber list as `state`). All connected clients receive the frame; **only `/participar` filters** by `participant_id === currentParticipant.id` and shows a toast. Kiosk display and operator clients ignore unknown event types. This satisfies FR-001/002 “to owning participant” via targeted payload + client filter (not per-participant SSE streams).

**Rationale**: Spec FR-008 requires existing realtime channel; no polling; minimal backend change vs per-participant streams.

**Alternatives considered**:
- Embed `notification` inside `StateResponse` — rejected (global state leak to kiosk; wrong targeting)
- Separate `/api/participant/notifications/stream` — rejected (extra endpoint, duplicate connection)
- Web Push — out of scope (v1.1)

## Decision: Emit points (backend)

**Decision**:

| Event | Trigger location | Condition |
|-------|------------------|-----------|
| `song.approved` | `queue_service.approve_entry` after commit | `submitted_by_participant_id` not null |
| `song.up_next` | `queue_service.skip_or_advance` before next entry → `playing` | next entry owner not null |

**Do not emit** on: `reject_entry`, vote reorder (`_recompute_positions`), participant submit, operator dev-submit without participant.

**Rationale**: Matches spec FR-001/002/005/006 and baseline 001 (`up_next` only on advance, not vote reorder).

**Alternatives considered**:
- Detect up_next on approve when queue empty — rejected (baseline ties up_next to play transition; edge case handled by approve then immediate start → two toasts in FIFO queue)

## Decision: Notification payload shape

**Decision**: `NotificationEventRead` Pydantic model serialized as JSON in SSE `data`:

| Field | Type | Notes |
|-------|------|-------|
| type | `song.approved` \| `song.up_next` | |
| queue_entry_id | string | dedupe key |
| participant_id | string | client filter |
| title | string | toast copy |

No persistence, no revision coupling (notification may arrive same tick as `state` event).

## Decision: Frontend toast UX

**Decision**: `NotificationToastService` on `/participar`:

- Fixed **bottom** safe area
- **FIFO** queue (one visible toast)
- **8s** auto-dismiss + manual close
- **Dedupe** `type:queue_entry_id` for page session
- Spanish templates:
  - approved: `«{title}» ha sido aprobada y está en cola.`
  - up_next: `«{title}» es la siguiente canción.`

**Rationale**: Clarify session 2026-07-18 decisions.

## Decision: Testing strategy

**Decision**:
- `test_notifications.py`: parse SSE from TestClient stream after approve/skip; assert notification payload and absence on reject/vote/playing edge case
- Frontend: `notification-toast.service.spec.ts` (FIFO, dedupe, 8s); `participant-state.service.spec.ts` (participant_id filter for SC-003); manual quickstart for mobile layout and SC-005

**Rationale**: Constitution V; SC-003/SC-004 coverage.

## Open questions

None blocking.
