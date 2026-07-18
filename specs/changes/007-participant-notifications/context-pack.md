# Context Pack: 007-participant-notifications

**Change**: 007-participant-notifications  
**Status**: implemented  
**Branch (git)**: `004-participant-notifications`

## One-liner

SSE `notification` events for `song.approved` and `song.up_next`; bottom Spanish toast queue on `/participar`.

## Read first

1. `specs/changes/007-participant-notifications/spec.md`
2. `specs/changes/007-participant-notifications/plan.md`
3. `specs/changes/007-participant-notifications/research.md`
4. `specs/contracts/backend-api/contract.md` — SSE section
5. `backend/app/services/sse_hub.py`, `queue_service.py`
6. `frontend/src/app/services/participant-state.service.ts`

## Depends on

- 004 approve/skip queue lifecycle
- 005 participant SSE on `/participar`
- 006 `submitted_by_participant_id` attribution

## Out of scope

- Web Push, reject toasts, catch-up banners, new HTTP routes

## Next SDD step

Change closed — run `quickstart.md` manually on a live stack if desired.
