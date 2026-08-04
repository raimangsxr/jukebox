# Feature Specification: Paneles plegables y reinicio de historial

**Feature Branch**: `021-collapsible-panels-reset`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "quiero hacer una serie de cambios ya que hay mucha información, el scroll es muy largo y el usuario y operador se pierden, he pensado en paneles collapsables pero se aceptan sugerencias mejores: - en el panel de admin, los bloques deben ser collapsables, por defecto están todos collapsed salvo el de aprobaciones - en participant mis canciones también los bloques deben ser collapsables, reorganicemos, para que primero este el de votos, luego el de enviar canciones y por ultimo el de mis canciones Por otro lado también quiero poder vaciar la lista de canciones reproducidas, significa que se eliminaran las canciones completamente. La idea es poder utilizar esto para reiniciar la aplicación entre eventos."

## Problem

El panel de administración y la vista de participación han acumulado muchas secciones (moderación, historial, reserva de relleno, configuración, votación, envío de canciones, etc.). En pantallas móviles y de escritorio el desplazamiento vertical es largo y dificulta localizar la acción relevante. Los operadores pierden tiempo buscando la sección correcta; los participantes deben recorrer toda la página para votar o enviar canciones.

Además, entre eventos el operador necesita vaciar por completo el historial (reproducidas y rechazadas) para empezar con un estado fresco, sin arrastrar datos del evento anterior.

## Clarifications

### Session 2026-08-04

- Q: Al vaciar el historial, ¿qué ocurre con las canciones reproducidas/rechazadas visibles en «Mis canciones» de cada participante? → A: Desaparecen también de «Mis canciones» (misma eliminación en base de datos).
- Q: ¿Dónde debe ubicarse «Sonando ahora» respecto a los paneles plegables del participante? → A: Fuera de los paneles plegables, como franja fija siempre visible entre cabecera y votos.
- Q: ¿Qué secciones de Admin muestran contador en la cabecera del panel plegado? → A: Moderación (pendientes) e Historial (total de entradas); el resto sin contador.
- Q: Si llegan nuevos pendientes de aprobación con Moderación plegada, ¿debe auto-expandirse el panel? → A: No; solo actualizar el contador en la cabecera.
- Q: ¿Qué nivel de confirmación requiere «Vaciar historial»? → A: Diálogo confirmar/cancelar con texto de advertencia (mismo patrón que otras acciones destructivas del Admin).

## Goals

- Reducir la carga visual y el scroll mediante **paneles plegables** (acordeón) en Admin y en la vista autenticada de participación.
- Priorizar en Admin la sección de **aprobaciones/moderación** como única expandida por defecto.
- Reordenar la vista de participación: **votos → enviar canciones → mis canciones**.
- Permitir al operador **vaciar por completo** todo el historial (reproducidas y rechazadas) para reiniciar entre eventos.

## Non-Goals

- Rediseño visual completo de la aplicación (colores, tipografía, layout del kiosk).
- Plegar secciones en la pantalla de onboarding de normas ni en el flujo de login.
- Vaciar la cola activa, pendientes de revisión o la reserva de relleno (acciones separadas ya existentes).
- Restablecer votos de participantes, sesiones OAuth, tokens de embed o configuración del evento.
- Persistir el estado plegado/expandido entre sesiones del navegador o dispositivos distintos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Admin con paneles plegables (Priority: P1)

Como operador en el panel de administración, quiero que cada bloque principal sea plegable y que solo la sección de aprobaciones esté abierta al cargar la página, para centrarme de inmediato en lo urgente sin perderme en un scroll infinito.

**Why this priority**: La moderación es la tarea más frecuente en vivo; reducir ruido en Admin tiene impacto inmediato en la operación del evento.

**Independent Test**: Iniciar sesión como operador → abrir Admin → verificar que solo «Moderación» (aprobaciones) está expandida → expandir «Historial» → comprobar que el contenido se muestra y el resto permanece plegado.

**Acceptance Scenarios**:

