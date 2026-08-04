# Contract Deltas: 022-limit-reset-countdown

**Status**: merged (022 implemented).

Modifies: `backend-api`, `app-core`. Unless **changed** or **new**, prior contract behavior is unchanged.

---

## backend-api

### Participant rate limits — window semantics (**changed**)

**Previous**: Rolling 10-minute window for votes (count votes with `created_at >= now − 10min`); in-memory rolling window for participant YouTube searches.

**New**: **Fixed window** per limit type:
- Window starts on **first consumption at full quota** (`votes_remaining == max` or `searches_remaining == max`).
- `*_quota_reset_at = now + 10 minutes` (deployment setting unchanged).
- Further consumptions in the same window **do not** extend reset time.
- When `now >= *_quota_reset_at`, quota restores to max; columns cleared.

### `GET /api/participant/state` — response (**changed**)

`ParticipantStateResponse` adds:

| Field | Type | Description |
|-------|------|-------------|
| `searches_remaining` | int | Searches left in current window (or max if no window) |
| `votes_quota_reset_at` | ISO 8601 datetime \| null | When full vote quota restores; null = no countdown |
| `searches_quota_reset_at` | ISO 8601 datetime \| null | When full search quota restores; null = no countdown |

Existing fields unchanged: `votes_remaining`, `max_votes_10_minutes`, `max_searches_10_minutes`, etc.

**Countdown rule**: Client shows «Cupo completo en MM:SS» when corresponding `*_quota_reset_at` is non-null and in the future. Server sets `reset_at` on first consumption at full quota and clears it when the window expires (equivalent to spec FR-004/FR-006).

### Vote / search endpoints (**changed behavior**)

- `POST /api/votes` — uses fixed window; `VoteResponse.state` includes new fields.
- `GET /api/youtube/search` — participant searches persist to `participant_searches`; rate limit uses fixed window (DB-backed).
- Invalid search query / non-votable entry → no window side effects.

### Database (**new**)

- `participants.votes_quota_reset_at`, `participants.searches_quota_reset_at` (nullable timestamptz)
- `participant_searches` table

Alembic migration required.

### SSE (**unchanged payload**)

`state` SSE events still omit participant-specific limits; clients call **`GET /api/participant/state` via `refresh()`** on every participant SSE `state` event (multi-tab sync), plus vote/search response, poll fallback, and **client countdown expiry** (FR-014).

---

## app-core

### Participate (`/participar`) — limit display (**changed**)

**Votes (header)**:
- Always: «X de Y votos disponibles»
- When `votes_quota_reset_at` active: append «· Cupo completo en MM:SS» (replaces legacy «cada 10 min)»)
- When no window: **no** countdown segment

**Searches (Buscar en YouTube subsection)**:
- Always: «X de Y búsquedas disponibles»
- When `searches_quota_reset_at` active: append «· Cupo completo en MM:SS»

**Countdown behavior**:
- Tick every second client-side from `*_quota_reset_at`
- At `00:00`: auto `ParticipantStateService.refresh()` without page reload
- After vote/search: merge full `state` from API response

### Shared utilities (**new**)

- `limit-countdown.util.ts` — `secondsUntil`, `formatCountdownMmSs`, `shouldShowQuotaCountdown`
- `participant-limits.util.ts` — label helpers accept optional `resetAt`

### Error messages (**unchanged copy, coherent timing**)

`voteLimitExceededMessage` / `searchRateLimitMessage` remain; countdown visible alongside when limit hit (FR-009).

### Out of scope (optional polish)

- Kiosk QR static hints (may still say «cada 10 minutos» until separate change)
- Onboarding «Normas» screen: verify static text does not contradict live countdown (T033 Phase 8); update copy if it still says «cada 10 min» without mentioning the live timer

---

## ops-platform

No manifest/compose changes. Window duration remains `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT` / `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT`.
