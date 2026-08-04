# Data Model: 020-fill-queue-from-reserve

**Change**: `020-fill-queue-from-reserve`  
**Migration**: None — reuses 017 schema

## Unchanged tables

| Table | Relevant fields |
|-------|-----------------|
| `queue_entries` | `status`, `priority`, `source` (`auto_inject`), `youtube_video_id` |
| `filler_reserve_entries` | `position`, `youtube_video_id` — consumido al inyectar |
| `event_config` | `filler_auto_inject_enabled` |
| `jukebox_runtime` | `now_playing_entry_id`, `revision` |

## Behavioral state machine (auto-inject evaluation)

```
ON mutation (queue or reserve or toggle-on):
  IF NOT filler_auto_inject_enabled → noop
  IF count(queued) > 0 → noop
  reserve_changed = false
  WHILE reserve not empty:
    candidate = reserve[position=1]
    IF candidate.video_id in active_duplicates(pending_review|queued|playing):
      DELETE candidate from reserve; renumber; reserve_changed = true; CONTINUE
    ELSE:
      CREATE queue_entry (queued, priority=low, source=auto_inject)
      DELETE candidate from reserve; renumber; reserve_changed = true
      BREAK  // max 1 inject per evaluation
  IF reserve_changed OR queue_changed:
    bump_revision + SSE  // once per evaluation (FR-008)
  IF idle (no playing) AND queued non-empty:
    existing auto-start path promotes top queued → playing (014)
```

## Active duplicate set

Reuses `ACTIVE_DUPLICATE_STATUSES` / `_has_active_duplicate` from `queue_service.py`:

- `pending_review`
- `queued`
- `playing`

## Invariants

| ID | Rule |
|----|------|
| INV-001 | At most one `playing` entry |
| INV-002 | Auto-inject never promotes injected entry to `playing` while another `playing` exists |
| INV-003 | Each successful inject removes exactly one reserve row |
| INV-004 | Duplicate skip during inject removes reserve row without creating queue entry |
| INV-005 | Passive `GET /api/state` and `GET /api/participant/state` do not mutate |
| INV-006 | One `bump_revision` per evaluation when reserve or queue mutates (inject or duplicate-only removal) |

## DTO / API schema changes

None. `StateResponse.queue` and `ParticipantStateResponse.queue` unchanged; content may include newly injected `queued` entries.
