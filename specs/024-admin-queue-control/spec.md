# Feature Specification: Control de cola de reproducción en Admin

**Feature Branch**: `024-admin-queue-control`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "quiero añadir una feature para controlar la cola de reproducción desde Admin, desde ver las canciones en cola (ordenadas por posición ascendente) con toda su info, sus votos, su posición en la cola. Debo poder vaciar toda la cola de reproducción en general, y luego como acciones individuales en cada acción: forzar reproducir, modificar votos, eliminarla de la cola"

## Problem

El operador gestiona la reproducción en vivo desde Admin, pero la cola activa (lo que está sonando y lo que viene después) no tiene una vista dedicada con control granular. Hoy los controles globales de reproducción (**Iniciar reproducción**, **Saltar canción**) y el estado de audio viven en Moderación junto a la aprobación de pendientes, mezclando tareas distintas. No puede inspeccionar la cola completa con contexto (votos, posición, quién envió la canción), vaciarla de un golpe, forzar una canción concreta, ajustar votos manualmente ni sacar una entrada sin pasar por moderación o historial.

Sin este panel, corregir la cola en un evento con mucha participación es lento y propenso a errores: el operador no ve el orden real de reproducción ni puede actuar sobre una sola canción con precisión.

## Clarifications

### Session 2026-08-04

- Q: Al eliminar una entrada de la cola o vaciar la cola, ¿qué ocurre con esas canciones en datos y en «Mis canciones» del participante? → A: **Eliminación permanente** — desaparecen de cola, historial y «Mis canciones» del participante.
- Q: Cuando forzar reproducir interrumpe otra canción que ya estaba sonando, ¿qué ocurre con la interrumpida? → A: **Marcar como reproducida** — aparece en historial y «Mis canciones» (como un skip).
- Q: Al eliminar una entrada individual de la cola, ¿se requiere confirmación? → A: **Siempre confirmar** — diálogo confirmar/cancelar antes de eliminar.
- Q: ¿El operador puede modificar votos de la canción que está sonando ahora? → A: **Sí, permitido** — puede editar votos de lo sonando; no interrumpe reproducción; solo reordena lo pendiente.
- Q: ¿En qué posición del Admin debe aparecer el panel Cola de reproducción? → A: **Justo después de Moderación** — antes de Historial y el resto.
- Q: ¿Dónde deben estar «Iniciar reproducción» y «Saltar canción»? → A: **En el panel Cola de reproducción** — se **mueven** desde Moderación; Moderación queda solo para modo de cola y pendientes de aprobación.

## Goals

- Añadir en Admin un **panel plegable de cola de reproducción** ubicado **inmediatamente después de Moderación** (antes de Historial y el resto de secciones), que concentre **toda la gestión de reproducción activa**: estado de reproducción/audio, **Iniciar reproducción**, **Saltar canción**, listado de cola y acciones sobre entradas.
- **Mover** desde Moderación al panel Cola de reproducción los controles **Iniciar reproducción** y **Saltar canción**, junto con el indicador de estado de reproducción y avisos de audio del kiosk (sin duplicarlos en Moderación).
- Mostrar en cada fila la **información completa** relevante para el operador: título, miniatura, votos, posición, estado (sonando / en cola), prioridad, duración cuando exista, origen de la entrada y nombre del participante que la envió (si aplica).
- Permitir **vaciar toda la cola de reproducción** con confirmación explícita.
- Permitir en cada entrada acciones individuales: **forzar reproducir**, **modificar votos** y **eliminar de la cola**.
- Mantener coherencia con el kiosk y la vista de participación: cualquier cambio en la cola debe reflejarse en las pantallas en vivo sin recargar manualmente.

## Non-Goals

