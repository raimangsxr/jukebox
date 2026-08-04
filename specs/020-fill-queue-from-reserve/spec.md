# Feature Specification: Rellenar cola visible desde reserva

**Feature Branch**: `020-fill-queue-from-reserve`

**Created**: 2026-08-04

**Status**: Draft

**Input**: La cola visible no puede estar vacia si hay canciones en la reserva, si la cola está vacía, meter automáticamente la siguiente cancion de reserva.

## Clarifications

### Session 2026-08-04

- Q: Si la primera canción de la reserva es duplicado del vídeo ya activo (en cola o sonando), ¿omitir y seguir, no inyectar, o eliminar de reserva? → A: **Omitir duplicados en reserva** y continuar con la siguiente posición en orden hasta encontrar una válida o agotar la reserva.
- Q: ¿En qué momentos debe evaluarse la inyección con `playing` y cola en espera vacía? → A: **Mutaciones de cola y cambios en la reserva** (añadir, importar, reordenar) mientras haya `playing` y cero `queued`.
- Q: Al omitir un duplicado activo durante la inyección automática, ¿permanece en la reserva? → A: **Eliminar de la reserva** al omitir por duplicado activo y continuar con la siguiente posición.
- Q: ¿Debe evaluarse la inyección en lecturas pasivas de estado (GET)? → A: **Solo tras mutaciones explícitas** (cola o reserva); las lecturas de estado no disparan inyección.
- Q: Al activar el toggle «Inyección automática» con `playing`, cero `queued` y reserva disponible, ¿disparar inyección? → A: **Sí**: activar el toggle dispara evaluación e inyección inmediata si procede.

## Problem

Hoy la inyección automática de relleno (017) solo actúa cuando **no hay nada reproduciéndose** y la cola activa está vacía. En la práctica, mientras suena una canción es habitual que no queden entradas en espera (`queued`): la franja visible del kiosk y la lista de «próximas» quedan vacías aunque el operador tenga canciones en la reserva de relleno. Eso rompe la expectativa de que el evento mantenga música preparada y visible para participantes y público.

## Goals

- Garantizar que la **cola visible** (entradas en espera mostradas en kiosk y estado público) **no permanezca vacía** mientras la reserva de relleno tenga al menos una canción y la inyección automática esté activada.
- Al quedar la cola en espera vacía, **transferir automáticamente** la siguiente canción de la reserva (posición 1) a la cola activa, con las mismas reglas de prioridad baja y consumo de reserva que la inyección manual o idle actual.
- Mantener coherencia con el toggle **Inyección automática** ya existente en Admin; no introducir un segundo interruptor.

## Non-Goals

- Rellenar proactivamente la cola hasta alcanzar `queue_visible_count` cuando ya hay una o más canciones en espera (solo actuar cuando la cola en espera está **vacía**).
- Cambiar el orden de la reserva, las reglas de votación, ni la prioridad de canciones de participante frente a relleno.
- Inyectar relleno si la reserva está vacía o si la inyección automática está deshabilitada.
- Modificar importación CSV, playlists, exportación o vaciado de reserva (019).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Cola visible con canción en reproducción (Priority: P1)

Como operador con reserva de relleno cargada, quiero que al sonar una canción sin nada detrás en cola aparezca automáticamente la siguiente de la reserva en la franja visible, para que participantes y público vean qué viene después sin esperar al final del tema actual.

**Why this priority**: Es el caso principal que hoy falla: cola en espera vacía con algo sonando y reserva disponible.

**Independent Test**: Poner una canción en reproducción sin entradas `queued`, con al menos una canción en reserva e inyección automática activada → verificar que la siguiente de reserva aparece en la cola visible sin que el operador intervenga.

**Acceptance Scenarios**:

1. **Given** hay una canción `playing`, cero entradas `queued`, la reserva tiene al menos una canción e inyección automática activada, **When** ocurre una mutación de cola o de reserva que dispara evaluación (p. ej. tras avanzar, vaciar cola o añadir a reserva), **Then** la primera canción válida de la reserva pasa a `queued` con prioridad baja, se elimina de la reserva y aparece en la cola visible del kiosk.
2. **Given** el escenario anterior y la canción en reproducción sigue sonando, **When** se completa la inyección, **Then** la reproducción actual **no** se interrumpe; la nueva entrada queda en espera detrás de lo que suena.
3. **Given** inyección automática desactivada, **When** hay `playing`, cero `queued` y reserva con canciones, **Then** no se inyecta relleno y la cola visible permanece vacía hasta acción manual del operador.
4. **Given** reserva vacía, **When** hay `playing` y cero `queued`, **Then** no se produce inyección ni error; la cola visible puede permanecer vacía.

