# Data Model: 017-admin-queue-history-filler

## Persistence (new migration `0010`)

### `queue_entries` — new columns

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| priority | VARCHAR(16) | NOT NULL, default `normal` | `normal` \| `low` |
| source | VARCHAR(24) | NOT NULL, default `participant` | ver enum abajo |
| finished_at | TIMESTAMPTZ | NULL | set on `played` / `rejected` |

**Index**: `(status, finished_at DESC)` para historial paginado.

**Backfill**:
- `priority = 'normal'`, `source = 'participant'` en filas existentes.
- `finished_at = created_at` donde `status IN ('played','rejected')`.

### `filler_reserve_entries` — new table

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK | uuid |
| youtube_video_id | VARCHAR(11) | NOT NULL, UNIQUE | |
| title | VARCHAR(500) | NOT NULL | |
| thumbnail_url | VARCHAR(500) | NULL | |
| duration_sec | INTEGER | NULL | |
| original_query | VARCHAR(500) | NOT NULL | URL o `search:{q}` |
| position | INTEGER | NOT NULL | 1-based, único por orden |
| created_at | TIMESTAMPTZ | NOT NULL | server default now() |

**Unique**: `youtube_video_id` (una copia por reserva).

**Límite**: máx. 50 ítems (validación en servicio; constante `MAX_FILLER_RESERVE_ENTRIES`).

### `event_config` — new column

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| filler_auto_inject_enabled | BOOLEAN | NOT NULL, default `true` | FR-010 |

## Application enums

### `QueueEntryPriority`

| Value | Orden rank | Uso |
|-------|------------|-----|
| `normal` | 0 | Peticiones de participante; re-encolado con participante histórico |
| `low` | 1 | Relleno operador, auto-inyectado, re-encolado sin participante |

### `QueueEntrySource`

| Value | Descripción |
|-------|-------------|
| `participant` | Envío `/api/queue/submit` |
| `operator_filler` | Transferido desde reserva a cola |
| `operator_direct` | Operador encola directo sin reserva |
| `auto_inject` | Inyección automática desde reserva |
| `operator_requeue` | Re-encolado desde historial |

## Queue entry lifecycle (delta)

```text
[participant submit moderated] --> pending_review --approve--> queued --playing--> played
                              \--reject--> rejected

[participant submit free] --> queued --playing--> played

[operator requeue] --> queued (bypass pending_review)

[filler reserve] --manual/auto inject--> queued (priority=low) --playing--> played
```

`finished_at` se establece al entrar en `played` o `rejected`.

## Orden de cola activa (`queued`)

```sql
ORDER BY vote_count DESC,
         CASE priority WHEN 'low' THEN 1 ELSE 0 END ASC,
         created_at ASC
```

## Re-encolar desde historial

| Condición histórica | `priority` nueva | `source` nueva |
|---------------------|------------------|----------------|
| `submitted_by_participant_id` NOT NULL | `normal` | `operator_requeue` |
| sin participante o `source` filler/operador | `low` | `operator_requeue` |

Siempre `status = queued`; nunca `pending_review` (clarificación Q2).

## Reserva — consumo y reorden

1. **Inyección auto**: tomar fila `position = 1`, borrar de reserva, crear `queue_entry` (`priority=low`, `source=auto_inject`), `_enqueue_entry`.
2. **Manual a cola**: igual con `source=operator_filler` (uno o lote).
3. **Reorden**: `PUT reorder` renumera `position` 1..n según `ordered_ids`.

4. **Encolado directo (sin reserva)**: `POST /api/queue/operator-submit` crea `queue_entry` en `queued` con `priority=low`, `source=operator_direct`.

## Regla de duplicados (global)

Rechazar con 409 si `youtube_video_id` existe en `queue_entries` (`pending_review`, `queued`, `playing`) **o** en `filler_reserve_entries`. Aplica a submit participante, re-encolar, añadir reserva, encolado directo operador y transferencia reserva→cola.

## API DTOs (nuevos / extendidos)

### `QueueEntryRead` (extended)

| Field | Type | Notes |
|-------|------|-------|
| priority | string | `normal` \| `low` — visible en admin/kiosk state |

`source` y `finished_at` **no** en payload público de cola en vivo (solo historial admin).

### `HistoryQueueEntryRead`

Extiende `QueueEntryRead` con:

| Field | Type |
|-------|------|
| finished_at | datetime |
| submitted_by_display_name | string \| null |
| source | string |

### `HistoryListResponse`

| Field | Type |
|-------|------|
| entries | HistoryQueueEntryRead[] |
| total | int |
| page | int |
| page_size | int |

Query: `status` optional `played` \| `rejected` \| omit (ambos); `page` default 1; `page_size` default 25, max 100.

### `FillerReserveEntryRead`

| Field | Type |
|-------|------|
| id | string |
| youtube_video_id | string |
| title | string |
| thumbnail_url | string \| null |
| duration_sec | int \| null |
| position | int |
| created_at | datetime |

### `FillerReserveAddRequest`

| Field | Type | Validation |
|-------|------|------------|
| youtube_url_or_id | string | required |
| search_query | string | optional |

### `OperatorQueueSubmitRequest`

| Field | Type | Validation |
|-------|------|------------|
| youtube_url_or_id | string | required |
| search_query | string | optional |

Misma validación YouTube que envío participante. Crea entrada `queued` con `priority=low`, `source=operator_direct`.

### `FillerReserveReorderRequest`

| Field | Type |
|-------|------|
| ordered_ids | string[] | todos los IDs actuales en orden |

### `FillerAutoInjectUpdate`

| Field | Type |
|-------|------|
| filler_auto_inject_enabled | boolean |

### `EventConfigRead` (extended)

| Field | Type | Default |
|-------|------|---------|
| filler_auto_inject_enabled | boolean | true |

`EventConfigSummary` — **sin cambios** (kiosk/participante no ven toggle).

## SSE

Sin nuevo event type. Historial, reserva, re-encolado, encolado directo e inyección llaman `bump_revision` → `event: state` existente. Tests deben verificar incremento de `revision` tras mutaciones (FR-015).

## Matriz `source` (FR-017)

| Acción | `source` |
|--------|----------|
| Participante submit | `participant` |
| Re-encolar historial | `operator_requeue` |
| Reserva → cola | `operator_filler` |
| Encolado directo operador | `operator_direct` |
| Auto-inyección | `auto_inject` |

## Frontend state (admin)

| State | Source |
|-------|--------|
| `history` | `GET /api/queue/history` |
| `fillerReserve` | `GET /api/filler-reserve` |
| `fillerAutoInject` | `EventConfigRead.filler_auto_inject_enabled` |
| Cola activa | SSE `DisplayStateService` (sin cambio) |

Nuevas secciones en `/admin`: **Historial** y **Reserva de relleno** (debajo o junto a Moderación).