- Gestionar desde este panel las canciones **pendientes de moderación** (permanece en Moderación).
- Mostrar **Iniciar reproducción**, **Saltar canción** ni indicadores de estado de reproducción/audio en Moderación (solo en Cola de reproducción).
- Gestionar historial reproducido/rechazado (permanece en Historial).
- Gestionar la reserva de relleno (permanece en su panel).
- Permitir reordenar arrastrando filas o cambiar prioridad (`normal` / `low`) desde la UI en la primera versión.
- Exportar la cola a CSV o compartir enlaces externos.
- Que participantes editen votos o fuerce reproducción desde `/participar`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ver cola activa ordenada (Priority: P1)

Como operador en Admin, quiero abrir un panel y ver todas las canciones de la cola de reproducción en el orden en que se reproducirán, con votos y posición, para entender el estado actual sin adivinar.

**Why this priority**: Sin visibilidad clara de la cola, ninguna acción de control tiene contexto; es el fundamento del feature.

**Independent Test**: Con varias canciones en cola y una sonando → expandir «Cola de reproducción» → verificar orden, posiciones y datos de cada fila.

**Acceptance Scenarios**:

1. **Given** el operador abre Admin, **When** la página termina de cargar, **Then** el panel **Cola de reproducción** está **plegado** por defecto, aparece **inmediatamente después de Moderación** (antes de Historial) y Moderación sigue siendo la única sección expandida por defecto.
2. **Given** el panel está plegado, **When** pulso su cabecera para expandirlo, **Then** se cargan y muestran las entradas de la cola activa sin recargar la página.
3. **Given** hay una canción sonando y varias en cola, **When** reviso el listado, **Then** la canción **sonando** aparece **primera**, marcada como tal, y el resto sigue en orden de **posición ascendente** (1, 2, 3… hacia lo que se reproducirá después).
4. **Given** cualquier fila del listado, **When** la inspecciono, **Then** veo al menos: **título**, **miniatura** (si existe), **número de votos**, **posición en cola**, **estado** (sonando / en cola), **prioridad**, enlace **Previsualizar** al vídeo y **nombre del participante** que envió la canción cuando está vinculada a un participante.
5. **Given** la cola activa está vacía (nada sonando ni en cola), **When** expando el panel, **Then** veo un estado vacío claro sin errores.
6. **Given** el panel está expandido, **When** otro operador o un participante cambia la cola (voto, envío, salto), **Then** el listado se actualiza en vivo en Admin (mismo comportamiento de actualización en vivo que el resto de la consola).

---

### User Story 1b — Controles globales de reproducción en el panel de cola (Priority: P1)

Como operador, quiero **Iniciar reproducción** y **Saltar canción** en el mismo panel donde veo la cola activa, para controlar el playback sin mezclarlo con la moderación de pendientes.

**Why this priority**: Reorganiza la UI según tareas reales; los controles globales deben vivir junto al listado de cola que afectan.

**Independent Test**: Expandir «Cola de reproducción» → verificar botones y estado de reproducción → usar Iniciar/Saltar → comprobar que Moderación ya no muestra esos controles.

**Acceptance Scenarios**:

1. **Given** el operador expande **Cola de reproducción**, **When** revisa la cabecera del contenido, **Then** ve el **estado de reproducción** (sonando / en espera / sin cola) y los avisos de audio del kiosk cuando aplican, igual que antes en Moderación.
2. **Given** hay canciones en cola pero nada sonando, **When** el operador pulsa **Iniciar reproducción** en Cola de reproducción, **Then** la primera canción pendiente empieza a sonar (misma semántica que el control actual).
3. **Given** hay una canción sonando, **When** el operador pulsa **Saltar canción** en Cola de reproducción, **Then** la actual se marca reproducida y la siguiente empieza si existe (misma semántica que el salto global actual).
4. **Given** el operador abre **Moderación**, **When** revisa su contenido, **Then** **no** aparecen los botones **Iniciar reproducción** ni **Saltar canción** ni el bloque de estado de reproducción/audio asociado.
5. **Given** Moderación sin controles de reproducción, **When** el operador revisa su contenido, **Then** sigue mostrando modo de cola (Moderado/Libre) y la lista de **pendientes de aprobación** con aprobar/rechazar.
6. **Given** un botón de reproducción no aplicable (sin cola o sin canción sonando), **When** el operador lo ve en Cola de reproducción, **Then** el botón correspondiente está deshabilitado con la misma lógica que hoy.

