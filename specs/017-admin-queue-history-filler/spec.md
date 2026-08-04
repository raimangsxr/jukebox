# Feature Specification: Historial de cola y canciones de relleno en Admin

**Feature Branch**: `017-admin-queue-history-filler`

**Created**: 2026-08-04

**Status**: Draft

**Input**: Añadir en Admin la visualización de canciones ya reproducidas o denegadas para que el operador pueda re-encolarlas. Permitir pre-cargar canciones de relleno con baja prioridad que suplan huecos de participación. Todas las canciones comparten la misma cola; ante empate en el orden, las canciones normales (de usuario) deben reproducirse antes que las de relleno.

## Clarifications

### Session 2026-08-04

- Q: ¿Qué enfoque de canciones de relleno adoptamos (A manual, B reserva, C híbrido, D híbrido en fases)? → A: **Opción C — Híbrido**: reserva separada, inyección automática en huecos vacíos y encolado manual desde reserva o directo a cola.
- Q: ¿Re-encolar desde historial respeta el modo Moderado (`pending_review`) o va directo a cola? → A: **Directo a cola** (`queued`): re-encolar siempre salta moderación, independientemente del modo Moderado/Libre.
- Q: ¿Al transferir una canción de la reserva a la cola activa, permanece en la reserva? → A: **Consumir**: al pasar a cola (inyección automática o manual), el ítem se elimina de la reserva.
- Q: ¿Los participantes pueden votar canciones de relleno en cola activa? → A: **Sí, votables**: mismas reglas de votación y orden (votos → prioridad → antigüedad).
- Q: ¿El operador puede reordenar manualmente la reserva de relleno? → A: **Sí, reordenable**: el operador define el orden; la inyección automática respeta ese orden (no solo FIFO por fecha de alta).

## Problem

Durante un evento en vivo el operador no puede recuperar canciones que ya sonaron o fueron rechazadas sin volver a buscarlas manualmente. Cuando los participantes dejan de pedir música, el jukebox puede quedarse en silencio aunque el operador tenga una lista mental de temas de ambiente. Hoy la cola solo expone entradas activas (`pending_review`, `queued`, `playing`); no hay historial operativo ni mecanismo de relleno con prioridad inferior a las peticiones de usuarios.

## Goals

- Panel en Admin con historial de canciones **reproducidas** y **rechazadas**, con acción de **re-encolar**.
- Gestión de **canciones de relleno** (baja prioridad) para mantener música cuando falta participación.
- **Una sola cola** de reproducción; el orden respeta votos y antigüedad, y en empate gana la canción de usuario frente a la de relleno.
- Las canciones de relleno **no sustituyen** peticiones activas de participantes; solo llenan huecos.

## Non-Goals

- Historial visible para participantes en `/participar` (solo operador en Admin).
- Reproducir automáticamente canciones de relleno mientras haya canciones de usuario en cola con votos pendientes.
- Editar votos históricos o restaurar el estado exacto de una entrada terminada (re-encolar crea una **nueva** entrada).
- Importación masiva desde archivos externos (CSV, playlists de Spotify, etc.) en esta versión.
- Cambiar el modo de cola Moderado/Libre ni las reglas de moderación de envíos de participantes.

## Diseño acordado — canciones de relleno

**Decisión confirmada: Opción C — Híbrido** (reserva + inyección automática + encolado manual). Las alternativas A (solo lote manual) y B (solo reserva sin auto-inyección) quedan descartadas para esta feature.

**Comportamiento acordado:**

1. **Reserva de relleno**: lista persistente durante el evento con canciones añadidas por URL/búsqueda (misma experiencia de descubrimiento que en participación, pero solo operador).
2. **Inyección automática**: cuando no hay entrada `playing` y la cola `queued` está vacía, el sistema toma la **primera canción según el orden definido en la reserva** (posición 1), la **elimina de la reserva** y la encola como `queued` con prioridad baja.
3. **Encolado manual**: el operador puede mover una o varias canciones de la reserva a la cola activa en cualquier momento (cada transferencia **consume** el ítem de la reserva), o añadir directamente a la cola sin pasar por reserva.
4. **Re-encolar desde historial**: siempre crea entrada nueva en cola con **prioridad normal** si la canción original fue pedida por un participante; con **prioridad baja** si fue solo de relleno u operador.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Consultar historial y re-encolar (Priority: P1)

Como operador en Admin, quiero ver las canciones ya reproducidas y las rechazadas con su motivo, para decidir si vuelvo a poner alguna en la cola sin buscarla de nuevo.