1. **Given** el operador abre Admin, **When** la página termina de cargar, **Then** todas las secciones principales están plegadas **excepto** la de moderación/aprobaciones (pendientes de revisión, controles de reproducción y modo de cola).
2. **Given** una sección plegada, **When** pulso su cabecera o control de expandir, **Then** se despliega su contenido sin recargar la página.
3. **Given** una sección expandida, **When** pulso su cabecera o control de plegar, **Then** el contenido se oculta y la cabecera sigue visible con indicador de estado (expandido/plegado).
4. **Given** el operador expande varias secciones en la misma visita, **When** navega dentro de Admin sin recargar, **Then** el estado plegado/expandido se mantiene hasta cerrar sesión o recargar la página.
5. **Given** las secciones actuales de Admin, **When** reviso la lista de bloques plegables, **Then** incluyen al menos: Moderación, Historial, Reserva de relleno, Uso de API Keys, Evento y Tokens de iframe.
6. **Given** la sección Moderación está plegada, **When** llega una nueva canción pendiente de aprobación, **Then** el panel **no** se expande automáticamente y el contador de pendientes en la cabecera se actualiza.

---

### User Story 2 — Participación reordenada con paneles plegables (Priority: P1)

Como participante autenticado, quiero ver primero la cola votable, luego las opciones para enviar canciones y al final mis canciones enviadas, cada una en un panel plegable, para votar y enviar música sin desplazarme innecesariamente.

**Why this priority**: La votación y el envío son las acciones principales del participante; el orden actual invierte prioridades y alarga el scroll.

**Independent Test**: Iniciar sesión en `/participar` → verificar orden vertical: votos arriba, envío en el medio, mis canciones abajo → plegar y expandir cada bloque.

**Acceptance Scenarios**:

1. **Given** un participante autenticado que ha aceptado las normas, **When** carga la vista principal, **Then** el primer bloque de contenido plegable (tras cabecera, avisos y «Sonando ahora» si aplica) es la **cola votable** (votos).
2. **Given** la misma vista, **When** despliego hacia abajo, **Then** el siguiente bloque agrupado es **enviar canciones** (búsqueda en YouTube, pegar enlace y acción de envío).
3. **Given** la misma vista, **When** continúo desplazándome, **Then** el bloque **Mis canciones** aparece **después** del de envío.
4. **Given** cada uno de esos tres bloques, **When** uso su control de plegar/expandir, **Then** puedo ocultar o mostrar su contenido de forma independiente.
5. **Given** un participante autenticado, **When** abre la página por primera vez en la sesión, **Then** la sección de **votos** está expandida por defecto y las de **enviar canciones** y **mis canciones** están plegadas por defecto.
6. **Given** hay una canción sonando, **When** la veo en la vista de participación, **Then** «Sonando ahora» aparece en una **franja fija siempre visible** situada entre la cabecera y el panel de votos, fuera de cualquier panel plegable.
7. **Given** no hay canción sonando, **When** cargo la vista de participación, **Then** la franja «Sonando ahora» no se muestra (o permanece oculta).

---

### User Story 3 — Vaciar historial completo (Priority: P2)

Como operador, quiero vaciar por completo todo el historial (reproducidas y rechazadas), para dejar la aplicación lista para un nuevo evento sin rastros del anterior.

**Why this priority**: Es una necesidad operativa entre eventos, pero menos urgente que la usabilidad diaria de Admin y participación.

**Independent Test**: Tener entradas reproducidas y rechazadas en historial → pulsar «Vaciar historial» en Admin → confirmar → verificar que desaparecen todas y no pueden re-encolarse.

**Acceptance Scenarios**:

