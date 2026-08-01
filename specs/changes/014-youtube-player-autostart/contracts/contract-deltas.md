# Contract Deltas: 014-youtube-player-autostart

**Status**: merged into active contracts at implementation.

Modifies: `backend-api`, `app-core`, `ops-platform`.

---

## backend-api

### Auto-start on enqueue (changes 004, 013)

When `_enqueue_entry` succeeds (approve or free-mode submit):

- If `get_now_playing(db)` is `None` and `_top_queued(db)` is not `None`, promote top `queued` → `playing` (same semantics as idle branch of `POST /api/queue/skip`).
- `emit_song_up_next` on promoted entry.
- `bump_revision` via existing callers (`approve_entry`, `submit_as_participant`).

`POST /api/queue/skip` unchanged.

### Tests

- Extend `test_queue.py`: approve idle → state has `now_playing`; approve while playing → `now_playing` unchanged.
- Extend `test_queue_approval_mode.py` or `test_queue.py`: free submit idle → `now_playing`.

---

## app-core

### YoutubePlayerComponent

- Create player when `videoId` set without requiring activation (muted autoplay).
- `playerVars`: `autoplay: 1`, `mute: 1`, `playsinline: 1`, `rel: 0`, `modestbranding: 1`.
- Overlay **Activar sonido** when muted and not sound-activated; **Activar reproducción** removed as blocking gate.
- `activate()`: `unMute()` + `playVideo()`; persist `sessionStorage` key `jukebox.playerActivated`.
- On `activate()`, if `!now_playing && queue.length > 0`, call `advancePlayback()`.
- Retry `playVideo()` when state remains `CUED`/`PAUSED` after load.

### Admin Moderación

- Playback status line: «Sonando: {title}» or «Cola lista — {n} canciones en espera» or idle empty message.
- **Iniciar reproducción** / **Saltar canción** unchanged.

---

## ops-platform

### Kiosk autoplay (deploy/k8s/README.md)

- Chromium kiosk: `--autoplay-policy=no-user-gesture-required` for sound without tap on dedicated hardware.
- Parent iframe embed: `allow="autoplay"` on kiosk-screen / bull iframe.
