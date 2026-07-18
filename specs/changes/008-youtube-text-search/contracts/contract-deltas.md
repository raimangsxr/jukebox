# Contract Deltas: 008-youtube-text-search

**Status**: draft — merge into active contracts before implementation

## backend-api

### Settings

| Env | Default | Notes |
|-----|---------|-------|
| `JUKEBOX_YOUTUBE_API_KEYS` | `""` | Comma-separated YouTube Data API keys (target 4–5) |
| `JUKEBOX_YOUTUBE_SEARCH_MAX_RESULTS` | `10` | Cap per search (optional; default 10) |
| `JUKEBOX_YOUTUBE_SEARCH_MIN_QUERY_LENGTH` | `2` | Min chars after trim |

### New endpoints

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/youtube/search/config` | public | 200 `SearchConfigResponse` |
| GET | `/api/youtube/search` | participant | 200 `SearchResponse` |

#### `GET /api/youtube/search`

Query: `q` (required string, min length after trim).

Success `200`:

```json
{
  "results": [
    {
      "youtube_video_id": "dQw4w9WgXcQ",
      "title": "Example",
      "channel_title": "Channel",
      "thumbnail_url": "https://i.ytimg.com/vi/.../mqdefault.jpg"
    }
  ]
}
```

#### Search errors

| Case | Status | `detail` |
|------|--------|----------|
| Not authenticated | 401 | `not authenticated` |
| Query too short / empty / whitespace-only | 422 | `invalid search query` |
| Participant rate limit (10/5 min) | 429 | `search rate limit exceeded` |
| Network failure / upstream timeout | 503 | `youtube search unavailable` |
| All API keys exhausted / search unavailable | 503 | `youtube search unavailable` |
| No keys configured | 503 | `youtube search unavailable` |

Frontend maps `detail` to Spanish (extend `ParticipantService` error maps).

#### Key pool behavior

- Round-robin key per search request
- Automatic retry on per-key quota exhaustion before returning 503
- Keys never returned in API responses

### Submit extension (search path)

`POST /api/queue/submit` body:

```json
{
  "youtube_url_or_id": "dQw4w9WgXcQ",
  "search_query": "never gonna give you up"
}
```

- `search_query` optional; when present and non-empty after trim, `queue_entries.original_query` = `search:{trimmed search_query}`; otherwise unchanged 006 behavior (stores URL/id string).
- Same limits and errors as 006.

### Route auth policy

| Path | Auth |
|------|------|
| `GET /api/youtube/search/config` | public |
| `GET /api/youtube/search` | participant |

Update `backend/tests/test_auth_policy.py` accordingly.

### New modules

| Module | Responsibility |
|--------|----------------|
| `routers/youtube.py` | config + search routes |
| `services/youtube_search_service.py` | API call, pool, parse results |
| `services/youtube_api_key_pool.py` | round-robin + exhausted tracking |
| `services/search_rate_limiter.py` | per-participant rolling window |

### Tests

- `backend/tests/test_youtube_search.py`
- `backend/tests/test_auth_policy.py` (008 paths)

### Unchanged

- SSE, votes, notifications, moderation routes
- oEmbed metadata for submit (strict validation on submit)

## app-core

### `/participar` submit area

| Rule | Value |
|------|-------|
| Layout | Stacked: **search block above URL block**; both always visible |
| Search trigger | **Buscar** button + **Enter**; no auto-search while typing |
| Result row | Title + thumbnail + channel; tap selects (highlight) |
| Active path | Last interaction: row select → search; URL text edit → URL; focus alone does not switch |
| Active section | Visual highlight (border/background) |
| Submit button | **Single** **Enviar canción** — **sticky footer** at viewport bottom |
| Search disabled | Section visible, controls disabled, Spanish message when `config.enabled=false` |
| URL path | Unchanged 006 behavior when search unused |

#### Spanish UI strings (add to frontend)

| Key | Copy |
|-----|------|
| search_heading | Buscar en YouTube |
| search_placeholder | Título o artista |
| search_button | Buscar |
| search_disabled | Búsqueda no disponible en este evento. Puedes pegar un enlace de YouTube. |
| search_empty | No hay resultados. Prueba otra búsqueda o pega un enlace. |
| search_rate_limit | Has hecho demasiadas búsquedas. Espera unos minutos o pega un enlace. |
| search_unavailable | La búsqueda no está disponible ahora. Puedes pegar un enlace de YouTube. |
| query_too_short | Escribe al menos 2 caracteres para buscar. |

### Extended services

| Service | Change |
|---------|--------|
| `ParticipantService` | `getSearchConfig()`, `searchYoutube(q)`, `mapSearchError()` |
| `ParticipateComponent` | dual-path state, search UI, sticky submit, section highlight |

### Layout notes

- Main content `padding-bottom` clears sticky footer
- Notification toast remains above footer (`z-index` > footer)

### Display / admin

Unchanged.

## ops-platform

| Env | Required | Notes |
|-----|----------|-------|
| `JUKEBOX_YOUTUBE_API_KEYS` | For search | Comma-separated; empty disables search UI |

Document in deployment README / K8s secret example (no keys in repo).
