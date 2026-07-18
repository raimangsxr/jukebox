# Quickstart: 005-participant-voting

Validation after implementation.

## Prerequisites

- Changes 001–004 applied
- `docker compose up` or local backend + frontend
- Operator credentials in `.env`
- Backend env: `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`
- At least one `queued` entry (use 004 dev-submit + approve flow)

## Phase 1 — Seed queue (operator)

```bash
# Operator login
curl -c op-cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"op","password":"change-me-please-1234"}'

# Dev submit + approve (requires JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true)
curl -b op-cookies.txt -X POST http://localhost:8000/api/queue/dev-submit \
  -H 'Content-Type: application/json' \
  -d '{"youtube_url_or_id":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Get pending id from list, then approve
curl -b op-cookies.txt http://localhost:8000/api/queue/pending
curl -b op-cookies.txt -X POST http://localhost:8000/api/queue/{id}/approve
```

## Phase 2 — Participant session (curl)

```bash
# Dev participant bootstrap
curl -c participant-cookies.txt -X POST http://localhost:8000/api/participant/dev-auth \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Test User"}'

# Me
curl -b participant-cookies.txt http://localhost:8000/api/participant/me

# Participant state (all queued + votes remaining)
curl -b participant-cookies.txt http://localhost:8000/api/participant/state

# Cast vote (replace {queue_entry_id})
curl -b participant-cookies.txt -X POST http://localhost:8000/api/votes \
  -H 'Content-Type: application/json' \
  -d '{"queue_entry_id":"{queue_entry_id}"}'

# Third vote within 5 minutes → 409 vote limit exceeded
curl -b participant-cookies.txt -X POST http://localhost:8000/api/votes \
  -H 'Content-Type: application/json' \
  -d '{"queue_entry_id":"{queue_entry_id}"}'
```

## Phase 3 — SSE as participant

```bash
curl -N -b participant-cookies.txt http://localhost:8000/api/events/stream
```

In another terminal, cast a vote → stream emits `event: state` with updated `vote_count` / order.

### Reconnect (US2)

1. Open `/participar` with participant session; confirm queue loaded
2. Disable network briefly (devtools offline) or restart backend
3. Re-enable network → queue/counts match server within reconnect backoff (no stale duplicates; `votes_remaining` preserved per client merge rule)

## Phase 4 — `/participar` UI (manual)

1. Open `http://localhost:4200/participar` without session → sign-in prompt, no active vote buttons
2. With `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`, use dev sign-in → queue list appears
3. Vote twice (same or different songs) → counts update; header shows "X de 2 votos disponibles" decrementing (SC-002, FR-008)
4. Third vote → Spanish error, no state corruption
5. Each vote action completes with visible feedback in **≤3 seconds** (SC-001)
6. Open kiosk `/` (embed token) in another window → vote on mobile → strip updates within 5s (SC-003)

## Phase 5 — Reorder verification

1. Seed 2+ `queued` entries with different titles
2. Vote multiple times for the lower-ranked song until it overtakes
3. Confirm `/participar` order matches kiosk queue strip order

## Phase 6 — Automated

```bash
pytest backend/tests/test_votes.py backend/tests/test_participant_auth.py
pytest backend/tests/test_sse.py backend/tests/test_auth_policy.py
npm --prefix frontend run build
```

## Regression

```bash
pytest backend/tests/test_queue.py backend/tests/test_state.py
# Operator moderation unchanged — approve/reject/skip still require operator cookie
curl -b participant-cookies.txt -X POST http://localhost:8000/api/queue/skip
# Expect 401
```

## Compose smoke

```bash
bash scripts/compose-smoke.sh
```

Requires migration `0004` applied.
