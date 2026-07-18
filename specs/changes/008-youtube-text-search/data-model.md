# Data Model Delta: 008-youtube-text-search

## Persistence

**No Alembic migration.** Search queries and results are ephemeral (request/response only). Submit still creates `queue_entries` via existing 006 path.

## API DTOs

### `SearchConfigResponse`

| Field | Type | Notes |
|-------|------|-------|
| enabled | boolean | `true` when ≥1 non-empty API key in `JUKEBOX_YOUTUBE_API_KEYS` |

### `SearchResultItem`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| youtube_video_id | string | yes | 11-char id |
| title | string | yes | From `snippet.title` |
| channel_title | string | yes | From `snippet.channelTitle` |
| thumbnail_url | string | yes | Prefer `medium` or `default` from `snippet.thumbnails` |

### `SearchResponse`

| Field | Type | Notes |
|-------|------|-------|
| results | `SearchResultItem[]` | Max 10 (default); may be empty |

## Runtime entities (in-process only)

### `youtube_api_key_pool`

| State | Type | Notes |
|-------|------|-------|
| keys | `string[]` | Parsed from env |
| next_index | int | Round-robin cursor |
| exhausted_until | `dict[key, datetime]` | Pacific-midnight reset per key |

Not exposed to clients.

### `participant_search_rate_limit`

| State | Type | Notes |
|-------|------|-------|
| timestamps | `dict[participant_id, deque[datetime]]` | Rolling 5-minute window |
| limit | 10 | Per FR-007 |

Not persisted; multi-replica = per-process limits (acceptable v1; document in ops).

## Existing tables (unchanged)

### `queue_entries`

Search submit creates rows identical to URL submit:

- `youtube_video_id` from selected result
- `title`, `thumbnail_url` from search result (re-validated via oEmbed strict on submit)
- `original_query` = **`search:{participant_query}`** (e.g. `search:bohemian rhapsody`); URL path unchanged (006 stores URL/id string)
- `submitted_by_participant_id` set
- `status` = `pending_review`

## Client ephemeral state (`/participar`)

| Field | Type | Purpose |
|-------|------|---------|
| activePath | `'search' \| 'url' \| null` | Which path **Enviar canción** uses |
| searchQuery | string | Input field |
| searchResults | `SearchResultItem[]` | Last successful search list (replaced each search) |
| selectedResult | `SearchResultItem \| null` | Highlighted row |
| searchEnabled | boolean | From config endpoint |
| submitting | boolean | Shared submit in flight |

No server session for search UI state.
