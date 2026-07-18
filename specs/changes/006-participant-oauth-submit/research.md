# Research: 006-participant-oauth-submit

**Date**: 2026-07-18

## Decision: Google OAuth authorization code flow (backend)

**Decision**: Backend-driven OAuth 2.0 authorization code flow:
- `GET /api/auth/google/login` — generate signed `state`, redirect to Google consent
- `GET /api/auth/google/callback` — verify `state`, exchange code for tokens, fetch userinfo, upsert `participants` by `google_sub`, set `jukebox_participant_session`, redirect to frontend `/participar`

**Rationale**: Matches amrn-bull sibling pattern; keeps `client_secret` on server; works on mobile browsers via full redirect.

**Alternatives considered**:
- Google Identity Services popup in Angular — more JS complexity; harder to test; rejected for v1
- Implicit flow — deprecated; rejected

## Decision: OAuth state / CSRF

**Decision**: Signed short-lived `state` parameter via `itsdangerous` (same secret as session); optional cookie `jukebox_oauth_state` for double-check; reject callback on mismatch.

**Rationale**: No new infrastructure; sufficient for single-event deployment.

## Decision: Participant upsert on login

**Decision**: `google_sub` unique; on callback lookup by `google_sub` → update `email`, `display_name`, `avatar_url`; else insert new row. Reuse same `participant.id` for returning users.

**Rationale**: Spec FR-003; dev-created rows without `google_sub` remain separate (nullable unique).

## Decision: Participant submit endpoint

**Decision**: `POST /api/queue/submit` with `CurrentParticipant`, body `{ "youtube_url_or_id": string }` → 201 `QueueEntryRead`, creates `pending_review` with `submitted_by_participant_id`.

**Rationale**: Distinct from operator `dev-submit`; participant-authenticated; mirrors product flow.

## Decision: Submit limits (service layer)

**Decision**: Reuse `queue_service` with new `submit_as_participant(db, participant_id, url)`:
- Max 2 `pending_review` where `submitted_by_participant_id = participant`
- Max 1 own entry in `queued` ∪ `playing` (by `submitted_by_participant_id`)
- Global active duplicate `youtube_video_id` check (existing `_has_active_duplicate`)
- oEmbed/metadata via existing `youtube_meta.py`
- `bump_revision` on success

**Rationale**: Baseline 001 limits; stable English API `detail` codes; Spanish mapping in frontend per spec clarification.

| Limit | HTTP | API `detail` |
|-------|------|--------------|
| 2 pending | 429 | `pending submission limit reached` |
| 1 active queued/playing own | 429 | `active song limit reached` |
| Duplicate video | 409 | `video already in queue` |
| Invalid YouTube / oEmbed failure | 422 | `invalid youtube reference` |

## Decision: Mis canciones API

**Decision**: `GET /api/participant/submissions` → `SubmissionListResponse` (`entries: QueueEntryRead[]`) all rows where `submitted_by_participant_id = current`, ordered `created_at DESC`.

**Rationale**: Separate from votable queue in `ParticipantStateResponse`; refreshed on init, after submit, and on SSE `revision` bump.

## Decision: Frontend OAuth UX

**Decision**:
- Unauthenticated `/participar`: primary **Iniciar sesión con Google**; vote/submit controls **disabled** (SC-005)
- `window.location.href = apiBaseUrl + '/auth/google/login'` for OAuth
- Dev button **hidden** unless `environment.allowDevParticipantAuth` or query `?dev=1` — production build hides dev path; backend still gates dev-auth
- Callback redirect to `/participar` with `?oauth_error=` query on failure; component shows Spanish message
- Submit form: URL input + **Enviar canción** above vote list
- **Mis canciones** section with status badges (pendiente, en cola, sonando, rechazada, reproducida)

**Rationale**: Spec US1–US3; dev-auth secondary per FR-011.

## Decision: Alembic 0005

**Decision**: Add to `participants`: `google_sub` (string 255 unique nullable), `email` (string 255 nullable), `avatar_url` (string 500 nullable). Backfill not required for dev rows.

**Rationale**: 005 data-model planned columns; dev participants keep `google_sub` null.

## Decision: Config env vars

**Decision**:
- `JUKEBOX_GOOGLE_CLIENT_ID`
- `JUKEBOX_GOOGLE_CLIENT_SECRET`
- `JUKEBOX_GOOGLE_REDIRECT_URI` (must match Google console; e.g. `http://localhost:8000/api/auth/google/callback`)
- `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` (default `http://localhost:4200/participar`)

**Rationale**: `JUKEBOX_` prefix per constitution; explicit redirect URI for prod/k8s.

## Decision: Voting regression

**Decision**: No vote API changes; OAuth session uses same `jukebox_participant_session` cookie path as dev-auth.

**Rationale**: Spec FR-010; extend tests only.

## Open questions

None blocking.