1. **Given** hay una o más entradas en el historial (reproducidas y/o rechazadas), **When** el operador pulsa «Vaciar historial» (o equivalente) en la sección Historial, **Then** se muestra un diálogo de confirmación con texto de advertencia y botones Cancelar / Confirmar, indicando que la acción es irreversible y eliminará **todas** las entradas del historial.
2. **Given** el diálogo de confirmación visible, **When** el operador confirma, **Then** todas las entradas del historial (reproducidas y rechazadas) se eliminan permanentemente y el listado se actualiza (incluida paginación y totales).
3. **Given** el diálogo de confirmación visible, **When** el operador cancela, **Then** no se elimina ninguna entrada.
4. **Given** hay canciones en cola activa, pendientes de revisión o en reproducción, **When** vacío el historial, **Then** esas entradas no se ven afectadas.
5. **Given** un participante o usuario no autenticado como operador, **When** intenta vaciar el historial, **Then** la acción no está disponible o se deniega.
6. **Given** el historial está vacío, **When** el operador ve la sección Historial, **Then** la acción de vaciar está deshabilitada o indica que no hay nada que eliminar.
7. **Given** el filtro de historial está activo (p. ej. solo «Reproducidas»), **When** el operador vacía el historial, **Then** se eliminan **todas** las entradas del historial, no solo las visibles con el filtro actual.
8. **Given** un participante tiene canciones reproducidas o rechazadas en «Mis canciones», **When** el operador vacía el historial, **Then** esas entradas desaparecen también de la vista del participante (actualización en vivo o al refrescar).

---

### Edge Cases

- ¿Qué ocurre si el operador vacía el historial mientras un participante tiene «Mis canciones» abierto? Las entradas eliminadas deben desaparecer de su lista vía actualización en vivo (SSE) o al refrescar.
- ¿Qué ocurre si el operador vacía el historial mientras otra pestaña de Admin lo muestra? Tras la acción, la lista y el badge de total global deben refrescarse vía evento SSE `state` (mismo mecanismo que pendientes de moderación).
- ¿Qué pasa si el historial solo tiene entradas rechazadas? La acción de vaciar sigue disponible y las elimina junto con cualquier reproducida.
- ¿Paneles con contenido dinámico (p. ej. tabla de aprobaciones vacía)? El panel sigue siendo plegable; Moderación muestra «0 pendientes» e Historial «0 entradas» en la cabecera cuando corresponda.
- ¿Llegan pendientes con Moderación plegada? El contador sube en la cabecera sin expandir el panel; el operador decide cuándo abrirlo.
- ¿Participante en móvil con teclado abierto al buscar? Plegar «Mis canciones» no debe interferir con el envío ni ocultar el botón «Enviar canción» del bloque de envío (el botón permanece en el panel «Enviar canciones», validar en quickstart Phase 2b).
- ¿Accesibilidad? Cada panel debe ser operable con teclado y anunciar estado expandido/plegado para lectores de pantalla.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El panel de administración DEBE presentar cada sección principal como un panel plegable con cabecera clicable y estado visual expandido/plegado.
- **FR-002**: Al cargar Admin por primera vez en una sesión, SOLO la sección de moderación/aprobaciones DEBE estar expandida; el resto DEBE estar plegado.
- **FR-003**: El estado plegado/expandido de las secciones de Admin DEBE conservarse mientras el operador permanece en la misma sesión de página (sin recarga); los nuevos pendientes de aprobación NO DEBEN forzar la expansión de Moderación, solo actualizar su contador en cabecera.
- **FR-004**: La vista autenticada de participación DEBE agrupar el contenido en paneles plegables para: cola votable, envío de canciones y mis canciones.
- **FR-005**: El orden vertical de esos tres bloques plegables en participación DEBE ser: (1) cola votable, (2) enviar canciones, (3) mis canciones. La franja «Sonando ahora» (cuando hay reproducción activa) DEBE mostrarse **antes** del panel de votos y **fuera** de los paneles plegables.
- **FR-006**: Al cargar participación por primera vez en una sesión, la sección de votos DEBE estar expandida; enviar canciones y mis canciones DEBEN estar plegadas por defecto.
- **FR-007**: El bloque «enviar canciones» DEBE incluir búsqueda, pegar enlace y el control para enviar la canción seleccionada.
- **FR-008**: El operador DEBE poder eliminar permanentemente **todas** las entradas del historial (reproducidas y rechazadas) mediante una acción dedicada en la sección Historial de Admin.
- **FR-009**: La acción de vaciar historial DEBE requerir confirmación explícita mediante un diálogo **confirmar/cancelar** con texto de advertencia (mismo patrón que otras acciones destructivas del Admin, sin escribir palabra clave ni doble diálogo), indicando que se borrarán todas las entradas del historial.
- **FR-010**: Vaciar historial NO DEBE eliminar entradas en cola, pendientes de revisión, en reproducción ni ítems de la reserva de relleno.
- **FR-011**: Tras vaciar el historial, el listado, el badge de total global y cualquier vista dependiente DEBEN quedar vacíos sin inconsistencias de paginación, independientemente del filtro de estado activo en el momento de la acción (véase FR-008).
- **FR-012**: Solo el operador autenticado DEBE poder ejecutar la acción de vaciar historial.
- **FR-013**: Las cabeceras de panel plegable en Admin DEBEN mostrar un resumen breve visible incluso con el panel plegado: **Moderación** con el número de pendientes de aprobación e **Historial** con el **total global** de entradas terminales (reproducidas + rechazadas), **independiente** del filtro de estado activo en el listado; las demás secciones no requieren contador.
- **FR-014**: Al vaciar el historial, las entradas eliminadas DEBEN dejar de aparecer en «Mis canciones» de los participantes afectados, con la misma inmediatez que en el listado de Admin.

