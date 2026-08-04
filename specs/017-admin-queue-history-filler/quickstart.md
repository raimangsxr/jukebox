# Quickstart: 017-admin-queue-history-filler

Validation after implementation.

## Prerequisites

- Changes 001–015 applied; operator on `/admin`, participant on `/participar`, kiosk `/`
- Branch `017-admin-queue-history-filler`
- `JUKEBOX_YOUTUBE_API_KEYS` configured for search/metadata tests

## Phase 1 — Historial y re-encolar (US1)

1. Play and reject at least one song each (moderation + skip)
2. Open **Historial** in admin → see paginated list with correct status labels
3. Filter **Reproducidas** / **Rechazadas**
4. **Re-encolar** a played song → appears in kiosk queue < 3s (SC-004)
5. Try re-encolar same video while in reserve → 409 with clear message
6. In **Moderado** mode, re-encolar rejected song → goes to `queued` directly (not pending)

## Phase 2 — Reserva de relleno (US2)

1. Add 3 songs to **Reserva** via URL and YouTube search
2. Confirm they do **not** appear in kiosk queue strip
3. **Añadir directo a cola** one song (operator-submit) → in queue, not in reserve
4. Reorder reserve (drag or controls) → order persists on reload
5. **Añadir a cola** one reserve item → removed from reserve, appears in queue with low priority
6. Delete reserve item → no longer injectable

## Phase 3 — Inyección automática (US3)

1. Enable **Inyección automática** toggle (default on)
2. Populate reserve; empty active queue; skip/end current song
3. Next track starts < 5s from reserve (SC-002)
4. Disable toggle → empty queue stays silent until manual action
5. Re-enable → next idle gap injects again

## Phase 4 — Prioridad en empates (US4)

1. Enqueue one filler (low) and one participant song with 0 votes
2. Kiosk/admin queue order: participant song first (SC-003)
3. Vote filler above user song → filler moves ahead (votes win)
4. Equal votes again → participant still first

## Phase 5 — Votación sobre relleno

1. Participant votes filler song in queue → vote count increases, order updates
2. Vote limit still applies per existing rules

## Phase 6 — Auth & visibility

1. `GET /api/queue/history` without cookie → 401
2. Participant cannot access `/api/filler-reserve` → 401
3. `/participar` — no historial/reserve sections

## Phase 7 — Automated

```bash
pytest backend/tests/test_queue_history.py backend/tests/test_filler_reserve.py
pytest backend/tests/test_queue.py backend/tests/test_votes.py backend/tests/test_state.py
npm --prefix frontend run build
```

## Manual API probe

```bash
# History (operator)
curl -s -b operator.txt 'http://localhost:8000/api/queue/history?page=1&page_size=25' | jq

# Requeue
curl -s -X POST -b operator.txt http://localhost:8000/api/queue/history/{id}/requeue | jq

# Add to reserve
curl -s -X POST -b operator.txt -H 'Content-Type: application/json' \
  -d '{"youtube_url_or_id":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
  http://localhost:8000/api/filler-reserve | jq

# Direct to queue (bypass reserve)
curl -s -X POST -b operator.txt -H 'Content-Type: application/json' \
  -d '{"youtube_url_or_id":"https://www.youtube.com/watch?v=abcdefghijk"}' \
  http://localhost:8000/api/queue/operator-submit | jq

# Toggle auto-inject
curl -s -X PUT -b operator.txt -H 'Content-Type: application/json' \
  -d '{"filler_auto_inject_enabled":false}' \
  http://localhost:8000/api/event-config/filler-auto-inject | jq
```

## SC gates (manual)

| ID | Gate |
|----|------|
| SC-001 | Re-encolar from 200-item history in < 30s (90% trials) |
| SC-002 | Auto-inject after idle < 5s |
| SC-003 | 100% participant-before-filler on vote tie |
| SC-004 | Live update < 3s after requeue/inject |
| SC-005 | Guided operator completes reserve→inject flow unassisted |

Document results in PR notes.
