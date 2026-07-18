# Research: 005-participant-voting

**Date**: 2026-07-18

## Decision: Participant session cookie

**Decision**: Separate signed cookie `jukebox_participant_session` containing `participant_id` (uuid string). Implemented via `participant_session.py` (itsdangerous + `settings.session_secret`, env `JUKEBOX_SESSION_SECRET`), not Starlette `SessionMiddleware` (operator-only `jukebox_session`).

**Rationale**: Product baseline (001) requires split auth; operator and participant can coexist in different browser contexts.

**Alternatives considered**:
- Shared session cookie — rejected; security and role confusion
- JWT bearer for mobile — deferred; cookies match sibling bull pattern

## Decision: Dev participant bootstrap

**Decision**: `POST /api/participant/dev-auth` with optional `{ "display_name": string }` when `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true` (default false). Creates or reuses participant row and sets session cookie.

**Rationale**: Mirrors `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT` from 004; enables pytest and manual QA before 006 OAuth.

**Alternatives considered**:
- Hardcoded test participant in pytest only — rejected; manual quickstart needs HTTP path

## Decision: Vote API shape

**Decision**: `POST /api/votes` body `{ "queue_entry_id": uuid }` → 201 `VoteResponse` with updated `votes_remaining` and optional full `ParticipantStateResponse`.

**Rationale**: Resource-oriented; one endpoint regardless of target entry; easy to test.

**Alternatives considered**:
- `POST /api/queue/{id}/vote` — acceptable but couples to queue router; votes get own router

## Decision: Rolling 5-minute window

**Decision**: Count rows in `votes` where `participant_id = current` and `created_at >= now() - 5 minutes`. Limit = 2. No separate `participant_vote_windows` table for v1.

**Rationale**: Spec assumption; simple and auditable; index on `(participant_id, created_at)`.

**Alternatives considered**:
- Dedicated window row — rejected for v1 complexity

## Decision: Vote side effects

**Decision**: On valid vote: insert `votes` row, increment `queue_entries.vote_count`, call existing `_recompute_positions` from queue_service, `bump_revision` (SSE broadcast).

**Rationale**: Reuses 004 ordering and realtime path; single source of truth for strip order.

## Decision: Participant state and SSE access

**Decision**:
- `GET /api/participant/state` — participant auth; returns `ParticipantStateResponse` (queue all `queued`, `now_playing`, `votes_remaining`, `event_config` subset).
- Extend `GET /api/events/stream` to accept **either** operator session (004) **or** participant session via `get_current_participant_or_operator` dependency.

**Rationale**: Participants must receive same SSE `state` events as kiosk without operator credentials; avoids duplicate stream logic.

**Alternatives considered**:
- Separate `/api/participant/events/stream` — duplicate hub wiring; rejected
- Public SSE — rejected; unnecessary exposure

## Decision: `/participar` frontend

**Decision**:
- `ParticipantService` — dev-auth, me, votes remaining, cast vote
- Reuse `DisplayStateService` pattern: `ParticipantStateService` with `GET /api/participant/state` + shared SSE URL (credentials)
- `ParticipateComponent` — sign-in prompt when unauthenticated; queue list with vote buttons; "X de 2 votos disponibles"

**Rationale**: Parallel to display architecture from 004; minimal new patterns.

## Decision: Alembic 0004

**Decision**: Tables `participants`, `votes`; FK `votes.queue_entry_id` → `queue_entries`, `votes.participant_id` → `participants`. Index `(participant_id, created_at)`.

**Rationale**: Matches 001 data model; `participants` minimal until 006 adds Google columns (nullable in 006 migration).

## Open questions

None blocking — OAuth deferred to 006 per spec clarify session.