### Key Entities

- **Panel plegable**: Sección de interfaz con cabecera, estado expandido/plegado y contenido asociado; agrupa funcionalidad relacionada sin eliminar datos subyacentes.
- **Entrada de historial**: Canción en estado terminal (reproducida o rechazada); candidata a eliminación permanente por la acción de vaciar; distinta de entradas activas en cola o pendientes de revisión.
- **Estado de interfaz de sesión**: Preferencia temporal de qué paneles están expandidos; aplica solo a la visita actual sin recarga.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El operador localiza la sección de aprobaciones en Admin en menos de 3 segundos tras cargar la página (sin scroll previo), en el 95 % de pruebas con usuarios de prueba.
- **SC-002**: La altura visible inicial de Admin (viewport estándar móvil 390×844) muestra la cabecera y al menos la sección de moderación expandida sin requerir scroll para ver pendientes de aprobación.
- **SC-003**: El participante puede emitir su primer voto sin desplazarse más de una pantalla desde la parte superior de la vista autenticada.
- **SC-004**: Tras vaciar el historial, el 100 % de las entradas (reproducidas y rechazadas) desaparecen y no son recuperables ni re-encolables desde la interfaz.
- **SC-005**: La cola activa, pendientes de revisión y reserva de relleno permanecen intactas en el 100 % de las pruebas de vaciado del historial.
- **SC-006**: Reducción percibida del «scroll innecesario»: en pruebas moderadas, al menos 4 de 5 operadores y participantes reportan que encuentran más rápido la acción que buscan frente a la versión anterior.
- **SC-007**: Tras vaciar el historial, ningún participante ve canciones reproducidas o rechazadas en «Mis canciones» que hayan sido eliminadas.

## Assumptions

- Se adoptan **paneles tipo acordeón** como patrón principal; no se requiere un rediseño alternativo (pestañas, navegación lateral) en esta entrega.
- «Aprobaciones» corresponde a la sección **Moderación** actual (pendientes de revisión y controles asociados), no a un bloque nuevo.
- «Vaciar historial» elimina **todas** las entradas terminales del historial (reproducidas y rechazadas), independientemente del filtro de estado visible en la interfaz; esas mismas entradas dejan de mostrarse en «Mis canciones» de cada participante.
- El estado plegado/expandido se reinicia al recargar la página; no se persiste en almacenamiento local ni en el servidor.
- La confirmación de vaciar historial sigue el **mismo patrón de diálogo** que re-encolar, cambio de modo de cola o vaciar reserva (advertencia + Cancelar / Confirmar).
- La acción de vaciar es **irreversible**; no hay papelera ni deshacer.
- «Sonando ahora» es una **franja fija no plegable**, siempre visible entre cabecera y panel de votos cuando hay reproducción activa; desaparece u oculta cuando no hay nada sonando.
- Los participantes no autenticados y la pantalla de normas no forman parte del alcance de paneles plegables.
