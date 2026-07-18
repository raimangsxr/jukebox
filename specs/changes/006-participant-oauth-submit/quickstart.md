# Quickstart: 006-participant-oauth-submit

Validation after implementation.

## Prerequisites

- Changes 001–005 applied
- Google Cloud OAuth client (Web application) with redirect URI matching `JUKEBOX_GOOGLE_REDIRECT_URI`
- Backend env:
  - `JUKEBOX_GOOGLE_CLIENT_ID`
  - `JUKEBOX_GOOGLE_CLIENT_SECRET`
  - `JUKEBOX_GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback`
  - `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL=http://localhost:4200/participar`
- Optional local QA without Google: `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`

## Phase 1 — Google OAuth (manual)

1. Open `http://localhost:4200/participar`
2. Confirm vote/submit controls are **disabled** and only sign-in is shown (**SC-005**)
3. Click **Iniciar sesión con Google**
4. Complete Google consent → land on `/participar` authenticated (**SC-001**: under 30s on typical mobile)
5. Refresh page → session persists (`GET /api/participant/me` returns profile)
6. Confirm dev-auth button is **not visible** without `?dev=1` or dev environment flag

## Phase 2 — Submit song (curl with session)

After OAuth in browser, copy `jukebox_participant_session` cookie or use dev-auth:

```bash
# Dev-auth fallback
curl -c p.txt -X POST http://localhost:8000/api/participant/dev-auth \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Test"}'

# Submit
curl -b p.txt -X POST http://localhost:8000/api/queue/submit \
  -H 'Content-Type: application/json' \
  -d '{"youtube_url_or_id":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# My submissions
curl -b p.txt http://localhost:8000/api/participant/submissions
```

## Phase 3 — Limits (manual / pytest)

1. Submit 2 songs → third pending → **Spanish UI error** (429; API `detail` English)
2. Operator approve one → participant has 1 in `queued` → another submit blocked (429 active limit)
3. Submit duplicate active video → 409 Spanish error in UI
4. Submit private/deleted video URL → 422 Spanish error in UI (no `pending_review` row)
5. Vote twice on `queued` → still works (005 regression)
6. **Concurrent submit** (pytest): two parallel requests at limit → one succeeds, one 429
7. Re-submit same video after `played` → allowed if no active duplicate
8. After moderator reject → participant can submit again if under pending limit

## Phase 4 — Mis canciones + SSE

1. Submit song → appears in **Mis canciones** as **Pendiente de revisión** within **3 seconds** (**SC-002**)
2. Operator approves in `/admin` → status updates to **En cola** within ~5s without reload
3. Operator rejects with reason → **Rechazada** + reason visible
4. With OAuth session: second participant votes → first participant's vote list updates via **SSE** without reload (US4.3)

## Phase 5 — Moderation integration (FR-012)

1. Operator `/admin` pending list shows participant-submitted entry
2. Approve/reject/skip flows unchanged from 004
3. Operator `POST /api/queue/dev-submit` still requires operator session (not participant)
4. Participant cannot access operator moderation routes

## Phase 6 — Automated

```bash
pytest backend/tests/test_oauth_google.py backend/tests/test_participant_submit.py backend/tests/test_participant_submissions.py
pytest backend/tests/test_votes.py backend/tests/test_participant_auth.py
npm --prefix frontend run build
```

## Regression

```bash
pytest backend/tests/test_queue.py backend/tests/test_state.py test_sse.py
# Operator dev-submit still requires operator session
# Participant cannot POST /api/queue/skip
```

## Compose / K8s note

Register production redirect URI in Google console for public API host (e.g. `https://jukebox.example.com/api/auth/google/callback`).
