# Quickstart: 024-admin-queue-control

Validation after implementation.

## Prerequisites

- Branch `024-admin-queue-control`
- Operator session on `/admin`
- 2+ queued songs + optional dev participants (`/participar?dev=1`)

## Phase 1 — Panel placement and Moderación split (US1, US1b, FR-001, FR-016–018)

1. Open `/admin`
2. **Expected**: **Cola de reproducción** after **Moderación**, before **Historial**, collapsed; only Moderación expanded.
3. Expand **Moderación**
4. **Expected**: Queue mode + pending table only — **no** Iniciar/Saltar, **no** playback status line.
5. Expand **Cola de reproducción**
6. **Expected**: Playback status, Iniciar/Saltar, list of active entries, **Vaciar cola**.

## Phase 2 — Active list (US1, FR-002–005)

1. With one playing + 3 queued entries
2. **Expected**: Sonando row first, then queued positions 1, 2, 3 ascending
3. **Expected**: Each row shows title, votes, position, priority, source, submitter when linked

## Phase 3 — Iniciar / Saltar in queue panel (US1b)

1. Idle + queued, no playing → **Iniciar reproducción** enabled → starts first song
2. Playing → **Saltar canción** enabled → previous marked played, next plays
3. **Expected**: Buttons only in Cola de reproducción, not Moderación

## Phase 4 — Forzar reproducir (US3)

1. Playing + queue → force play 3rd queued
2. **Expected**: 3rd plays; interrupted song in **Historial** as played (not deleted)
3. Force play on already playing → no destructive change

## Phase 5 — Modificar votos (US4)

1. Two queued with different votes → increase lower to exceed higher
2. **Expected**: Positions reorder; playing entry vote edit does not stop playback

## Phase 6 — Eliminar entrada (US5)

1. Eliminar non-playing → confirm dialog → entry gone, no historial row
2. Eliminar playing with queue left → next auto-starts
3. Cancel confirm → no change
4. Participant **Mis canciones** loses deleted entry on refresh/SSE

## Phase 7 — Vaciar cola (US2)

1. Playing + queued → Vaciar cola → confirm
2. **Expected**: All active gone, kiosk idle, pending/reserve/historial untouched
3. **Expected**: No filler auto-inject immediately after vaciar

## Phase 8 — Live updates (FR-006)

1. Expand Cola de reproducción
2. Vote or submit from participant tab
3. **Expected**: List updates without manual refresh

## Phase 9 — Auth (FR-013)

1. Without operator session → **401** on: `GET /api/queue/active`, `DELETE /api/queue/active`, `DELETE /api/queue/active/{id}`, `POST /api/queue/{id}/play-now`, `PATCH /api/queue/{id}/vote-count`
2. Participant dev session cannot call any of the above

## Phase 10 — Participant sync (FR-014)

1. Participant with song in cola → operador elimina entrada
2. **Expected**: Entry absent from `GET /api/participant/submissions` and cola votable after SSE/refresh

## Phase 11 — Response timing (SC-001, SC-002, SC-003, SC-008)

1. Expand Cola de reproducción → identify sonando + order in **&lt; 10s** without kiosk (SC-001)
2. Vaciar / forzar / Iniciar/Saltar → Admin + kiosk reflect change in **&lt; 5s** on local network (SC-002, SC-003, SC-008)

## Phase 12 — Stats impact

1. Note stats submission count for participant song
2. Eliminar that song from cola
3. **Actualizar** Estadísticas
4. **Expected**: Totals decrease (permanent delete)

## Automated tests

```bash
cd backend && pytest tests/test_admin_queue_control.py -q
cd frontend && npm test -- --run admin-queue  # if spec added
npm --prefix frontend run build
```