---

### User Story 2 — Hueco total sin reproducción (Priority: P1)

Como operador, quiero que el comportamiento existente de inyección en hueco total (sin `playing` ni `queued`) se mantenga, para no perder el relleno automático al terminar el último tema.

**Why this priority**: Regresión crítica; la feature extiende el alcance, no lo sustituye.

**Independent Test**: Vaciar cola activa con reserva poblada e inyección activada → avanzar o quedar idle → verificar inyección y auto-arranque según reglas actuales (014).

**Acceptance Scenarios**:

1. **Given** no hay `playing` ni `queued`, reserva con canciones e inyección activada, **When** el sistema necesita siguiente tema, **Then** se inyecta la primera de la reserva y, si aplica, comienza reproducción automáticamente como hoy.
2. **Given** tras inyectar en hueco total, **When** la canción pasa a `playing`, **Then** el ítem ya no figura en la reserva (consumo) y la cola visible refleja el nuevo estado.

---

### User Story 3 — Participantes ven próximas canciones (Priority: P2)

Como participante en `/participar`, quiero ver al menos una canción en la lista de próximas cuando el operador tiene reserva de relleno, para poder votar o anticipar el ambiente aunque nadie haya pedido música recientemente.

**Why this priority**: Valor de audiencia; depende de la inyección automática ampliada (US1).

**Independent Test**: Con cola en espera vacía, reserva con relleno e inyección activa → abrir `/participar` → comprobar que la lista de cola muestra la canción inyectada con las mismas reglas de votación que cualquier otra entrada de relleno.

**Acceptance Scenarios**:

1. **Given** se inyectó relleno con cola en espera vacía, **When** un participante consulta su vista de cola, **Then** ve la canción inyectada entre las entradas `queued` ordenadas por votos y reglas vigentes.
2. **Given** una canción inyectada en cola, **When** un participante vota por ella, **Then** el orden puede cambiar según votos; no hay distinción visual especial frente a otro relleno en cola (coherente con 017).

---

### Edge Cases

