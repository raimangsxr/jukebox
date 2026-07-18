# Quickstart: 007-participant-notifications

Validation after implementation.

## Prerequisites

- Changes 001–006 applied
- Operator session on `/admin`
- Participant session on `/participar` (OAuth or `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`)

## Phase 1 — song.approved toast (SC-001)

1. Participant submits a YouTube URL on `/participar`
2. Operator approves in `/admin` pending list
3. Within **5 seconds**, participant sees bottom toast: «{title}» ha sido aprobada y está en cola.
4. Mis canciones shows **En cola**
5. Second participant on another browser does **not** see the toast (SC-003 manual)

## Phase 2 — song.up_next toast (SC-002)

1. Ensure a song is **playing** and participant's approved song is top of `queued` (or only queued item)
2. Operator clicks **Saltar canción** (or wait for natural end — kiosk calls `POST /api/queue/skip`, same backend path)
3. Within **3 seconds**, owner participant sees: «{title}» es la siguiente canción.
4. Non-owner participants do not see the toast

## Phase 3 — Negative cases and edge cases

1. Operator **rejects** participant song → **no** approval toast; Mis canciones **Rechazada**
2. Vote reorder changes queue order → **no** `up_next` toast (SC-004 manual)
3. Participant's song already **`playing`** → skip/advance does **not** show a new `up_next` toast for that entry
4. Dismiss toast manually → does not reappear for same event
5. Wait **8s** → toast auto-dismisses; next queued toast appears if any
6. **Reconnect dedupe**: With toast already shown for an event, briefly disconnect network (or stop backend), reconnect SSE — duplicate `(type, queue_entry_id)` delivery must **not** produce a second toast for that event

## Phase 4 — Regression (SC-005)

1. With an approval or up-next toast **visible**, vote on a queued song → vote succeeds; `votes_remaining` updates per 005
2. With toast visible or within **2 seconds** after dismiss/auto-dismiss, submit a new URL → submit succeeds per 006 limits
3. SSE queue / Mis canciones still update on revision bump
4. Kiosk `/` display unaffected (no toast UI; playback normal)

## Phase 5 — Automated

```bash
pytest backend/tests/test_notifications.py
pytest backend/tests/test_votes.py backend/tests/test_participant_submit.py backend/tests/test_sse.py
npm --prefix frontend test
npm --prefix frontend run build
```

## SSE manual probe (optional)

With participant cookie:

```bash
curl -N -b cookies.txt http://localhost:8000/api/events/stream
# Approve or skip in /admin — expect `event: notification` lines with correct participant_id
```
