# Context Pack: 006-participant-oauth-submit

## Mandatory reads

1. `specs/manifest.yml`
2. `specs/changes/006-participant-oauth-submit/spec.md`
3. `specs/contracts/backend-api/contract.md`
4. `specs/contracts/app-core/contract.md`
5. `specs/changes/006-participant-oauth-submit/contracts/contract-deltas.md`
6. `specs/changes/005-participant-voting/contracts/contract-deltas.md` (participant session + votes)

## Reference implementation

- amrn-bull Google OAuth redirect + callback patterns
- 005 `participant_session.py`, `ParticipantStateService`
- 004 `queue_service.create_pending_entry`, `youtube_meta.py`
- `frontend/src/app/participate/` (extend, do not replace vote UI)

## Code entrypoints (planned)

### Backend

- `backend/app/config.py` — Google OAuth settings
- `backend/app/models.py` — extend `Participant`
- `backend/app/services/google_oauth_service.py` — login URL, callback, upsert
- `backend/app/services/queue_service.py` — `submit_as_participant`
- `backend/app/routers/auth_google.py` — login + callback routes
- `backend/app/routers/participant.py` — `GET /submissions`
- `backend/app/routers/queue.py` or `submit.py` — `POST /api/queue/submit`
- `backend/alembic/versions/0005_participant_google_profile.py`
- `backend/tests/test_oauth_google.py`, `test_participant_submit.py`

### Frontend

- `frontend/src/app/participate/participate.component.*` — Google button, submit form, Mis canciones
- `frontend/src/app/services/participant.service.ts` — OAuth redirect, submit, submissions

## Tests (planned)

- OAuth callback upsert + cookie (mocked Google HTTP)
- Submit limits 429/409
- Vote regression (005)
- Manual: `quickstart.md`

## Out of scope

- Notifications (007+)
- YouTube search
- Operator Google login
- Kiosk layout changes

## Do not read by default

- `specs/changes/003-kubernetes-manifests/` (ops reference only unless wiring secrets)
- `specs/archive/**`
