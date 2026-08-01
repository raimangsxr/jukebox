# Context Pack: 014-youtube-player-autostart

**Change**: 014-youtube-player-autostart  
**Status**: implemented

## One-liner

Auto-start `now_playing` on enqueue when idle; muted YouTube bootstrap; sound overlay; admin playback status.

## Read first

1. `specs/changes/014-youtube-player-autostart/spec.md`
2. `backend/app/services/queue_service.py` — `_enqueue_entry`, `skip_or_advance`
3. `frontend/src/app/display/youtube-player.component.ts`
4. `frontend/src/app/admin/admin.component.*`

## Key decisions

- `_maybe_auto_start_playback(db)` after `_enqueue_entry` when idle + queued
- Player: `mute:1` + `autoplay:1` without activation gate; overlay for unmute only
- `sessionStorage` `jukebox.playerActivated` for sound unlock persistence