- La reserva tiene canciones pero la posición 1 (o siguientes) coincide con un vídeo ya activo (`pending_review`, `queued` o `playing`) → **eliminar** ese ítem de la reserva al omitirlo por duplicado y evaluar la siguiente posición en orden; repetir hasta encolar una válida o agotar candidatos. Si ninguna es válida, la cola en espera puede permanecer vacía sin error.
- La cola en espera alcanza el límite máximo del sistema → no aplica inyección por vacío (solo se dispara con cero `queued`).
- Varias transiciones seguidas que dejan `queued` en cero → cada evaluación inyecta como máximo la siguiente canción de reserva (una por ciclo), respetando orden de posición en reserva.
- El operador vacía la reserva mientras una canción inyectada está en `queued` → la entrada en cola permanece; solo deja de haber nuevas inyecciones automáticas.
- Cambio de toggle de inyección automática de activado a desactivado con cola en espera vacía y reserva poblada → no nuevas inyecciones hasta reactivar o encolar manualmente.
- El operador **activa** inyección automática con `playing`, cero `queued` y reserva con canciones → evaluar e inyectar de inmediato si procede (sin esperar otra mutación).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE considerar la cola en espera (`queued`) **vacía** cuando su recuento es cero, independientemente de si hay una entrada `playing`.
- **FR-002**: Cuando la cola en espera está vacía, la reserva tiene al menos una canción válida y la inyección automática está habilitada, el sistema DEBE transferir automáticamente la **primera candidata válida en orden de reserva** a la cola activa como entrada `queued` de prioridad baja (omitiendo duplicados activos según FR-007).
- **FR-003**: Cada transferencia automática DEBE **consumir** el ítem de la reserva (eliminarlo de la reserva y renumerar posiciones), con origen identificable como inyección automática, coherente con 017.
- **FR-004**: La inyección automática por cola vacía NO DEBE interrumpir la reproducción actual: si hay `playing`, la nueva entrada queda en espera.
- **FR-005**: El comportamiento existente de inyección cuando no hay `playing` ni `queued` DEBE conservarse sin regresión (incluido auto-arranque cuando corresponda).
- **FR-006**: Si la inyección automática está deshabilitada, el sistema NO DEBE inyectar aunque la cola en espera esté vacía y la reserva tenga canciones.
- **FR-007**: Las reglas de duplicado de vídeo en cola activa DEBEN aplicarse a la inyección automática: no encolar un vídeo que ya esté en estados activos (`pending_review`, `queued`, `playing`). Si la candidata en posición N de la reserva es duplicado, el sistema DEBE **eliminarla de la reserva** y evaluar la posición siguiente hasta encontrar una válida o agotar la reserva.
- **FR-008**: Tras una evaluación de inyección que modifique reserva o cola (inyección exitosa u omisión de duplicados que eliminen filas de reserva), el estado publicado (kiosk, participantes, operador vía actualizaciones en vivo) DEBE reflejar reserva y cola actualizadas en un único `bump_revision` coherente.
- **FR-009**: El sistema DEBE evaluar la necesidad de inyección tras **mutaciones explícitas de cola** que dejen cero `queued` con `playing` activo (p. ej. `skip_or_advance` o auto-arranque que promueve la última entrada en espera a `playing`), tras **cambios en la reserva** que no añadan a cola (añadir, importar, reordenar), y al **activar** el toggle de inyección automática, además de los puntos idle existentes (sin `playing` ni `queued`). No existe API de eliminación de entradas `queued`; `reject_entry` solo afecta `pending_review` y no dispara esta evaluación. El encolado manual desde reserva (`transfer_to_queue`) añade a `queued` y no requiere inyección. Las **lecturas pasivas de estado** NO DEBEN disparar inyección.

### Key Entities

- **Cola en espera (`queued`)**: Entradas visibles en la franja del kiosk y listadas como «próximas»; su recuento determina si la cola visible está vacía.
- **Reserva de relleno**: Lista ordenada del operador; la posición 1 es la siguiente candidata a inyección automática.
- **Inyección automática (configuración de evento)**: Interruptor operador existente que habilita o deshabilita todo relleno automático desde reserva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 100% de escenarios de prueba con `playing`, cero `queued`, reserva no vacía e inyección activada, la cola visible muestra al menos una entrada en espera en menos de 3 segundos desde la transición que dejó la cola vacía (validación funcional en quickstart T016; sin aserción de tiempo automatizada).
- **SC-002**: En escenarios de regresión (hueco total sin `playing` ni `queued`), el comportamiento idle de inyección + auto-arranque se mantiene equivalente a 017/014 (validado por tests de regresión T012 y suite existente; sin benchmark de latencia automatizado).
- **SC-003**: Cero regresiones en pruebas existentes de inyección idle, toggle de inyección automática y consumo de reserva.
- **SC-004**: Operadores reportan que la franja de «próximas canciones» deja de quedarse vacía durante reproducción cuando tienen reserva cargada (validación manual en ensayo de evento).

## Assumptions

- «Cola visible vacía» se interpreta como **cero entradas en espera** (`queued`), no como ausencia de `now_playing`. La franja del kiosk muestra `queued`; la canción actual suena aparte.
- Solo se inyecta **una** canción por evaluación cuando la cola en espera está vacía; no se rellena hasta `queue_visible_count` en esta versión.
- Se reutiliza el toggle **Inyección automática** (`filler_auto_inject_enabled`) sin nuevo control en Admin.
- Orden de reserva, prioridad baja, votabilidad del relleno en cola y auto-arranque en idle siguen las reglas ya definidas en 017 y 014.
- Los puntos de disparo son **solo mutaciones explícitas**: `skip_or_advance` / auto-arranque que deje `playing` + cero `queued`, cambios en reserva que no encolen (`add_to_reserve`, import, reordenar), y activación del toggle de inyección automática. No aplican: `GET` de estado, `reject_entry` (`pending_review` solo), ni `transfer_to_queue` manual.
