# Data Model: 021-collapsible-panels-reset

**Change**: `021-collapsible-panels-reset`  
**Migration**: None — reuses existing `queue_entries` and `votes` tables

## Unchanged tables (relevant)

| Table | Role in this feature |
|-------|----------------------|
| `queue_entries` | Terminal rows (`played`, `rejected`) deleted by clear history; active rows untouched |
| `votes` | CASCADE delete when parent `queue_entry` removed |
| `participants` | Unchanged; submissions list filters by `submitted_by_participant_id` |

## Terminal vs active statuses

| Status | In history list | Cleared by `DELETE /api/queue/history` | Visible in «Mis canciones» |
|--------|-----------------|----------------------------------------|----------------------------|
| `played` | Yes | Yes | Yes (until cleared) |
| `rejected` | Yes | Yes | Yes (until cleared) |
| `pending_review` | No | No | Yes |
| `queued` | No | No | Yes |
| `playing` | No | No | Yes |

## Clear history operation

```
clear_history(db):
  DELETE FROM queue_entries WHERE status IN ('played', 'rejected')
  COMMIT
  bump_revision(db)  → SSE state to all audiences
```

**Invariants**:

| ID | Rule |
|----|------|
| INV-001 | Clear history never deletes `pending_review`, `queued`, or `playing` rows |
| INV-002 | Clear history never touches `filler_reserve_entries` |
| INV-003 | Idempotent: second DELETE with empty history → 204, no error |
| INV-004 | `jukebox_runtime.now_playing_entry_id` unchanged if playing entry is not terminal |
| INV-005 | Participant `/api/participant/submissions` reflects deletions after SSE `state` or refresh |

## UI state (client-only, not persisted)

| Surface | Panel key | Default `expanded` |
|---------|-----------|-------------------|
| Admin | `moderation` | `true` |
| Admin | `history` | `false` |
| Admin | `reserve` | `false` |
| Admin | `apiKeys` | `false` |
| Admin | `event` | `false` |
| Admin | `tokens` | `false` |
| Participate | `votes` | `true` |
| Participate | `submit` | `false` |
| Participate | `mySongs` | `false` |

**Badge fields** (Admin headers only):

| Panel | Badge source |
|-------|----------------|
| Moderación | `pending().length` → «N pendiente(s)» |
| Historial | `historyTotalAll` from unfiltered `GET /history` → «N entrada(s)» |

## DTO / API schema changes

| Method | Path | Auth | Response |
|--------|------|------|----------|
| DELETE | `/api/queue/history` | operator | **204** (new) |

No change to `HistoryListResponse`, `QueueEntryRead`, or SSE payload shapes.
