# Context Pack: 008-youtube-text-search

**Change**: 008-youtube-text-search  
**Status**: implemented  
**Branch (git)**: `005-youtube-text-search`

## One-liner

YouTube text search on `/participar` so participants find and submit songs without pasting URLs (baseline 001 v1.1).

## Read first

1. `specs/changes/008-youtube-text-search/spec.md`
2. `specs/changes/001-foundation-jukebox/spec.md` — YouTube input v1/v1.1
3. `specs/changes/006-participant-oauth-submit/spec.md` — submit limits, Mis canciones
4. `specs/contracts/backend-api/contract.md` — submit API, metadata rules
5. `backend/app/services/youtube_meta.py`, `queue_service.submit_as_participant`

## Depends on

- 006 participant OAuth + submit
- 004 queue + moderation
- 005 voting (regression)
- 007 notifications (regression)

## Out of scope

- Web Push, operator search UI, playlist submit
- Paid YouTube API tiers or billing alerts (free quota only)

## Multi-key strategy

- Pool target: **4–5** API keys, round-robin, failover on quota before user error
- Submit metadata (URL path) still uses oEmbed — no API key

## Dual submit paths

- **Search**: query → results → select → **Enviar canción**
- **URL**: paste link/ID → **Enviar canción** (006)
- Both valid; URL never removed or demoted when search is added
- **One active path** at a time (last interaction: row select → search; URL text edit → URL; focus alone does not switch)
- **Stacked layout**: search block above URL block; both always visible
- **Active section** highlighted (border/background)
- **Single sticky** **Enviar canción** footer at bottom of viewport

## Next SDD step

`/speckit.implement`