---

### User Story 2 — Vaciar toda la cola (Priority: P1)

Como operador, quiero vaciar por completo la cola de reproducción para detener la secuencia planificada y dejar el reproductor sin pendientes cuando el evento lo requiera.

**Why this priority**: Es una acción global solicitada explícitamente y crítica en situaciones de reinicio o corrección masiva.

**Independent Test**: Con canciones sonando y en cola → pulsar «Vaciar cola» → confirmar → verificar que no quedan entradas activas y el kiosk refleja el vacío.

**Acceptance Scenarios**:

1. **Given** hay al menos una entrada en la cola activa (sonando o en cola), **When** el operador pulsa «Vaciar cola» (o equivalente), **Then** aparece un diálogo de confirmación con advertencia de que se eliminarán **todas** las canciones de la cola de reproducción y se detendrá lo que esté sonando.
2. **Given** el diálogo visible, **When** el operador confirma, **Then** **todas** las entradas de la cola activa se **eliminan permanentemente** (cola, historial terminal e «Mis canciones»): lo que estaba sonando deja de reproducirse y no quedan canciones pendientes de reproducir.
3. **Given** el diálogo visible, **When** el operador cancela, **Then** la cola no cambia.
4. **Given** hay canciones pendientes de moderación, en historial o en reserva de relleno, **When** vacío la cola de reproducción, **Then** esas otras listas **no** se ven afectadas.
5. **Given** la cola activa está vacía, **When** el operador ve el panel, **Then** «Vaciar cola» está deshabilitado o indica que no hay nada que vaciar.
6. **Given** un usuario sin sesión de operador, **When** intenta vaciar la cola, **Then** la acción no está disponible o se deniega.

---

### User Story 3 — Forzar reproducir una canción (Priority: P2)

Como operador, quiero forzar que una canción concreta de la cola empiece a reproducirse ahora, para responder a peticiones urgentes del evento sin reordenar manualmente votos.

**Why this priority**: Control fino de alto valor en vivo, pero depende de ver la cola (P1).

**Independent Test**: Con varias canciones en cola y una sonando → forzar reproducir la tercera → verificar que esa canción pasa a sonar y el estado global es coherente.

**Acceptance Scenarios**:

1. **Given** una entrada en cola (no sonando), **When** el operador elige «Forzar reproducir», **Then** esa canción pasa a **sonando** y el reproductor del kiosk la reproduce (o la prepara según el comportamiento actual de inicio de reproducción).
2. **Given** otra canción estaba sonando, **When** fuerzo reproducir una distinta, **Then** la anterior **deja de sonar**, **no** vuelve a la cola activa y se **marca como reproducida** (visible en historial y «Mis canciones» del participante, igual que un salto manual).
3. **Given** la entrada seleccionada ya está sonando, **When** el operador pulsa «Forzar reproducir», **Then** no hay cambio destructivo (acción deshabilitada o sin efecto visible).
4. **Given** la acción se completa, **When** reviso el panel y el kiosk, **Then** la cola se reordena y las posiciones mostradas se actualizan.

---

### User Story 4 — Modificar votos de una entrada (Priority: P2)

Como operador, quiero ajustar manualmente el número de votos de una canción en cola para corregir errores o decisiones del evento, y que el orden de reproducción refleje el nuevo recuento.

**Why this priority**: Solicitado explícitamente; complementa la visibilidad de votos en el listado.

**Independent Test**: Dos canciones en cola con distintos votos → aumentar votos de la segunda por encima de la primera → verificar nuevo orden de posiciones.

**Acceptance Scenarios**:

