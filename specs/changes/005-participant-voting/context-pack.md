# Context Pack: 005-participant-voting

## Mandatory reads

1. `specs/manifest.yml`
2. `specs/changes/005-participant-voting/spec.md`
3. `specs/contracts/backend-api/contract.md`
4. `specs/contracts/app-core/contract.md`
5. `specs/changes/005-participant-voting/contracts/contract-deltas.md`
6. `specs/changes/004-kiosk-display-queue/contracts/contract-deltas.md` (SSE + queue baseline)

## Reference implementation

- 004 `queue_service._recompute_positions`, `state_service.bump_revision`, `sse_hub`
- 004 `DisplayStateService` pattern for `ParticipantStateService`
- `frontend/src/app/participate/` (replace placeholder)
- amrn-bull participant session patterns (sibling)

## Code entrypoints (planned)

### Backend

- `backend/app/models.py` — `Participant`, `Vote`
- `backend/app/services/vote_service.py`, `participant_session.py`
- `backend/app/security.py` — `get_current_participant`, stream dual-auth
- `backend/app/routers/participant.py`, `votes.py`
- `backend/app/routers/state.py` — extend SSE auth
- `backend/alembic/versions/0004_participants_and_votes.py`
- `backend/app/config.py` — `allow_dev_participant_auth`
- `backend/app/main.py` — mount routers

### Frontend

- `frontend/src/app/participate/participate.component.*`
- `frontend/src/app/services/participant.service.ts`
- `frontend/src/app/services/participant-state.service.ts`
- `frontend/src/app/auth.interceptor.ts` — `/participar` 401 handling

## Tests (planned)

- `backend/tests/test_votes.py`
- `backend/tests/test_participant_auth.py`
- Update `backend/tests/test_sse.py`, `test_auth_policy.py`
- Manual: `quickstart.md` vote + SSE flows

## Out of scope

- Google OAuth (006)
- Song submit / `pending_review` from participant (006)
- Web Push, kiosk-screen repo, K8s manifest changes
- Operator vote controls

## Do not read by default

- `specs/changes/003-kubernetes-manifests/` (ops only)
- `specs/archive/**`
