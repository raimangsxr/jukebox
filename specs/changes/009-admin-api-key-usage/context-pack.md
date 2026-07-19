# Context Pack: 009-admin-api-key-usage

**Change**: 009-admin-api-key-usage  
**Status**: implemented  
**Branch (git)**: `006-admin-api-key-usage`

## One-liner

Operator admin view of per-key YouTube API daily usage (100/day) with exact attempt tracking and SSE live updates.

## Read first

1. `specs/changes/009-admin-api-key-usage/spec.md`
2. `specs/changes/008-youtube-text-search/plan.md` — key pool, search, metadata
3. `specs/contracts/backend-api/contract.md` — SSE stream, operator auth
4. `backend/app/services/youtube_api_key_pool.py`, `youtube_search_service.py`, `youtube_meta.py`
5. `backend/app/services/sse_hub.py`, `frontend/src/app/services/display-state.service.ts`

## Depends on

- 002 operator auth + `/admin`
- 008 YouTube key pool, search, metadata fetches

## Out of scope

- Editing API keys in admin
- Historical usage beyond current Pacific quota day
- HTTP polling for usage
- Participant-visible quota UI

## Key decisions

- **Persistence**: PostgreSQL `youtube_api_key_daily_usage` (migration 0006)
- **Counting**: Attempt-based before outbound HTTP (clarify)
- **Google exhausted**: Force display 100/0
- **Realtime**: `event: api_key_usage` on `/api/events/stream`
- **REST**: `GET /api/youtube/api-keys/usage` for initial snapshot
- **UI**: Section **Uso de API Keys** on `/admin`; Spanish; global reset label

## Next SDD step

`/speckit-tasks`
