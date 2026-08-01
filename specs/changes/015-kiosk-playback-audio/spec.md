---
id: 015-kiosk-playback-audio
type: change
status: implemented
modifies:
  - backend-api
  - app-core
  - ops-platform
depends_on:
  - 014-youtube-player-autostart
requires_contract_update: true
read_by_default: true
---

# Feature: Kiosk playback with audio

**Status**: Implemented

## Goals

- Detect browser autoplay-with-sound capability on kiosk load.
- Start YouTube playback unmuted when kiosk Chromium is configured correctly.
- Keep muted fallback + overlay for dev / misconfigured displays.
- Report `audio_mode` from display to admin via SSE.

## Acceptance

- Kiosk with `--autoplay-policy=no-user-gesture-required`: first song plays with sound, no overlay.
- Standard browser: muted autoplay + overlay; admin shows «Sonando sin audio» + hint.
- `POST /api/display/playback-status` updates operator SSE `playback_status`.
- Playwright stack e2e: `npm run test:e2e:stack` (Docker + ng serve + kiosk audio flow).
