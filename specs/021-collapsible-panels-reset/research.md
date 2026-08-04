# Research: 021-collapsible-panels-reset

**Date**: 2026-08-04

## R1 — Componente de panel plegable (frontend)

**Decision**: Crear `CollapsibleSectionComponent` standalone reutilizable (`frontend/src/app/components/collapsible-section/`) con cabecera `<button type="button">`, `aria-expanded`, `aria-controls`, indicador visual (chevron) y proyección de contenido (`ng-content`). Estado `expanded` controlado por el padre (one-way + toggle en click).

**Rationale**: No hay acordeón en el proyecto; CDK no está en dependencias. `<details>` nativo dificulta badges dinámicos (pendientes, total historial) y estilos consistentes con Tailwind/jukebox-surface. Componente compartido entre Admin y Participar evita duplicar lógica ARIA.

**Alternatives considered**:
- `<details>/<summary>` — rechazado: menos control de estado por defecto y badges en summary.
- Tres implementaciones inline en cada vista — rechazado: duplica accesibilidad y estilos.
- Pestañas o nav lateral — rechazado en spec (non-goals).

## R2 — Estado expandido/plegado (sesión)

**Decision**: Estado en memoria del componente padre (`admin.component.ts`, `participate.component.ts`) como `Record<string, boolean>` o campos nombrados; **sin** `localStorage` ni API. Valores por defecto según spec/clarificaciones.

**Rationale**: Alineado con FR-003 y assumption de no persistencia entre recargas.

**Alternatives considered**:
- `sessionStorage` — rechazado en spec.
- Query params — rechazado: ruido en URL sin valor.

## R3 — API vaciar historial

**Decision**: `DELETE /api/queue/history` (operator session) → **204 No Content**; elimina todas las filas `queue_entries` con `status IN ('played', 'rejected')`; `bump_revision` + SSE `state` (mismo patrón que `DELETE /api/filler-reserve`).

**Rationale**: Simetría con `clear_reserve`; operación idempotente (0 filas → 204); participantes reciben SSE y `ParticipantStateService` ya llama `refreshSubmissions()` en evento `state`.

**Alternatives considered**:
- `POST /api/queue/history/clear` — válido pero inconsistente con reserva.
- Soft-delete / flag `archived` — rechazado: spec exige eliminación permanente.
- Filtrar por query `status` en DELETE — rechazado en clarificación (siempre borra todo el historial).

## R4 — Confirmación vaciar historial (UI)

**Decision**: Modal de confirmación en Admin (mismo patrón que re-encolar y cambio de modo de cola), **no** `window.confirm` como en vaciar reserva.

**Rationale**: Clarificación Q5 pide patrón de otras acciones destructivas del Admin con diálogo Cancelar/Confirmar; re-encolar ya usa modal en `admin.component.html`.

**Alternatives considered**:
- `confirm()` nativo — usado en reserva pero no cumple clarificación para historial.
- Escribir palabra clave — rechazado en clarificación.

## R5 — Contadores en cabeceras Admin

**Decision**: Moderación → `pending().length` (signal existente); Historial → `historyTotal` del último `GET /api/queue/history` (sin filtro de estado para el badge, o `total` de listado sin `status` param). Actualizar `historyTotal` tras vaciar a 0.

**Rationale**: Clarificación Q3; datos ya disponibles sin nuevo endpoint.

**Alternatives considered**:
- Endpoint `GET /api/queue/history/count` — innecesario; `total` en paginación basta.
- Contadores en todas las secciones — rechazado en clarificación.

## R6 — Reorden participación + «Sonando ahora»

**Decision**: Reestructurar `participate.component.html`: (1) franja fija `@if (state?.now_playing)` fuera de paneles; (2) panel votos; (3) panel enviar (búsqueda + URL + botón Enviar); (4) panel mis canciones. Mover `submit-footer` dentro del panel enviar.

**Rationale**: FR-005, FR-007 y clarificación «Sonando ahora» entre cabecera y votos.

**Alternatives considered**:
- «Sonando ahora» dentro del panel votos — rechazado en clarificación Q2.

## R7 — Propagación SSE tras vaciar historial

**Decision**: Reutilizar `bump_revision` existente; no nuevo tipo de evento SSE. Admin escucha `state` vía `DisplayStateService` / refresh hooks existentes y recarga historial; participante refresca submissions en handler `state` (ya implementado).

**Rationale**: Mínimo cambio; cumple FR-014 y edge case multi-pestaña.

**Alternatives considered**:
- Evento SSE dedicado `history.cleared` — over-engineering.
- Solo refresh manual — incumple FR-014.

## R8 — FK y votos al borrar historial

**Decision**: `DELETE` masivo de `queue_entries` terminales; votos asociados se eliminan por `ON DELETE CASCADE` en `votes.queue_entry_id`.

**Rationale**: Modelo existente; entradas terminales no son votables; sin migración.

**Alternatives considered**:
- Borrado lógico — rechazado en spec.
