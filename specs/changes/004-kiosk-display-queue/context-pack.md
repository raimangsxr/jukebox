# Context Pack: 004-kiosk-display-queue

## Mandatory reads

1. `specs/manifest.yml`
2. `specs/changes/004-kiosk-display-queue/spec.md`
3. `specs/contracts/backend-api/contract.md`
4. `specs/contracts/app-core/contract.md`
5. `specs/changes/004-kiosk-display-queue/contracts/contract-deltas.md`

## Reference implementation

- amrn-bull display state + SSE patterns
- `specs/changes/001-foundation-jukebox/data-model.md` (queue lifecycle)
- `frontend/src/app/display/` (replace placeholders)
- `frontend/src/app/admin/admin.component.*` (add moderation section)

## Code entrypoints (planned)

### Backend

- `backend/app/models.py` — `QueueEntry`, `JukeboxRuntime`
- `backend/app/services/queue_service.py`, `state_service.py`, `youtube_meta.py`
- `backend/app/routers/state.py`, `queue.py`
- `backend/alembic/versions/0003_queue_and_runtime.py`
- `backend/app/main.py` — mount routers

### Frontend

- `frontend/src/app/display/` — layout + child components
- `frontend/src/app/services/display-state.service.ts`
- `frontend/src/app/services/queue-admin.service.ts`
- `frontend/src/app/admin/admin.component.*` — moderation UI

## Tests (planned)

- `backend/tests/test_queue.py`
- `backend/tests/test_state.py`
- `backend/tests/test_sse.py`
- Update `backend/tests/test_auth_policy.py`
- Manual: `quickstart.md` kiosk + moderation flows

## Out of scope

- Participant Google OAuth and `/participar` submit/vote UI (005–006)
- Web Push, kiosk-screen repo, K8s manifest changes
- YouTube text search (v1.1)

## Do not read by default

- `specs/changes/003-kubernetes-manifests/` (ops only, no app behavior)
- `specs/archive/**`