1. **Given** una entrada en la cola activa, **When** el operador elige «Modificar votos», **Then** puede introducir un **entero no negativo** como nuevo total de votos de esa entrada.
2. **Given** el operador guarda un valor válido, **When** la acción termina, **Then** el recuento mostrado en la fila coincide con el valor guardado y las **posiciones** del resto de la cola se recalculan según las reglas de orden existentes (más votos primero, con desempates por prioridad y antigüedad).
3. **Given** el operador introduce un valor no válido (negativo, vacío, no numérico), **When** intenta guardar, **Then** se muestra error claro y la cola no cambia.
4. **Given** una canción está sonando, **When** modifico sus votos, **Then** sigue sonando en ese momento (el cambio de votos no interrumpe la reproducción actual) pero las entradas **en cola** se reordenan según el nuevo recuento.

---

### User Story 5 — Eliminar una entrada de la cola (Priority: P2)

Como operador, quiero eliminar una canción concreta de la cola de reproducción sin vaciar todo, para quitar contenido inapropiado o duplicados detectados tarde.

**Why this priority**: Acción individual esencial junto a forzar reproducir y modificar votos.

**Independent Test**: Eliminar una entrada en cola que no está sonando → verificar que desaparece y las posiciones se actualizan; eliminar o saltar la que está sonando → verificar transición coherente.

**Acceptance Scenarios**:

1. **Given** una entrada en cola (no sonando), **When** el operador elige «Eliminar de la cola», **Then** se muestra un diálogo de confirmación con advertencia antes de eliminar permanentemente.
2. **Given** el diálogo de eliminación visible, **When** el operador confirma, **Then** la entrada desaparece de la cola activa y no aparece en el kiosk como pendiente.
3. **Given** la entrada eliminada era la que estaba sonando, **When** el operador confirma la eliminación, **Then** deja de reproducirse y, si hay otra canción en cola, **la siguiente empieza a reproducirse** automáticamente; si no hay más, el reproductor queda sin canción activa.
4. **Given** el operador cancela la confirmación de eliminación, **When** cierra el diálogo, **Then** la entrada permanece en la cola.
5. **Given** la eliminación se completa, **When** reviso historial y «Mis canciones» del participante remitente, **Then** la entrada **no** existe en ninguna de esas vistas (eliminación permanente, no un evento de historial).
6. **Given** un participante tenía la canción eliminada en «Mis canciones», **When** la eliminación se completa, **Then** esa entrada desaparece también de su vista (actualización en vivo o al refrescar).

---

### Edge Cases

