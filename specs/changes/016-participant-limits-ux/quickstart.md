# Quickstart: 016-participant-limits-ux

## Local dev

### 1. Backend ENV

Add to `backend/.env`:

```env
JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT=2
JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT=10
JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT=2
```

### 2. Run stack

```bash
docker compose up -d db
cd backend && alembic upgrade head && uvicorn app.main:app --reload --port 8000
cd frontend && npm start
```

### 3. Verify connection indicator

1. Open `/admin` — badge hidden when SSE connected.
2. Stop backend briefly — see «Reconectando…» then «Modo respaldo».
3. Restart backend — badge clears within ~30s.

### 4. Verify participant rules

1. Open `/participar` in incognito.
2. Dev login (`?dev=1` if enabled).
3. See «Normas de participación» with 2 / 10 / 2 limits.
4. Accept → full participate UI.
5. Refresh tab — rules skipped; new incognito — rules shown again.

### 5. Verify admin mobile

1. `/admin` with pending entries.
2. DevTools device mode 390px width.
3. No horizontal scroll; cards show approve/reject.

## Tests

```bash
cd backend && pytest tests/test_rate_limiter.py tests/test_votes.py tests/test_youtube_search.py -q
cd frontend && npm test -- --run live-connection && npm run build
```

## K8s

Apply updated ConfigMap keys before rollout:

- `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT`
- `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT`
