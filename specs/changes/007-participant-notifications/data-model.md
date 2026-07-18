# Data Model Delta: 007-participant-notifications

## Persistence

**No Alembic migration.** Notifications are ephemeral on the SSE wire and in the browser toast queue.

## Wire entity: `notification_event` (SSE)

| Field | Type | Notes |
|-------|------|-------|
| type | enum string | `song.approved` \| `song.up_next` |
| queue_entry_id | uuid string | FK logical to `queue_entries.id` |
| participant_id | uuid string | Target recipient; must match `submitted_by_participant_id` |
| title | string | From `queue_entries.title` at emit time |

### Targeting rules

| Rule | Enforcement |
|------|-------------|
| Owner only | `submitted_by_participant_id` must be non-null at emit |
| No cross-participant delivery (client) | `/participar` ignores events where `participant_id !== me.id` |
| No operator dev-submit without participant | `submitted_by_participant_id` null → no emit |

## Existing tables (unchanged)

### `queue_entries`

Notification ownership uses existing `submitted_by_participant_id` (006).

### State transitions → events

| Transition | Notification |
|--------------|--------------|
| `pending_review` → `queued` (approve) | `song.approved` |
| `queued` → next to play (skip/advance) | `song.up_next` for that entry |
| `pending_review` → `rejected` | none |
| `queued` reorder (vote) | none |
| `queued` → `playing` | up_next already fired at advance boundary |

## API DTO (reference)

```python
class NotificationEventRead(BaseModel):
    type: Literal["song.approved", "song.up_next"]
    queue_entry_id: str
    participant_id: str
    title: str
```

## Client-side ephemeral state

| Store | Scope | Purpose |
|-------|-------|---------|
| `shownKeys: Set<string>` | page session | dedupe `"{type}:{queue_entry_id}"` |
| `pendingToasts: NotificationEvent[]` | page session | FIFO queue |

No server session storage for notifications.
