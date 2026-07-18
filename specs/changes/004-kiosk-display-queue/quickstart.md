# Quickstart: 004-kiosk-display-queue

Validation after implementation.

## Prerequisites

- Changes 001–003 applied
- `docker compose up` or local backend + frontend
- Operator credentials in `.env`
- For dev submit: `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true` in backend env

## Phase 1 — Backend API (curl)

```bash
# Login
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"op","password":"change-me-please-1234"}'

# Dev submit (pending_review) — requires JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true
curl -b cookies.txt -X POST http://localhost:8000/api/queue/dev-submit \
  -H 'Content-Type: application/json' \
  -d '{"youtube_url_or_id":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# List pending
curl -b cookies.txt http://localhost:8000/api/queue/pending

# Approve (replace {id})
curl -b cookies.txt -X POST http://localhost:8000/api/queue/{id}/approve

# Start playback (idle + queued entries — same endpoint as skip)
curl -b cookies.txt -X POST http://localhost:8000/api/queue/skip

# State snapshot
curl -b cookies.txt http://localhost:8000/api/state

# SSE (terminal)
curl -N -b cookies.txt http://localhost:8000/api/events/stream

# Skip / advance
curl -b cookies.txt -X POST http://localhost:8000/api/queue/skip
```

## Phase 2 — Kiosk display (manual)

1. Create embed token in `/admin` → copy plaintext
2. Private window: `http://localhost:4200/?token=<plaintext>`
3. Verify **no placeholder text** — player area, QR, queue strip show real or empty states
4. With `app_height_px=720`, measure queue strip ≈ 8–12% of viewport height (SC-001)
5. Scan QR → opens `/participar` on same origin
6. Invalid token / expired session still show static Spanish errors (002 regression)

## Phase 3 — Moderation flow (manual)

1. Login `/admin` → Moderación section
2. Dev-submit 2–3 pending entries (different video ids)
3. Approve one → within 5s kiosk strip updates without reload (SC-002)
4. Open YouTube preview link → new tab with correct watch URL
5. Reject one with reason → disappears from pending, not on display
6. Seed 100 queued (pytest) → approve blocked with Spanish "cola llena" message

## Phase 4 — Skip / start playback (manual)

1. Approve at least one song (status `queued`, nothing `playing` yet)
2. Click **Iniciar reproducción** in admin (calls `POST /api/queue/skip`)
3. Kiosk player starts the approved video; queue strip updates
4. With one `playing` and another `queued`, click **Saltar canción** → advances to next

## Phase 5 — Automated

```bash
pytest backend/tests/test_queue.py backend/tests/test_state.py backend/tests/test_sse.py
pytest backend/tests/test_auth_policy.py
npm --prefix frontend run build
```

## Regression

```bash
pytest backend/tests/test_auth.py backend/tests/test_tokens.py
# Display error paths from 002 quickstart Phase 2–3
```

## Compose smoke

```bash
bash scripts/compose-smoke.sh
```

Requires Docker daemon; validates health after migrate includes 0003.

## SSE / proxy note

Backend SSE responses set `X-Accel-Buffering: no`. If `/api/events/stream` is proxied through nginx or ingress, ensure buffering is disabled for that path (see ops-platform ingress config from change 003).
