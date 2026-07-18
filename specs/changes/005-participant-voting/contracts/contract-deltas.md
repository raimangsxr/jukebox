# Contract Deltas: 005-participant-voting

**Status**: implemented — merged into active contracts

## backend-api

### New settings

| Env | Default | Purpose |
|-----|---------|---------|
| `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` | `false` | Enable `POST /api/participant/dev-auth` |

### Participant session

- Cookie name: `jukebox_participant_session`
- Signed payload contains `participant_id` (uuid string)
- Separate from operator `jukebox_session` / `user_id`
- Dependency `get_current_participant` → 401 `{"detail":"not authenticated"}` if missing/invalid

### New endpoints

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/participant/dev-auth` | public (if enabled) | 200 `ParticipantMeResponse` + Set-Cookie |
| GET | `/api/participant/me` | participant | 200 `ParticipantMeResponse` |
| GET | `/api/participant/state` | participant | 200 `ParticipantStateResponse` |
| POST | `/api/votes` | participant | 201 `VoteResponse` |

#### `POST /api/participant/dev-auth`

Body (optional): `{ "display_name": string }` (default `"Participante"`).

Only registered when `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`. Creates participant row if needed; sets `jukebox_participant_session`.

#### `POST /api/votes`

Body: `{ "queue_entry_id": uuid }`.

Response: `{ "id": uuid, "votes_remaining": 0-2, "state": ParticipantStateResponse optional }`.

### Participant DTOs

```text
ParticipantRead: { id, display_name, created_at }
ParticipantMeResponse: { participant: ParticipantRead }
ParticipantStateResponse: {
  revision, now_playing?, queue: QueueEntryRead[], votes_remaining: int, event_config: EventConfigSummary
}
VoteCreateRequest: { queue_entry_id: uuid }
VoteResponse: { id, votes_remaining, state?: ParticipantStateResponse }
```

`ParticipantStateResponse.queue` lists **all** `queued` entries (ordered by vote rules), not truncated to `queue_visible_count`.

### Vote rules (API behavior)

| Rule | HTTP |
|------|------|
| Target not `queued` | 409 `{"detail":"entry not votable"}` |
| Vote limit exhausted (2 in 5 min) | 409 `{"detail":"vote limit exceeded"}` |
| Entry not found | 404 `{"detail":"queue entry not found"}` |
| No participant session | 401 |

On success: `vote_count++`, positions recomputed, `revision` bumped, SSE broadcast.

### SSE auth change (004 extension)

| Method | Path | Auth (after 005) |
|--------|------|------------------|
| GET | `/api/events/stream` | operator session **or** participant session |
| GET | `/api/state` | operator session only (unchanged) |
| GET | `/api/participant/state` | participant session |

SSE event format unchanged (`event: state`, payload matches operator `StateResponse`).

**Client merge rule**: SSE `StateResponse` does **not** include `votes_remaining`. `/participar` clients MUST preserve `votes_remaining` from the last `GET /api/participant/state` or `POST /api/votes` response when applying SSE queue/revision updates (only refresh queue, `now_playing`, `revision` from stream).

### Public vs protected (after 005)

| Public | Protected (operator session) | Protected (participant session) | Dual-auth (operator **or** participant) |
|--------|------------------------------|--------------------------------|----------------------------------------|
| `GET /api/health` | `GET /api/auth/me` | `GET /api/participant/me` | `GET /api/events/stream` |
| `POST /api/auth/login` | `GET/POST/DELETE /api/tokens` | `GET /api/participant/state` | |
| `POST /api/auth/token` | `GET /api/state` | `POST /api/votes` | |
| `POST /api/participant/dev-auth` (when enabled) | `GET /api/queue/pending` | | |
| | `POST /api/queue/*` | | |

Participant session MUST NOT satisfy operator-protected routes (e.g. `POST /api/queue/skip` → 401).

Update `backend/tests/test_auth_policy.py` canonical public list.

### New persistence

- Tables `participants`, `votes` (see `data-model.md`)
- Alembic `0004_participants_and_votes.py`

### Unchanged (004)

All operator queue/moderation endpoints, embed token auth, `GET /api/state` for kiosk.

## app-core

### `/participar` (005 — replaces placeholder)

| State | UI |
|-------|-----|
| No participant session | Spanish copy: sign-in required to vote; OAuth arrives in 006; vote buttons disabled |
| Participant session | List all `queued` entries: title, vote count, vote button per row |
| Votes remaining | Header/badge: "X de 2 votos disponibles" |
| Limit exceeded | Inline Spanish error from 409 `vote limit exceeded` |
| Invalid target | Inline Spanish error from 409 `entry not votable` |
| Empty queue | Friendly empty state (no errors) |
| `now_playing` | Shown optionally as context; **no vote control** |

### New services

| Service | Responsibility |
|---------|----------------|
| `ParticipantService` | `devAuth()`, `me()`, `castVote(queueEntryId)`, participant session state |
| `ParticipantStateService` | `GET /api/participant/state`, SSE `/api/events/stream`, `state$`, `votesRemaining$`; merge SSE without overwriting `votes_remaining` |

### ParticipateComponent behavior

- On init: `ParticipantService.me()`; if 401, show sign-in prompt
- Dev quickstart: button "Entrar como participante (dev)" calls `devAuth()` when backend flag enabled
- On vote: `POST /api/votes`; update local `votes_remaining`; SSE keeps list in sync across tabs
- SSE disconnect: exponential backoff reconnect (mirror `DisplayStateService`)
- 401 on participant APIs: clear participant session, show sign-in prompt (no `/login` redirect)

### authInterceptor update

- `/participar` route: 401 on `/api/participant/*` or `/api/votes` does not navigate to `/login`
- Exempt paths: add `/api/participant/dev-auth`, `/api/participant/me`

### Display (004 — unchanged layout)

Kiosk `DisplayStateService` continues operator session + `GET /api/state`. Vote count badges update via same SSE `state` events when participants vote.

### Deferred

- Google OAuth sign-in button (006)
- Song submit form (006)
- Web Push (v1.1)

## ops-platform

No changes (003 delivered).
