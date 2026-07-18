# Quickstart: 008-youtube-text-search

Validation after implementation.

## Prerequisites

- Changes 001–007 applied
- `JUKEBOX_YOUTUBE_API_KEYS` set to at least one valid YouTube Data API key (or test with mocks)
- Participant session on `/participar` (OAuth or dev auth)
- Operator session on `/admin` for approval checks

## Phase 1 — Search and submit (SC-001)

1. Sign in on `/participar`
2. Confirm **stacked layout**: search block above URL field; both visible
3. Enter query (≥2 chars) → **Buscar** or **Enter**
4. Results show **title**, **thumbnail**, **channel**
5. Tap a row → row highlighted; search section **active** (border/background)
6. Tap sticky **Enviar canción** at bottom
7. **Mis canciones** shows **Pendiente de revisión** within 5s
8. Operator approves → behaves per 004/007

## Phase 2 — Dual path + active section (FR-003b–003e)

1. Paste URL in URL field → URL section becomes active (highlight)
2. Select a search result → search section becomes active
3. Focus URL field **without typing** → active path **unchanged**
4. Edit URL text → URL path active; **Enviar** submits URL
5. Select result again → **Enviar** submits search selection (video id via submit API)

## Phase 3 — URL path regression (SC-003)

1. Do not use search; paste URL → **Enviar canción**
2. Same limits/errors as 006 (duplicate, pending cap, invalid link)
3. Vote, notifications, Mis canciones unchanged

## Phase 4 — Errors and limits

1. Query with 1 character → Spanish hint; no API call
2. Zero results → empty state in Spanish; URL still works
3. 11 searches in 5 minutes → rate-limit message; URL still works
4. Unset `JUKEBOX_YOUTUBE_API_KEYS` → search section disabled with message; URL active
5. (Test/mocked) all keys exhausted → Spanish unavailable message; URL active

## Phase 5 — Multi-key failover (SC-007, SC-008)

With mocked backend or test keys:

1. First key returns quota exceeded → search still succeeds with second key (transparent)
2. All keys exhausted → participant sees error; no crash

## Phase 6 — Regression 005–007

1. Vote after search UI present
2. Receive approval toast after searched song approved
3. Kiosk `/` unaffected

## Phase 7 — Automated

```bash
pytest backend/tests/test_youtube_search.py
pytest backend/tests/test_participant_submit.py backend/tests/test_votes.py backend/tests/test_notifications.py
npm --prefix frontend test
npm --prefix frontend run build
```

## Manual API probe

```bash
# Config (no auth)
curl -s http://localhost:8000/api/youtube/search/config

# Search (participant cookie)
curl -s -b participant-cookies.txt \
  "http://localhost:8000/api/youtube/search?q=never+gonna+give+you+up"
```