**Why this priority**: Recuperar temas del evento es la necesidad más directa y aporta valor aunque no exista relleno automático.

**Independent Test**: Completar o rechazar varias canciones → abrir historial en Admin → re-encolar una → verificar que aparece en la cola activa respetando reglas de duplicado y prioridad.

**Acceptance Scenarios**:

1. **Given** hay entradas en estado reproducido o rechazado, **When** abro la sección de historial en Admin, **Then** veo lista paginada con título, miniatura, estado, fecha y (si aplica) motivo de rechazo y nombre del participante.
2. **Given** una canción reproducida que no está duplicada en cola activa, **When** pulso «Re-encolar», **Then** se crea una nueva entrada en cola y recibo confirmación visual; la cola y el kiosk se actualizan en vivo.
3. **Given** una canción rechazada, **When** la re-encolo, **Then** entra en cola con prioridad normal si tenía participante asociado; con prioridad baja si era de relleno u operador.
4. **Given** el evento está en modo Moderado, **When** re-encolo una canción del historial (reproducida o rechazada), **Then** la nueva entrada va directo a `queued` sin pasar por `pending_review`.
5. **Given** el mismo vídeo ya está en cola activa o pendiente de revisión, **When** intento re-encolar, **Then** el sistema impide la acción y muestra mensaje claro (misma regla que envíos duplicados actuales).
6. **Given** el historial tiene muchas entradas, **When** navego o filtro por estado (reproducida / rechazada), **Then** puedo localizar canciones sin degradar la experiencia (paginación o carga incremental).

---

### User Story 2 — Gestionar reserva de canciones de relleno (Priority: P1)

Como operador, quiero añadir y quitar canciones en una reserva de relleno de baja prioridad, para tener música preparada cuando baje la participación.

**Why this priority**: Sin reserva no hay relleno automático ni control proactivo del ambiente musical.

**Independent Test**: Añadir 3 canciones a la reserva → verificar que no aparecen en la cola visible del kiosk hasta inyectarse → quitar una de la reserva → verificar que ya no puede inyectarse.

**Acceptance Scenarios**:

1. **Given** estoy autenticado como operador, **When** añado una canción por URL o búsqueda a la reserva de relleno, **Then** aparece en la lista de reserva con indicador de baja prioridad y **no** cuenta para el límite de cola activa hasta inyectarse.
2. **Given** hay canciones en la reserva, **When** elimino una, **Then** desaparece de la reserva y no se inyectará automáticamente en el futuro.
3. **Given** hay varias canciones en la reserva, **When** reordeno manualmente la lista, **Then** el nuevo orden se guarda y la próxima inyección automática tomará la canción en la primera posición.
4. **Given** selecciono varias canciones en la reserva, **When** uso «Añadir a cola ahora», **Then** entran en la cola activa marcadas como baja prioridad, se eliminan de la reserva y se respeta el límite máximo de cola.
5. **Given** la reserva está vacía y la cola activa también, **When** termina la última canción en reproducción, **Then** el sistema no bloquea el avance; simplemente no hay siguiente tema (sin error para el operador).

---

### User Story 3 — Inyección automática de relleno en huecos (Priority: P2)

Como operador, quiero que el jukebox saque automáticamente una canción de la reserva cuando no quede nada por reproducir, para que no haya silencios largos entre rondas de participación.

**Why this priority**: Es el comportamiento que cumple el objetivo de «suplir huecos», pero depende de tener reserva (US2).

**Independent Test**: Vaciar cola activa con reserva poblada → avanzar reproducción → verificar que la siguiente entrada proviene de la reserva con prioridad baja.

**Acceptance Scenarios**:

1. **Given** no hay nada `playing` ni entradas `queued` y la reserva tiene al menos una canción, **When** el sistema necesita siguiente tema (p. ej. tras terminar la anterior o al arrancar evento idle), **Then** la primera canción de la reserva se elimina de la reserva, pasa a la cola activa como `queued` con baja prioridad y comienza reproducción según reglas actuales de auto-arranque.
2. **Given** la reserva tiene un orden definido por el operador, **When** se inyectan varias canciones en distintos huecos, **Then** el orden de la reserva se respeta en cada inyección sucesiva.
3. **Given** entra una nueva petición de participante mientras suena relleno, **When** ambas comparten el mismo criterio de orden (mismos votos), **Then** la canción de participante queda por delante de la de relleno.
4. **Given** la inyección automática está deshabilitada por configuración de evento (toggle operador), **When** la cola queda vacía, **Then** no se inyecta relleno hasta que el operador lo active de nuevo o encole manualmente.

