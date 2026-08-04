# Quickstart: 021-collapsible-panels-reset

Validation after implementation.

## Prerequisites

- Branch `021-collapsible-panels-reset`
- Operator session on `/admin`
- Participant session on `/participar` (dev or Google)
- Historial con al menos 1 reproducida y 1 rechazada
- Participante con esas canciones visibles en «Mis canciones»

## Phase 1 — Admin paneles plegables (US1)

1. Abrir `/admin`
2. **Expected**: Solo **Moderación** expandida; resto plegado
3. Cabecera Moderación muestra contador de pendientes; Historial muestra **total global** (plegado), igual con filtro «Reproducidas» activo en el listado
4. Expandir Historial → contenido visible; plegar Moderación → pendientes siguen en badge
5. Recargar página → Moderación expandida de nuevo; otras plegadas

## Phase 2 — Participación reordenada (US2)

1. Abrir `/participar` autenticado (post-normas)
2. **Expected** orden: Sonando ahora (si hay) → Cola votable (expandida) → Enviar canciones (plegado) → Mis canciones (plegado)
3. Primer voto sin scroll > 1 pantalla desde arriba
4. Expandir «Enviar canciones» → búsqueda, URL y botón enviar visibles juntos

## Phase 2b — Participación móvil + teclado (edge case)

1. En viewport móvil (~390px), expandir «Enviar canciones» y enfocar campo de búsqueda (teclado virtual abierto)
2. **Expected**: Botón «Enviar canción» sigue visible/accesible en el panel de envío; plegar «Mis canciones» no lo oculta

## Phase 3 — Vaciar historial (US3)

1. En Admin → Historial → «Vaciar historial»
2. **Expected**: Modal advertencia; Cancelar → sin cambios
3. Confirmar → historial vacío; badge «0 entradas»; botón deshabilitado
4. Cola activa y pendientes de moderación intactos
5. En `/participar`, «Mis canciones» ya no lista reproducidas/rechazadas eliminadas (SSE o refresh)

## Phase 4 — Filtro historial + vaciar (FR-011)

1. Con historial mixto, filtrar solo «Reproducidas»
2. Vaciar historial
3. **Expected**: También desaparecen rechazadas del total

## Phase 5 — Accesibilidad (smoke)

1. Tab hasta cabecera de panel → Enter expande/colapsa
2. `aria-expanded` refleja estado en inspección DOM
3. Chevron rota al expandir/colapsar

## Phase 6 — Multi-pestaña Admin (edge case)

1. Abrir dos pestañas `/admin` con historial poblado
2. En pestaña A, vaciar historial
3. **Expected**: Pestaña B actualiza badge y listado tras evento SSE (sin recargar manualmente)

## Automated

```bash
pytest backend/tests/test_queue_history.py -k clear
npm --prefix frontend run build
npm --prefix frontend test -- --include='**/collapsible-section*' --include='**/participate.component.spec.ts'
```

Required `test_clear_history` cases: operator 204, participant 401, active queue untouched, terminal rows deleted, idempotent second call, **with UI filter active deletes all terminal rows**.
