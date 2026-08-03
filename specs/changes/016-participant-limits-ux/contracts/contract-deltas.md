# Contract Deltas: 016-participant-limits-ux

**Contracts modified**: `backend-api`, `app-core`, `ops-platform`

## backend-api

### Participant state

`GET /api/participant/state` — `ParticipantStateResponse` adds:

- `max_searches_10_minutes: int`
- `max_votes_10_minutes: int`

SSE `state` events still omit participant-specific fields; client merges from last REST snapshot.

### Rate limits

| Limit | Window | ENV | Default |
|-------|--------|-----|---------|
| Search | 10 min rolling | `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT` | 10 |
| Votes | 10 min rolling | `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT` | 2 |

Search 429 `detail` unchanged: `search rate limit exceeded`.  
Vote 409 `detail` unchanged: `vote limit exceeded`.

### Pending submissions

`JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT` — unchanged semantics (013).

## app-core

### Live status badge

- Component `LiveStatusComponent` — fixed top-right, Spanish, single label
- Wired on Display, Admin, Participate (authenticated, post-onboarding)

### DisplayStateService / ParticipantStateService

- `connectionStatus$`: `connected` | `reconnecting` | `fallback`
- Shared `LiveConnectionManager`: SSE + exponential reconnect + 15s polling fallback

### Admin moderation

- Mobile: card list for pending entries (`md:hidden`)
- Desktop: table (`hidden md:block`)
- `overflow-x: hidden` on admin main

### Participate onboarding

- After auth, if `sessionStorage` lacks `jukebox.participantRulesAccepted`, show rules screen
- Limits from `GET /api/participant/state`
- Accept → set session flag → start SSE + full UI
- `votesRemainingLabel` uses `max_votes_10_minutes` from state

## ops-platform

ConfigMap + backend deployment env:

```yaml
JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT: "10"
JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT: "2"
```

`backend/.env.example` documents all three limit vars.

## Non-changes

- No new REST endpoints
- No SSE event types added
- No migration files
