# Context Pack: 002-operator-auth-embed-tokens

## Mandatory reads

1. `specs/manifest.yml`
2. `specs/changes/002-operator-auth-embed-tokens/spec.md`
3. `specs/contracts/backend-api/contract.md`
4. `specs/contracts/app-core/contract.md`
5. `specs/changes/001-foundation-jukebox/spec.md` (auth split clarifications)

## Reference implementation

- `amrn-bull/specs/changes/003-auth-and-tokens/`
- `amrn-bull/backend/app/routers/auth.py`, `tokens.py`, `security.py`
- `amrn-bull/frontend/src/app/services/auth.service.ts`, `auth.guard.ts`, `auth.interceptor.ts`

## Code entrypoints (planned)

### Backend

- `backend/app/models.py` — add `ApiToken`
- `backend/app/schemas.py` — auth/token DTOs (new file)
- `backend/app/security.py` — extend with `get_current_user`, token helpers
- `backend/app/routers/auth.py`, `tokens.py` (new)
- `backend/app/main.py` — mount routers
- `backend/alembic/versions/0002_api_tokens.py` (new)

### Frontend

- `frontend/src/app/services/auth.service.ts` (new)
- `frontend/src/app/auth.interceptor.ts`, `auth.guard.ts` (new)
- `frontend/src/app/login/login.component.*` — wire form
- `frontend/src/app/admin/admin.component.*` — tokens panel
- `frontend/src/app/app.config.ts` — interceptor
- `frontend/src/app/app.routes.ts` — guards
- `frontend/src/app/app.component.ts` — bootstrap auth

## Tests (planned)

- `backend/tests/test_auth.py`
- `backend/tests/test_tokens.py`
- Extend `backend/tests/conftest.py` — `authed_client`
- Manual: iframe `/?token=` smoke per quickstart.md

## Out of scope

- Google OAuth `/participar`
- `jukebox_participant_session`
- Queue, SSE, event-config write APIs

## Do not read by default

- `specs/changes/001-foundation-jukebox/analyze.md` (historical)
- `specs/archive/**`
