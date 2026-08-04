# Data Model: 024-admin-queue-control

**Feature**: `024-admin-queue-control`  
**Migration**: No

## Overview

No new tables. Operations mutate or delete existing `queue_entries` rows and `jukebox_runtime.now_playing_entry_id`. Response DTOs are API-only.

## Source tables (unchanged schema)

| Table | Role in feature |
|-------|-----------------|
| `queue_entries` | Active list (`status IN (queued, playing)`); hard delete on eliminar/vaciar; `played` on force-play interrupt |
| `votes` | CASCADE delete when parent `queue_entries` row deleted |
| `jukebox_runtime` | `now_playing_entry_id`, `revision` for SSE |
| `participants` | `display_name` for `submitted_by_display_name` on list |

## `queue_entries` state transitions (this feature)

| Action | Target status | `finished_at` | Row persisted? |
|--------|---------------|---------------|----------------|
| Forzar reproducir (queued → playing) | `playing` | — | Yes |
| Forzar reproducir (interrupt) | previous → `played` | set | Yes (historial) |
| Modificar votos | unchanged | — | Yes |
| Eliminar entrada | — | — | **Deleted** |
| Vaciar cola | — | — | **Deleted** (all active) |
| Saltar / Iniciar (UI moved) | existing skip semantics | per skip | Yes (`played`) |

## Active queue ordering (read model)

1. Entry with `status = playing` (via `now_playing_entry_id`) — shown first, labeled sonando.
2. Entries with `status = queued` ordered by `queued_order_columns()` (`vote_count DESC`, `priority ASC`, `created_at ASC`), `position` 1…n after `_recompute_positions`.

## API DTOs (not persisted)

### `ActiveQueueEntryRead`

Extends `QueueEntryRead` with:

| Field | Type | Notes |
|-------|------|-------|
| `submitted_by_display_name` | string \| null | From `participants.display_name` |
| `source` | enum | `participant`, `operator_direct`, `operator_filler`, `auto_inject`, `operator_requeue` |

### `ActiveQueueListResponse`

| Field | Type |
|-------|------|
| `now_playing` | `ActiveQueueEntryRead` \| null |
| `queued` | `ActiveQueueEntryRead[]` | Full list, not kiosk-limited |

### `VoteCountUpdateRequest`

| Field | Type | Validation |
|-------|------|------------|
| `vote_count` | int | ≥ 0 |

## Validation rules

| Rule | Endpoint / action |
|------|-------------------|
| Operator session | All new routes → 401 participant/anonymous |
| `play-now` target must be `queued` | 409 if `playing` (no-op or 409 `already playing`) |
| `play-now` invalid status | 409 `invalid status` for pending/terminal |
| `vote-count` target must be `queued` or `playing` | 404 / 409 |
| `DELETE active/{id}` target must be `queued` or `playing` | 404 / 409 |
| `vote_count` negative | 422 |
| Eliminar/vaciar | Hard delete; votes cascade |

## Side effects (all mutating routes)

- `bump_revision` + SSE `state` broadcast
- `_recompute_positions` after vote change or queue shape change
- `song.up_next` when promoting next queued after delete-playing or force-play (when owner participant set)
- **No** `maybe_inject_from_reserve` after vaciar cola
- After delete-playing with remaining queued: promote next (like skip)
- Stats (`GET /api/admin/stats`) reflect deletes on next fetch (submissions/votes counts decrease)

## Admin UI state (frontend, not persisted)

| Field | Purpose |
|-------|---------|
| `panelExpanded.queue` | default `false` |
| `activeQueue` | last `ActiveQueueListResponse` |
| `activeQueueLoading` / `activeQueueError` | expand fetch |
| Confirm dialogs | eliminar entrada, vaciar cola |
| Vote edit modal | `vote_count` input per row |
