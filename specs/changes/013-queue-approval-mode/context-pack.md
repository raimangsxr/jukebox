# Context Pack: 013-queue-approval-mode

**Change**: 013-queue-approval-mode  
**Status**: draft  
**Branch (git)**: `013-queue-approval-mode`

## One-liner

Operator-selectable queue mode on `/admin`: **Moderado** (approve before queue) vs **Libre** (direct to queue), persisted on `event_config`.

## Read first

1. `specs/changes/013-queue-approval-mode/spec.md` (incl. clarifications 2026-07-30)
2. `specs/changes/013-queue-approval-mode/plan.md`
3. `specs/contracts/backend-api/contract.md` — queue submit, moderation, event-config, notifications
4. `backend/app/services/queue_service.py` — `submit_as_participant`, `approve_entry`
5. `backend/app/routers/event_config.py`, `frontend/src/app/admin/admin.component.*`

## Depends on

- 004 queue + moderation
- 006 participant submit
- 007 `song.approved` notifications
- 010 event-config editor + SSE revision bump

## Out of scope

- Bulk approve, mode history/audit
- Participant-visible mode indicator
- New submission cap env var (reuse `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT`)
- Kiosk UI changes

## Key decisions

- **Storage**: `event_config.queue_mode` (`moderated` \| `free`), migration `0009`, default `moderated`
- **API**: `PUT /api/event-config/queue-mode`; `queue_mode` on `EventConfigRead` only
- **Free submit**: `queued` + `emit_song_approved`; cap counts `queued` per participant
- **UI**: Selector in **Moderación**; confirm dialog; Spanish labels Moderado/Libre
- **Legacy pendings**: unchanged on mode switch until operator acts

## Next SDD step

`/speckit-tasks`
