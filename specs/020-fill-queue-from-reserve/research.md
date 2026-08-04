# Research: 020-fill-queue-from-reserve

**Date**: 2026-08-04

## R1 — Extender inyección automática sin romper idle

**Decision**: Refactor `inject_next_if_idle` → `maybe_inject_from_reserve(db) -> QueueEntry | None` que solo exige `_count_queued == 0` y `filler_auto_inject_enabled`; **eliminar** el early-return por `get_now_playing() is not None`. Mantener auto-arranque en `_maybe_auto_start_playback` / `skip_or_advance` solo cuando no hay `playing`.

**Rationale**: El guard de `playing` en la implementación actual (017) es la causa raíz del bug. La spec clarifica que inyección con `playing` activo debe añadir a `queued` sin interrumpir reproducción (FR-004).

**Alternatives considered**:
- Función separada `inject_next_if_queued_empty` — rechazada: duplica lógica de consumo de reserva y duplicados.
- Inyección en `build_state_response` — rechazada en clarificación (lecturas pasivas no disparan).

## R2 — Omisión de duplicados activos en auto-inyección

**Decision**: Bucle en `maybe_inject_from_reserve`: iterar reserva por `position` ascendente; si `_has_active_duplicate(db, video_id)` → `db.delete(reserve_entry)`, `_renumber_reserve_positions`, continuar; si candidata válida → transferir con `source=auto_inject` y salir (máx. 1 inyección por llamada). Un solo `bump_revision` al final si reserva o cola cambiaron (FR-008).

**Rationale**: Alineado con clarificación Q1/Q3: omitir y **eliminar** duplicados de reserva para evitar bucles en evaluaciones sucesivas.

**Alternatives considered**:
- Saltar sin eliminar — rechazado: reevaluaría el mismo duplicado en cada mutación.
- Mover al final de reserva — rechazado en clarificación.

## R3 — Puntos de disparo (event-driven)

**Decision**: Invocar `maybe_inject_from_reserve` al final de mutaciones que puedan dejar `queued == 0`:

| Área | Función / ruta | Cuándo |
|------|----------------|--------|
| Cola | `skip_or_advance` | Tras promover siguiente a `playing` si `queued` sigue en 0 |
| Cola | `_maybe_auto_start_playback` | Tras promover a `playing` si `queued` sigue en 0 |
| Reserva | `append_reserve_entries`, `add_to_reserve`, `reorder_reserve`, import/playlist commit | Tras commit si `playing` y 0 `queued` (not `transfer_to_queue`) |
| Config | `PUT /api/event-config/filler-auto-inject` | Solo cuando `enabled` pasa `false → true` |

**Rationale**: Clarificación Q2/Q4/Q5. Centralizar en un helper evita olvidar rutas.

**Alternatives considered**:
- Middleware post-request — rechazado: demasiado amplio y podría ejecutarse en GET.
- Solo `skip_or_advance` — insuficiente (no cubre añadir a reserva ni toggle).

## R4 — Frontend

**Decision**: Sin cambios de UI. Kiosk y `/participar` reciben la cola inyectada vía SSE `state` existente.

**Rationale**: Comportamiento puramente de backend; contratos de estado sin cambio de schema.

## R5 — Contratos y migración

**Decision**: Actualizar sección **Auto-inject** en `backend-api` contract; sin migración Alembic; `app-core` nota de comportamiento en kiosk (franja deja de vaciarse).

**Rationale**: Sin nuevas tablas ni campos; solo semántica de inyección ampliada.
