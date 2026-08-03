# Context Pack: 016-participant-limits-ux

**Change**: 016-participant-limits-ux  
**Status**: draft  
**Branch (git)**: `016-participant-limits-ux`

## One-liner

Fix live connection status UX (SSE + fallback), mobile-friendly admin moderation, and participant rules screen with ENV-configurable limits after first login.

## Read first

1. `specs/changes/016-participant-limits-ux/spec.md`
2. `specs/changes/016-participant-limits-ux/plan.md`
3. `specs/contracts/backend-api/contract.md` — participant state, rate limits, SSE
4. `specs/contracts/app-core/contract.md` — `/participar`, admin, display services
5. `frontend/src/app/services/display-state.service.ts`, `participant-state.service.ts`
6. `backend/app/config.py`, `vote_service.py`, `search_rate_limiter.py`

## Depends on

- 005 participant voting (votes_remaining)
- 006 OAuth + submit
- 008 YouTube search rate limit
- 010 SSE hardening + event config

## Out of scope

- Server-side persistence of rules acceptance
- Participant route rename to `/participant`
- Full admin redesign

## Key decisions

- **Connection**: Shared live connection manager; states `connected` | `reconnecting` | `fallback`; single badge top-right; polling 15s after SSE failures
- **Admin mobile**: Card layout `< md`, table `≥ md` for pending moderation
- **Onboarding**: `sessionStorage` key `jukebox.participantRulesAccepted`; fetch limits from `GET /api/participant/state` before full SSE start
- **ENV**: `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT`, `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT`, `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT`; 10-minute rolling windows for search/vote

## Next SDD step

`/speckit-tasks` then verify implementation against spec
