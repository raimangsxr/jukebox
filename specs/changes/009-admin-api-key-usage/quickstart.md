# Quickstart: 009-admin-api-key-usage

Validation after implementation.

## Prerequisites

- Changes 001–008 applied
- `JUKEBOX_YOUTUBE_API_KEYS` set to at least one key (or test with mocks)
- Operator session on `/admin`
- Optional: participant session on `/participar` to trigger search usage

## Phase 1 — Admin usage list (SC-001, FR-009)

1. Sign in on `/admin`
2. **SC-001 timing**: Section **Uso de API Keys** visible with data within **10 seconds** of page load (stopwatch from navigation complete to table populated)
3. Confirm section appears between **Moderación** and **Evento**
4. Each configured key shows: label (`Clave N`), usados, restantes, límite 100
5. Masked suffix visible; **no** full API key in HTML or network tab
6. **Próximo reinicio** shows next Pacific midnight

## Phase 2 — Exact tracking (SC-002)

1. Note baseline `used_count` for a key
2. On `/participar`, run a text search (or submit URL that triggers metadata fetch)
3. **SC-001 timing**: Within **5 seconds** of the outbound request, admin table updates **without refresh** (SSE)
4. `used_count` increased by exactly 1 for the key that sent the outbound request

## Phase 2b — No increment without outbound request (FR-003)

1. Trigger participant search with query too short (422) or exceed rate limit (429)
2. Confirm **no** key `used_count` changes in admin

## Phase 3 — Failure still counts (clarify Q1)

1. (Mocked test) Force HTTP error after send for a key
2. `used_count` still increments by 1

## Phase 4 — Google quota exhausted (clarify Q2)

1. (Mocked) Return quota error when local count &lt; 100
2. Row shows **100** usados, **0** restantes, estado **Agotada**

## Phase 5 — Empty and auth (SC-005, SC-006)

1. Unset `JUKEBOX_YOUTUBE_API_KEYS` → Spanish empty state in section
2. `curl` usage endpoint without operator cookie → 401
3. Participant cookie → 401

## Phase 6 — Persistence (SC-003)

1. Record counts → restart backend → reload `/admin` → same counts for current Pacific day

## Phase 7 — Regression 004–008

1. Moderation, tokens, search, URL submit, voting, notifications unchanged
2. Kiosk `/` ignores `api_key_usage` SSE events

## Phase 8 — Automated

```bash
pytest backend/tests/test_youtube_api_key_usage.py
pytest backend/tests/test_youtube_search.py
pytest backend/tests/test_sse.py
npm --prefix frontend run build
```

## Manual API probe

```bash
# Usage snapshot (operator cookie)
curl -s -b operator-cookies.txt http://localhost:8000/api/youtube/api-keys/usage | jq

# SSE (operator) — expect event: api_key_usage after a search
curl -N -b operator-cookies.txt http://localhost:8000/api/events/stream
```