- ¿Qué ocurre si se vacía la cola mientras el kiosk está reproduciendo? → La reproducción se detiene y el kiosk muestra estado sin canción activa, coherente con cola vacía.
- ¿Qué pasa si forzar reproducir con cola de una sola entrada ya sonando? → Sin cambio o acción deshabilitada.
- ¿Modificar votos a 0? → Permitido; la entrada puede bajar de posición según las reglas de orden.
- ¿Eliminar la última canción en cola mientras otra suena? → Solo se elimina la seleccionada; lo sonando continúa si no era la eliminada.
- ¿Entradas de operador sin participante vinculado? → Se muestran con indicador de origen operador (relleno, directo, re-encolado, etc.) sin nombre de participante.
- ¿Cola llena (límite de entradas en cola)? → El panel muestra todas las entradas activas; vaciar o eliminar libera capacidad para nuevos envíos.
- ¿Usuario no operador? → No ve el panel o no puede ejecutar acciones; intentos directos se deniegan.
- ¿Operador busca Saltar/Iniciar en Moderación tras el cambio? → Esos controles solo existen en Cola de reproducción; Moderación limitada a modo de cola y pendientes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST ofrecer en Admin un panel plegable **Cola de reproducción**, ubicado **inmediatamente después de Moderación** (antes de Historial y demás secciones), plegado por defecto al cargar la página.
- **FR-002**: Al expandir el panel, el sistema MUST cargar y mostrar todas las entradas de la **cola activa** (estados sonando y en cola pendiente de reproducir), excluyendo pendientes de moderación e historial.
- **FR-003**: El listado MUST ordenarse por **posición ascendente**: primero la entrada sonando (si existe), luego las demás en el orden en que se reproducirán.
- **FR-004**: Cada fila MUST mostrar al menos: título, miniatura cuando exista, votos, posición, estado (sonando / en cola), prioridad, enlace **Previsualizar** al vídeo (mismo patrón que Moderación) y nombre del participante remitente cuando la entrada esté vinculada a un participante.
- **FR-005**: Cada fila MUST mostrar además metadatos ya disponibles en el sistema para la entrada: duración cuando exista, origen de la entrada (participante, operador, relleno automático, etc.) y fecha de creación en formato legible.
- **FR-006**: El panel MUST actualizarse en vivo cuando la cola cambie por votos, envíos, saltos u otras acciones autorizadas, sin exigir recarga manual de la página.
- **FR-007**: El operador MUST poder **vaciar toda la cola de reproducción** mediante una acción global con diálogo de confirmación que advierta que se detendrá la reproducción y se eliminarán todas las entradas activas.
- **FR-008**: Tras confirmar vaciar cola, el sistema MUST **eliminar permanentemente** todas las entradas de la cola activa (sonando y en cola), incluidas de historial y «Mis canciones» de participantes, y MUST NOT afectar pendientes de moderación, entradas ya en historial terminal ni reserva de relleno.
- **FR-009**: En cada entrada, el operador MUST poder **forzar reproducir**, haciendo que esa entrada pase a sonar; si otra estaba sonando, MUST marcarla como **reproducida** (historial y «Mis canciones», coherente con salto manual) sin devolverla a la cola activa.
- **FR-010**: En cada entrada de la cola activa (sonando o en cola), el operador MUST poder **modificar votos** introduciendo un entero ≥ 0; al guardar, MUST actualizar el recuento mostrado, reordenar las entradas **pendientes de reproducir** según las reglas de orden vigentes del producto y, si la entrada está sonando, MUST NOT interrumpir la reproducción actual.
- **FR-011**: En cada entrada, el operador MUST poder **eliminar de la cola** tras diálogo de **confirmación obligatoria**; al confirmar, la entrada MUST eliminarse **permanentemente** (sin fila en historial ni en «Mis canciones» del participante).
- **FR-012**: Si se elimina la entrada sonando y quedan entradas en cola, el sistema MUST iniciar automáticamente la siguiente según el orden vigente; si no quedan, MUST dejar el reproductor sin canción activa.
- **FR-013**: Todas las acciones del panel MUST requerir sesión de operador; participantes y usuarios no autenticados MUST NOT poder ejecutarlas.
- **FR-014**: Tras cualquier acción exitosa que modifique la cola, el kiosk y la vista de participación MUST reflejar el nuevo estado en vivo (cola votable, sonando ahora, etc.).
- **FR-015**: La cabecera del panel plegable MUST mostrar un **contador** de entradas en la cola activa (incluyendo la que está sonando), actualizado en vivo.
- **FR-016**: El panel Cola de reproducción MUST incluir los controles **Iniciar reproducción** y **Saltar canción** con la **misma semántica y reglas de habilitación** que tenían en Moderación (idle + cola → iniciar; sonando → saltar).
- **FR-017**: El panel Cola de reproducción MUST mostrar el **estado de reproducción** (texto de estado sonando/en espera/sin cola) y los **avisos de audio del kiosk** (p. ej. reproducción silenciada) cuando aplican.
- **FR-018**: Moderación MUST **no** mostrar Iniciar reproducción, Saltar canción ni el bloque de estado/avisos de reproducción/audio; MUST conservar modo de cola y gestión de pendientes de aprobación.

### Key Entities