---

### User Story 4 — Orden de cola con prioridad en empates (Priority: P1)

Como participante y operador, quiero que las canciones pedidas por usuarios suenen antes que las de relleno cuando compiten en la misma posición lógica, para que la audiencia tenga prioridad sobre el ambiente.

**Why this priority**: Regla de negocio central que afecta a toda la cola; sin ella el relleno podría eclipsar a los usuarios.

**Independent Test**: Encolar una canción de relleno y una de usuario con los mismos votos y timestamp cercano → verificar orden en kiosk y admin.

**Acceptance Scenarios**:

1. **Given** dos canciones con el mismo número de votos, **When** se ordena la cola, **Then** la de participante (prioridad normal) aparece antes que la de relleno (baja prioridad).
2. **Given** una canción de relleno tiene más votos que una de usuario, **When** se ordena la cola, **Then** gana la de más votos (los votos siguen siendo el criterio principal).
3. **Given** dos canciones del mismo tipo y mismos votos, **When** se ordena la cola, **Then** gana la más antigua (`created_at` ascendente), coherente con el comportamiento actual.
4. **Given** un participante vota una canción de relleno en cola activa, **When** aumentan sus votos, **Then** puede adelantar a otras según votos, pero el desempate por tipo sigue aplicando solo en empate de votos.

---

### Edge Cases

- ¿Qué ocurre si re-encolo una canción reproducida hace horas y el participante original ya no está en sesión? → Se crea entrada nueva; se conserva metadatos (título, vídeo); la atribución al participante es informativa en historial pero la nueva entrada se trata como re-encolado por operador con prioridad normal por haber sido petición original de usuario.
- ¿Qué pasa si la reserva y la cola activa suman el límite máximo? → Solo las entradas `queued` activas cuentan para el límite; la reserva tiene su propio tope configurable (p. ej. 50 ítems) para evitar abusos.
- ¿Puede el operador re-encolar una canción rechazada por moderación a `pending_review`? → No; re-encolar va **siempre** directo a `queued`, incluso en modo Moderado. El operador tiene autoridad explícita al re-encolar.
- ¿Qué ocurre si se inyecta relleno y acto seguido un participante envía canción? → La del participante entra en cola; si empatan en votos, la del participante va primero.
- ¿Historial tras reinicio del servicio? → Las entradas terminadas persisten en base de datos; el historial sobrevive al reinicio del mismo evento.
- ¿Canción de relleno duplicada en reserva? → No permitir el mismo `youtube_video_id` dos veces en reserva ni en cola activa simultáneamente.
- ¿Qué pasa si la reserva se agota tras consumir todos los ítems? → No hay auto-inyección hasta que el operador añada más canciones a la reserva o encole manualmente; no hay bucle automático.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE exponer en Admin un listado del historial de entradas en estado **reproducido** y **rechazado**, ordenado por fecha de finalización descendente (rechazo o fin de reproducción).
- **FR-002**: Cada ítem del historial DEBE mostrar al menos: título, miniatura, identificador de vídeo, estado, fecha/hora, motivo de rechazo (si aplica), nombre del participante (si existía) y **origen** (`source`: participante, relleno, re-encolado, etc.) para auditoría operativa.
- **FR-003**: El operador DEBE poder **re-encolar** una entrada del historial con un solo paso de confirmación, creando una **nueva** entrada en estado `queued` (sin pasar por `pending_review`, independientemente del modo Moderado/Libre).
- **FR-004**: Al re-encolar, añadir a reserva o encolar directamente, el sistema DEBE aplicar la regla de duplicados vigente: no permitir el mismo `youtube_video_id` en `pending_review`, `queued`, `playing` **ni** en `filler_reserve_entries`.
- **FR-005**: Al re-encolar, el sistema DEBE asignar **prioridad normal** si la entrada histórica tenía participante asociado; **prioridad baja** si fue añadida solo por operador como relleno.
- **FR-006**: El sistema DEBE mantener una **reserva de relleno** separada de la cola activa, gestionable solo por operador (alta, baja, listado y **reordenación manual**).
- **FR-007**: Las entradas de relleno DEBEN estar marcadas con **prioridad baja** al pasar a la cola activa (manual o automática).
- **FR-008**: El orden de la cola activa DEBE ser: (1) `vote_count` descendente; (2) prioridad (normal antes que baja); (3) `created_at` ascendente.
- **FR-009**: Cuando no haya entrada sonando ni cola activa y la inyección automática esté habilitada, el sistema DEBE tomar la canción en la **primera posición del orden de reserva** definido por el operador, **eliminarla de la reserva** y encolarla con prioridad baja.
- **FR-010**: El operador DEBE poder desactivar la inyección automática de relleno sin vaciar la reserva.
- **FR-011**: El operador DEBE poder añadir canciones a la reserva o directamente a la cola mediante URL o búsqueda de vídeo (misma validación de vídeo que envíos existentes).
- **FR-012**: El operador DEBE poder mover una o varias canciones de la reserva a la cola activa manualmente; cada transferencia DEBE **consumir** (eliminar) el ítem de la reserva.
- **FR-013**: Las canciones de relleno en cola activa DEBEN ser **votables** por participantes con las mismas reglas que el resto de entradas `queued` (incremento de `vote_count`, reordenación y límites de voto vigentes).
- **FR-014**: Los participantes NO DEBEN ver la reserva de relleno ni el historial operativo; solo la cola pública habitual.
- **FR-015**: Los cambios en historial, reserva y re-encolado DEBEN reflejarse en kiosk y admin mediante actualización en vivo (mismo mecanismo de tiempo real del evento).
- **FR-016**: El historial DEBE soportar paginación (tamaño de página por defecto 25, máximo 100 por petición).
- **FR-017**: El sistema DEBE registrar en la nueva entrada si proviene de re-encolado, inyección automática, reserva manual o envío de participante, para auditoría operativa.

