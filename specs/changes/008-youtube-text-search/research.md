# Research: 008-youtube-text-search

**Date**: 2026-07-18

## Decision: YouTube Data API `search.list` (video-only)

**Decision**: Call `GET https://www.googleapis.com/youtube/v3/search` with `part=snippet`, `type=video`, `maxResults=10` (config default), `q={query}`.

**Rationale**: Product baseline 001 v1.1; returns title, channel, thumbnails required by FR-005.

**Alternatives considered**:
- Invidious / scraping — rejected (ToS, fragility)
- oEmbed search — not available
- Embed search widget — rejected (ads/UX; spec requires custom list)

## Decision: API key pool (4–5 keys, round-robin, failover)

**Decision**: `JUKEBOX_YOUTUBE_API_KEYS` comma-separated list in settings. In-process `YoutubeApiKeyPool`:

- Round-robin starting index per successful search
- On HTTP 403 with `quotaExceeded` (or `dailyLimitExceeded`), mark key exhausted until **next Pacific midnight** (Google quota reset)
- Retry same search with next key synchronously (max N keys)
- Participant error only when all keys exhausted

**Rationale**: FR-008; zero-cost multi-project quota pooling.

**Alternatives considered**:
- Single key — rejected (spec target 4–5)
- Redis-backed pool state — deferred (single-replica acceptable for v1; document multi-replica caveat in plan)

## Decision: Participant search rate limit (10 / 5 min)

**Decision**: In-process rolling window per `participant_id`: store timestamps of successful search **attempts that reached YouTube** (or all attempts after validation — prefer counting after min-length check, before external call). Reject with `429` / `search rate limit exceeded` without calling YouTube.

**Rationale**: FR-007; protects quota and abuse.

**Alternatives considered**:
- IP-based limit — rejected (shared Wi‑Fi at events)
- DB persistence — rejected (ephemeral, no migration)

## Decision: New REST endpoints (not SSE)

**Decision**:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/youtube/search/config` | public | `{ enabled: bool }` — `enabled` iff ≥1 API key configured |
| GET | `/api/youtube/search` | participant | `?q=` text search → `SearchResponse` |

Search submit reuses **`POST /api/queue/submit`** with video id plus optional `search_query` → `original_query=search:{query}`.

**Rationale**: Minimal surface; submit limits unchanged in one code path.

**Alternatives considered**:
- `POST /api/queue/submit-from-search` — rejected (duplicate validation)
- SSE search results — rejected (request/response fit)

## Decision: HTTP client

**Decision**: `urllib.request` in `youtube_search_service.py` (same pattern as `youtube_meta.py`); no new production dependency.

**Rationale**: Stack consistency; `httpx` is dev-only for tests.

## Decision: `/participar` dual-path UX

**Decision** (from clarify pass 2):

| Rule | Implementation |
|------|----------------|
| Layout | Stacked: search block above URL block |
| Active path | `'search' \| 'url' \| null`; last meaningful interaction |
| URL activates path | Only on text edit (type/paste/clear), not focus |
| Search activates path | Row selection |
| Active section | CSS highlight (border/background) |
| Submit control | Single **Enviar canción** sticky footer |
| Toast coexistence | Footer `z-40`; notification toast `z-50`; main `padding-bottom` for both |

**Rationale**: FR-003b–003e; clarify session answers.

## Decision: Search disabled states

**Decision**:

- **No keys**: `config.enabled=false`; search UI visible, controls disabled, Spanish static message; URL submit active
- **All keys exhausted**: `config.enabled=true` but search returns `503`; Spanish error; URL active
- **Unauthenticated**: search UI behind same gate as submit (sign-in prompt); no API calls

## Decision: Testing strategy

**Decision**:
- `test_youtube_search.py`: mock YouTube HTTP; rate limit; failover; config endpoint; auth
- Extend `test_participant_submit.py` with video-id-only submit from search path (regression)
- Frontend: `participant.service.spec.ts` (search API); participate component tests for active path + sticky submit
- Full 005–007 regression in quickstart

**Rationale**: Constitution V; SC-002/006/007/008.

## Open questions

None blocking plan.