- **Entrada de cola activa**: Canción en estado sonando o en cola pendiente de reproducir; atributos visibles: título, miniatura, enlace de previsualización al vídeo, votos, posición, estado, prioridad, duración, origen, participante remitente, fecha de creación.
- **Cola de reproducción**: Conjunto ordenado de entradas activas que define qué suena ahora y qué sonará después; distinta de pendientes de moderación, historial y reserva de relleno.
- **Acción de vaciar cola**: Operación global que elimina permanentemente todas las entradas activas, detiene la reproducción y borra esas entradas de historial terminal y «Mis canciones».
- **Acción forzar reproducir**: Promoción inmediata de una entrada a sonando; si otra estaba sonando, la interrumpida se marca **reproducida** (no eliminada).
- **Acción modificar votos**: Actualización manual del recuento de votos de una entrada con reordenación consecuente.
- **Acción eliminar**: Eliminación permanente de una entrada de la cola activa (sin historial terminal ni rastro en «Mis canciones»).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El operador puede identificar la canción sonando y el orden completo de las siguientes en **menos de 10 segundos** tras expandir el panel, sin consultar el kiosk.
- **SC-002**: Vaciar la cola activa (confirmación incluida) completa la operación y actualiza Admin y kiosk en **menos de 5 segundos** en condiciones normales de evento.
- **SC-003**: Forzar reproducir una canción en cola hace que esa canción sea la sonando en **menos de 5 segundos** y el kiosk refleja el cambio sin recarga manual.
- **SC-004**: Tras modificar votos, el **100%** de las posiciones mostradas coinciden con el orden de reproducción definido por las reglas de orden del producto (votos, prioridad, antigüedad).
- **SC-005**: Eliminar una entrada la hace desaparecer de la cola activa y del listado del panel en la **misma sesión de actualización en vivo**, sin pasos manuales adicionales.
- **SC-006**: **Cero** acciones del panel son ejecutables por participantes o usuarios no operadores en pruebas de acceso no autorizado.
- **SC-007**: En pruebas con cola vacía, el panel muestra estado vacío claro y **no** presenta errores ni acciones destructivas habilitadas sin contenido.
- **SC-008**: Tras expandir Cola de reproducción, el operador puede **Iniciar** o **Saltar** en **menos de 5 segundos** sin abrir Moderación; Moderación **no** expone esos botones en ningún estado de la página.

## Assumptions

- «Cola de reproducción» se refiere únicamente a entradas **sonando** y **en cola** (cola activa), no a pendientes de moderación ni historial; coherente con la distinción ya existente en Admin entre Moderación, Historial y Reserva.
- «Toda su info» incluye los campos que el sistema ya almacena para cada entrada (título, miniatura, votos, posición, estado, prioridad, duración, origen, participante, fecha); no se exige mostrar datos que el sistema no posee.
- «Posición ascendente» significa orden de reproducción: primero lo que suena, luego posición 1, 2, 3… hacia lo que viene; la entrada sonando se distingue visualmente y no compite con el número de posición de las siguientes.
- «Forzar reproducir» equivale a un salto inmediato: la entrada elegida suena; si otra estaba sonando, la interrumpida se **marca como reproducida** (historial y «Mis canciones», como skip global), no se elimina permanentemente.
- «Eliminar de la cola» y «Vaciar cola» **eliminan permanentemente** las entradas afectadas (cola activa, historial terminal e «Mis canciones»); distinto de rechazar en moderación (que marca rechazada) o de vaciar historial (solo terminal existente).
- «Vaciar cola» detiene todo lo activo y deja cero entradas en cola de reproducción, sin tocar pendientes de moderación, historial terminal previo ni reserva.
- El panel sigue el patrón de paneles plegables de Admin (como Estadísticas e Historial): plegado por defecto, contador en cabecera, confirmación en acciones destructivas; **orden en Admin**: Moderación (expandida por defecto, solo modo de cola + pendientes) → **Cola de reproducción** (reproducción global + listado + acciones) → Historial → resto de secciones.
- La actualización en vivo reutiliza el mismo mecanismo de sincronización que ya usa Admin para estado de cola y reproducción (sin polling dedicado al panel salvo carga inicial al expandir).
