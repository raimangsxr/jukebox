# Data Model Delta: 009-admin-api-key-usage

## Persistence (new migration `0006`)

### `youtube_api_key_daily_usage`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| key_hash | VARCHAR(64) | NOT NULL | SHA-256 hex of raw API key |
| quota_day | DATE | NOT NULL | Pacific calendar date |
| used_count | INTEGER | NOT NULL, default 0 | 0–100 inclusive |
| exhausted | BOOLEAN | NOT NULL, default false | true when used_count=100 or Google quota error |
| updated_at | TIMESTAMPTZ | NOT NULL | last mutation |

**Unique**: `(key_hash, quota_day)`

**Indexes**: `quota_day` (optional cleanup)

Rows exist only for keys currently in `JUKEBOX_YOUTUBE_API_KEYS` for the active quota day (ensured on read/write). Removed keys drop from API list (historical rows may remain in DB but are not exposed).

### State transitions (per key per quota day)

```text
[0 used, active]
  -- record_attempt (each outbound send) --> used_count += 1
  -- used_count reaches 100 --> exhausted=true
  -- Google quota error --> used_count=100, exhausted=true

[exhausted]
  -- no further pool selection for that key until quota day roll (pool + DB)

[Pacific midnight]
  -- new quota_day --> used_count=0, exhausted=false (new or reset rows)
```

## API DTOs

### `ApiKeyUsageItem`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| index | integer | yes | 1-based display order in config |
| label | string | yes | e.g. `Clave 1` |
| masked_suffix | string | yes | Last 4 chars of key, e.g. `…x7Kp` |
| used_count | integer | yes | 0–100 |
| remaining_count | integer | yes | `max(0, 100 - used_count)` |
| daily_limit | integer | yes | Always `100` |
| exhausted | boolean | yes | |

### `ApiKeyUsageListResponse`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| keys | `ApiKeyUsageItem[]` | yes | Ordered by config index |
| daily_limit | integer | yes | `100` |
| quota_day | string (date) | yes | Pacific ISO date |
| next_reset_at | string (datetime) | yes | Next Pacific midnight ISO-8601 |

Empty `keys` when no API keys configured.

## SSE payload

`event: api_key_usage` — `data` is JSON `ApiKeyUsageListResponse` (same as REST).

Emitted when:
- Any `record_attempt` changes counts
- `mark_google_exhausted` runs
- Quota day rolls on first touch after midnight Pacific

## Runtime integration (unchanged tables)

### `youtube_api_key_pool` (008, extended behavior)

| State | Notes |
|-------|-------|
| exhausted_until | Still in-memory for fast acquire; kept in sync when DB marks exhausted |
| acquire_key | Skip keys where DB `exhausted=true` for current quota day **or** in-memory exhausted |

Pool remains ephemeral for round-robin cursor; authoritative counts in PostgreSQL.

## Client ephemeral state (`/admin`)

| Field | Type | Purpose |
|-------|------|---------|
| apiKeyUsage | `ApiKeyUsageListResponse \| null` | Table + reset label |
| apiKeyUsageError | string \| null | Spanish load error |

No local persistence; merges REST snapshot + SSE events.
