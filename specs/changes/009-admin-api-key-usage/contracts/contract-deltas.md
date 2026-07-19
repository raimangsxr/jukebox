# Contract Deltas: 009-admin-api-key-usage

**Status**: draft — merge into active contracts before implementation

## backend-api

### New endpoint

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/youtube/api-keys/usage` | operator session | 200 `ApiKeyUsageListResponse` |

#### `GET /api/youtube/api-keys/usage`

Success `200`:

```json
{
  "keys": [
    {
      "index": 1,
      "label": "Clave 1",
      "masked_suffix": "…x7Kp",
      "used_count": 12,
      "remaining_count": 88,
      "daily_limit": 100,
      "exhausted": false
    }
  ],
  "daily_limit": 100,
  "quota_day": "2026-07-19",
  "next_reset_at": "2026-07-20T07:00:00+00:00"
}
```

- `keys` ordered by configuration index (1-based `index` / `label`)
- `masked_suffix`: last four characters of the raw key with leading ellipsis; never the full secret
- `next_reset_at`: next Pacific midnight (ISO-8601)

#### Errors

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated | 401 | `not authenticated` |
| Participant session (no operator) | 401 | `not authenticated` |

### SSE extension (same stream)

On `GET /api/events/stream` (operator **or** participant session), add:

| Event | Payload | When |
|-------|---------|------|
| `api_key_usage` | `ApiKeyUsageListResponse` | After any per-key usage change, exhaustion, or Pacific quota-day reset |

- Kiosk and participant clients MUST ignore unknown event types (existing behavior)
- Event is broadcast to all `/api/events/stream` subscribers; only `/admin` renders usage data
- `/admin` merges `api_key_usage` into the usage table

### Usage accounting rules

- Increment `used_count` by 1 **before** each outbound YouTube Data API HTTP request attributed to a configured key (search `search.list`, metadata `videos.list`)
- Increment applies regardless of HTTP success/failure once the request is sent
- Do not increment when no outbound request is sent (validation/rate-limit before pool)
- On Google quota-exhausted (403 quota reasons): set `used_count=100`, `exhausted=true` for that key
- Daily limit: 100 per key per Pacific quota day
- Failover: each key that sends an outbound request increments its own counter
- Pool `acquire_key()` MUST skip keys marked exhausted in DB for the current quota day (in addition to in-memory `exhausted_until` from 008)

### Route auth policy

| Path | Auth |
|------|------|
| `GET /api/youtube/api-keys/usage` | operator session |

### Migration

| Revision | Table |
|----------|-------|
| `0006_youtube_api_key_daily_usage` | `youtube_api_key_daily_usage` |

### Tests (add to contract test list)

- `backend/tests/test_youtube_api_key_usage.py` — increment, exhaustion, auth, persistence, Pacific roll
- Extend `backend/tests/test_youtube_search.py` — usage increment on search
- SSE `api_key_usage` emit in `test_youtube_api_key_usage.py` or `test_sse.py`

## app-core

### Admin UI — new section

| Section | Position | Content |
|---------|----------|---------|
| **Uso de API Keys** | After **Moderación**, before **Evento** | Table of keys + global reset label |

#### Table columns (Spanish)

| Column | Source |
|--------|--------|
| Clave | `label` + `masked_suffix` |
| Usados | `used_count` |
| Restantes | `remaining_count` |
| Límite | `daily_limit` (100) |
| Estado | **Activa** / **Agotada** from `exhausted` |

#### Copy

| Key | Spanish |
|-----|---------|
| `section_title` | Uso de API Keys |
| `reset_label` | Próximo reinicio: {formatted next_reset_at} |
| `empty_state` | No hay API keys de YouTube configuradas. |
| `status_active` | Activa |
| `status_exhausted` | Agotada |
| `load_error` | No se pudo cargar el uso de API keys. |

#### Data flow

1. On `/admin` init: `GET /api/youtube/api-keys/usage`
2. Subscribe to `api_key_usage` on existing `DisplayStateService` SSE connection
3. No HTTP polling for usage

### Services

- Extend `DisplayStateService` with `apiKeyUsage$` (or equivalent) fed by SSE `api_key_usage`
- Kiosk `/` does not subscribe to usage UI (ignores event)

### Unchanged

- Moderación, tokens, participate, display, voting, notifications