### Key Entities

- **Entrada de cola (histórica o activa)**: Representa una canción en el ciclo de vida del jukebox. Atributos relevantes: vídeo, metadatos, estado, votos, prioridad (normal | baja), origen (participante, operador, re-encolado, relleno), participante opcional, motivo de rechazo, marcas temporales.
- **Reserva de relleno**: Colección ordenada de ítems pendientes de inyección con **posición explícita** definible por el operador; cada ítem referencia un vídeo y metadatos; no consume cupo de cola activa hasta transferirse. Al transferirse a cola activa (auto o manual), el ítem se **consume** y deja de existir en la reserva.
- **Configuración de relleno (evento)**: Preferencias del operador: inyección automática activa/inactiva; límites de tamaño de reserva (valores por defecto razonables documentados en supuestos).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El operador puede localizar y re-encolar una canción del historial en menos de **30 segundos** en el 90 % de los intentos en pruebas con listas de hasta 200 entradas históricas.
- **SC-002**: Cuando la reserva tiene al menos una canción y la cola activa queda vacía, el siguiente tema comienza en menos de **5 segundos** tras finalizar la reproducción anterior (sin intervención manual).
- **SC-003**: En pruebas con empate de votos entre canción de usuario y de relleno, el **100 %** de los ordenamientos coloca primero la canción de usuario.
- **SC-004**: Tras re-encolar o inyectar relleno, operador y kiosk reflejan el cambio en menos de **3 segundos** en condiciones de red normales de evento.
- **SC-005**: El **95 %** de los operadores de prueba completan el flujo «añadir 3 canciones a reserva → vaciar cola → verificar que suena relleno» sin asistencia, en una sesión de prueba guiada.

## Assumptions

- Solo usuarios con sesión de operador acceden a historial, reserva y acciones de re-encolado.
- Re-encolar desde historial entra **siempre** directamente en `queued`, sin pasar por `pending_review`, tanto en modo Moderado como Libre; la acción es deliberada del operador.
- La reserva es por evento (misma instancia de configuración/`event_config`); no se exige portabilidad entre despliegues distintos en v1.
- Límite por defecto de reserva: **50** ítems; límite de cola activa existente (**100** `queued`) se mantiene.
- Inyección automática habilitada por defecto; el operador puede desactivarla desde Admin.
- La reserva admite **reordenación manual** por el operador; la inyección automática siempre toma el ítem en posición 1 del orden actual.
- Las canciones de relleno en cola activa **sí** pueden recibir votos de participantes con las **mismas reglas** que cualquier otra entrada en cola; la prioridad baja solo actúa en desempate de votos iguales frente a canciones de usuario.
- El historial incluye entradas del evento actual almacenadas en base de datos; no se implementa archivado multi-evento ni exportación en esta versión.
- Textos de interfaz en **español**, coherente con el resto de Admin.
- Se reutiliza el flujo de búsqueda/validación de vídeo ya existente para operador (equivalente funcional al de participante, sin exponerlo en `/participar`).
