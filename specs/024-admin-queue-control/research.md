# Research: 024-admin-queue-control

**Feature**: `024-admin-queue-control`  
**Date**: 2026-08-04

## R1 — Active queue list: dedicated endpoint vs `GET /api/state`

**Decision**: New operator endpoint `GET /api/queue/active` returning **all** active entries (playing + full queued list) with admin metadata.

**Rationale**: `StateResponse.queue` is capped by `queue_visible_count` (kiosk strip, default 8). Admin panel requires every `queued` + `playing` row (FR-002, SC-001). Participant `GET /api/participant/state` returns full queued list but is participant-auth and lacks `source` / display names for operator.

**Alternatives considered**:
- Raise `queue_visible_count` temporarily — rejected: wrong abstraction, affects kiosk.
- Client merge `now_playing` + multiple polls — rejected: still capped, no source labels.

## R2 — Permanent delete semantics

**Decision**: **Hard `DELETE` from `queue_entries`** for eliminar individual and vaciar cola; `votes` cascade (`ON DELETE CASCADE` on `votes.queue_entry_id`).

**Rationale**: Clarification A — no historial terminal row, no «Mis canciones». Matches `DELETE /api/queue/history` pattern using SQLAlchemy `delete()`.

**Alternatives considered**:
- New status `cancelled` — rejected: would still appear in submissions list unless filtered everywhere.
- Soft delete flag — rejected: migration + filter churn.

**Implementation note**: Clear `jukebox_runtime.now_playing_entry_id` before deleting playing row; FK allows SET NULL but explicit clear avoids transient inconsistency.

## R3 — Force play vs global skip

**Decision**: `POST /api/queue/{id}/play-now` promotes target `queued` entry to `playing`; if another is playing, mark it **`played`** (with `finished_at`) — same as `skip_or_advance` interrupt path, **not** hard delete.

**Rationale**: Clarification Q2 — interrupted song appears in historial / «Mis canciones» like skip.

**Alternatives considered**:
- Reuse skip in loop until target — rejected: wrong intermediate notifications and order side effects.

## R4 — Admin vote count update

**Decision**: `PATCH /api/queue/{id}/vote-count` body `{ "vote_count": int ≥ 0 }`; set denormalized `vote_count`, `_recompute_positions(db)`, `bump_revision`. **No** participant vote-limit checks; **no** new `votes` rows.

**Rationale**: Operator correction of totals; participant votes table tracks individual casts, `vote_count` is ordering field. Reordering uses existing `queued_order_columns()`.

**Alternatives considered**:
- Insert/delete vote rows to match delta — rejected: complex, quota side effects, FK to entry on delete.

## R5 — Delete playing entry / auto-advance

**Decision**: After deleting `playing` entry, if another `queued` exists → promote top `queued` to `playing` (emit `song.up_next` when owner set); else clear `now_playing`. Same helper path as skip tail.

**Rationale**: FR-012; mirrors skip after mark-played.

## R6 — Vaciar cola and filler auto-inject

**Decision**: After `DELETE /api/queue/active`, **do not** call `maybe_inject_from_reserve` automatically.

**Rationale**: Operator explicitly emptied playback queue; auto-inject would contradict «sin pendientes». Filler inject still runs on later lifecycle events (skip leaving empty queued, etc.).

## R7 — Panel data refresh UX

**Decision**: Load `GET /api/queue/active` on panel expand; refresh list on every operator SSE `state` event while expanded (reuse `DisplayStateService` / existing admin SSE). Playback buttons keep `POST /api/queue/skip` (moved in UI only).

**Rationale**: FR-006 live updates without polling; initial expand needs full metadata (`source`, submitter name) not in SSE strip.

**Alternatives considered**:
- Fetch only on expand + manual Actualizar — rejected: weaker than spec FR-006 / US1 scenario 6.

## R8 — Moderación UI split

**Decision**: Remove playback status block + Iniciar/Saltar from Moderación template; add identical controls to Cola de reproducción panel (same `advancePlayback()`, `canStartPlayback`, `playbackStatusLabel`, `playbackAudioHint`).

**Rationale**: User scope addendum + FR-016–FR-018; no backend change for skip endpoint.

## R9 — Migration

**Decision**: **No migration** — uses existing `queue_entries`, `votes`, `jukebox_runtime`.

**Rationale**: New endpoints and UI; no schema change.

## R10 — Route layout

**Decision**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/queue/active` | List active queue |
| DELETE | `/api/queue/active` | Vaciar cola |
| DELETE | `/api/queue/active/{id}` | Eliminar entrada |
| POST | `/api/queue/{id}/play-now` | Forzar reproducir |
| PATCH | `/api/queue/{id}/vote-count` | Modificar votos |

Place `GET/DELETE /active` routes **before** `/{entry_id}/approve` in router to avoid path shadowing.

**Alternatives considered**:
- `DELETE /api/queue/{id}` — rejected: future ambiguity with history ids; `active` prefix scopes operator destructive ops.
