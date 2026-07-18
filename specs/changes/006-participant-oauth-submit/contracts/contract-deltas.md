# Contract Deltas: 006-participant-oauth-submit

**Status**: draft — merge into active contracts before implementation

## backend-api

### New settings

| Env | Default | Purpose |
|-----|---------|---------|
| `JUKEBOX_GOOGLE_CLIENT_ID` | required in prod | Google OAuth client id |
| `JUKEBOX_GOOGLE_CLIENT_SECRET` | required in prod | Google OAuth client secret |
| `JUKEBOX_GOOGLE_REDIRECT_URI` | e.g. `http://localhost:8000/api/auth/google/callback` | Registered redirect URI |
| `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` | `http://localhost:4200/participar` | Frontend redirect after OAuth |

### Google OAuth (participant)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/auth/google/login` | public | 302 redirect to Google |
| GET | `/api/auth/google/callback` | public | 302 redirect to `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` + Set-Cookie `jukebox_participant_session` |

Callback on success: redirect to return URL (optional `?oauth=ok`). On failure: redirect with `?oauth_error=denied|invalid_state|exchange_failed` (Spanish handling in frontend).

### Participant submit

| Method | Path | Auth | Response |
|--------|------|------|----------|
| POST | `/api/queue/submit` | participant | 201 `QueueEntryRead` |
| GET | `/api/participant/submissions` | participant | 200 `SubmissionListResponse` |

#### `POST /api/queue/submit`

Body: `{ "youtube_url_or_id": string }`.

Creates `pending_review` with `submitted_by_participant_id`; bumps `revision`.

#### Submit errors

API returns stable **English** `detail` strings (programmatic). Frontend `/participar` maps them to Spanish user-facing text.

| Case | Status | API `detail` | Spanish (UI) |
|------|--------|--------------|--------------|
| Pending limit (2) | 429 | `pending submission limit reached` | Has alcanzado el límite de canciones pendientes (2). |
| Active own queued/playing limit (1) | 429 | `active song limit reached` | Ya tienes una canción activa en cola o sonando. |
| Duplicate active video | 409 | `video already in queue` | Ese vídeo ya está en la cola o pendiente de revisión. |
| Invalid YouTube / metadata failure | 422 | `invalid youtube reference` | Enlace de YouTube no válido o vídeo no disponible. |
| Not authenticated | 401 | `not authenticated` | Inicia sesión para continuar. |

### Participant profile (extend)

`ParticipantRead` adds optional `email`, `avatar_url` (no `google_sub` in API).

### Public vs protected (after 006)

| Public | Protected (operator) | Protected (participant) | Dual-auth |
|--------|---------------------|-------------------------|-----------|
| `GET /api/health` | (005 operator routes) | `GET /api/participant/me` | `GET /api/events/stream` |
| `POST /api/auth/login` | | `GET /api/participant/state` | |
| `POST /api/auth/token` | | `GET /api/participant/submissions` | |
| `GET /api/auth/google/login` | | `POST /api/votes` | |
| `GET /api/auth/google/callback` | | `POST /api/queue/submit` | |
| `POST /api/participant/dev-auth` (when enabled) | | | |

Update `backend/tests/test_auth_policy.py`.

### Persistence

- Migration `0005_participant_google_profile.py`
- `google_service.py` or `oauth_google.py` for token exchange + userinfo

### Unchanged

- Operator `dev-submit`, moderation, votes (005), kiosk `GET /api/state`
- `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` dev bootstrap

## app-core

### `/participar` (006 — extends 005)

| Region | Content |
|--------|---------|
| Unauthenticated | **Iniciar sesión con Google** (primary); vote/submit **disabled** (SC-005); dev sign-in **hidden** unless `environment.allowDevParticipantAuth` or `?dev=1` |
| Authenticated header | Display name, avatar, votes remaining |
| Submit | YouTube URL field + **Enviar canción** |
| Cola votable | Unchanged from 005 |
| Mis canciones | List with Spanish status badges + rejection reason |

### Status labels (Spanish)

| status | Label |
|--------|-------|
| pending_review | Pendiente de revisión |
| queued | En cola |
| playing | Sonando |
| played | Reproducida |
| rejected | Rechazada |

### New / extended services

| Service | Responsibility |
|---------|----------------|
| `ParticipantService` | + `startGoogleLogin()` (full redirect), parse `oauth_error` query |
| `ParticipantStateService` | + `refreshSubmissions()`, reload submissions on SSE revision |
| `ParticipantService` | + `submitSong(url)`, `getSubmissions()`, `mapSubmitError(detail)` → Spanish |

### OAuth UX

- Login: navigate to `GET /api/auth/google/login` (not XHR)
- Callback lands on `/participar`; component calls `loadMe()` and starts state/SSE
- 401 on participant APIs: show sign-in (no `/login` redirect)

### Display (004)

Unchanged; vote counts update when participants vote (005).

### Deferred

- In-app notifications (007+)
- YouTube text search (v1.1)

## ops-platform

- Document `JUKEBOX_GOOGLE_*` secrets in K8s/compose examples (no manifest structure change).
