# Research: 017-admin-queue-history-filler

## R1 — Modelo de reserva vs extensión de `queue_entries`

**Decision**: Tabla dedicada `filler_reserve_entries` separada de `queue_entries`.

**Rationale**: La reserva no consume cupo de cola activa (FR-006), admite reordenación independiente (clarificación Q5) y consumo al transferir (clarificación Q3). Mezclar estados `reserved` en `queue_entries` complicaría duplicados, límites y consultas de kiosk.

**Alternatives considered**:
- Estado `reserved` en `queue_entries` — rechazado: mezcla ciclo de vida y filtros públicos.
- Solo encolado directo sin reserva — rechazado en clarificación (Opción C).

---

## R2 — Prioridad y orden de cola

**Decision**: Columna `queue_entries.priority` enum `normal` | `low` (default `normal`). Orden SQL: `vote_count DESC`, `priority ASC` con mapeo `normal=0`, `low=1`, `created_at ASC`.

**Rationale**: Alineado con FR-008 y clarificación Q4 (votos primero; desempate prioridad; antigüedad). Un entero explícito evita ambigüedad lexicográfica de strings.

**Alternatives considered**:
- Flag booleano `is_filler` — equivalente pero menos extensible.
- Cola separada — rechazado en spec (una sola cola).

---

## R3 — Historial y timestamp de finalización

**Decision**: Columna `queue_entries.finished_at` (nullable). Se rellena al pasar a `played` o `rejected`. Historial = `status IN (played, rejected)` ordenado por `finished_at DESC`.

**Rationale**: FR-001 exige orden por fecha de finalización; `created_at` no refleja cuándo terminó. Backfill en migración: `finished_at = COALESCE(approved_at, created_at)` para filas terminales existentes.

**Alternatives considered**:
- Tabla de historial aparte — rechazado: duplica metadatos y rompe re-encolado desde la misma entidad.

---

## R4 — Origen / auditoría de entrada

**Decision**: Columna `queue_entries.source` enum: `participant`, `operator_filler`, `operator_requeue`, `auto_inject`, `operator_direct`. Default `participant` para envíos existentes.

**Rationale**: FR-017. Determina prioridad al re-encolar (FR-005): `participant` o re-encolado de entrada con `submitted_by_participant_id` → `normal`; resto → `low`.

**Alternatives considered**:
- Inferir solo por `submitted_by_participant_id` — insuficiente para re-encolados y relleno operador.

---

## R5 — Inyección automática de relleno

**Decision**: Tras `skip_or_advance` cuando no queda `playing` ni `queued`, y en `_maybe_auto_start_playback` cuando la cola sigue vacía, invocar `_try_inject_filler(db)` si `event_config.filler_auto_inject_enabled` y hay ítems en reserva.

**Rationale**: Cubre fin de canción, arranque idle y auto-start post-enqueue sin duplicar lógica. Respeta toggle FR-010.

**Alternatives considered**:
- Job en background — innecesario en single-replica.
- Inyectar con cola no vacía — prohibido por non-goals.

---

## R6 — Búsqueda YouTube para operador

**Decision**: Permitir `GET /api/youtube/search` con sesión de **operador** además de participante; operador **no** consume rate limit de participante.

**Rationale**: Spec asume misma experiencia URL/búsqueda que participación (Assumptions). Hoy el endpoint exige `CurrentParticipant`.

**Alternatives considered**:
- Solo URL en admin — peor UX, no cumple spec.
- Endpoint duplicado `/api/queue/filler-search` — duplicación innecesaria.

---

## R7 — API surface y prefijos

**Decision**:
- `POST /api/queue/history/{id}/requeue`
- `POST /api/queue/operator-submit`
- Reserva bajo `/api/filler-reserve/*`
- Toggle auto-inyect en `PUT /api/event-config/filler-auto-inject`

**Rationale**: Historial es extensión natural de cola; reserva es recurso distinto. Sigue convención `/api/*` y patrones de `event_config` para toggles de evento.

**Alternatives considered**:
- Todo bajo `/api/queue/*` — mezcla recursos con ciclos de vida distintos.

---

## R8 — Reordenación de reserva

**Decision**: `PUT /api/filler-reserve/reorder` con body `{ "ordered_ids": string[] }` — lista completa de IDs en orden deseado; servidor reasigna `position` 1..n.

**Rationale**: Clarificación Q5; patrón simple y testeable; evita drag per-item N requests.

**Alternatives considered**:
- Swap adyacente — más round-trips en UI móvil.

---

## R9 — Duplicados vídeo

**Decision**: Al añadir a reserva o re-encolar, rechazar si `youtube_video_id` existe en: `pending_review`, `queued`, `playing`, o `filler_reserve_entries`.

**Rationale**: Edge case spec + regla actual de duplicados activos extendida a reserva.

**Alternatives considered**:
- Permitir duplicado en reserva si no está en cola — rechazado por edge case explícito.
