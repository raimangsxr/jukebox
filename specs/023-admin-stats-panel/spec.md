# Feature Specification: Panel de estadísticas en Admin

**Feature Branch**: `023-admin-stats-panel`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "quiero añadir en admin un nuevo panel collapsed de estadisticas, entre otros datos me gustaría tener información de cuantos usuarios han participado, los 10 que más canciones han enviado (y cuantas), los 10 qué más canciones han votado, las 10 canciones más votadas (y con cuantos votos) y otras estadísticas que te parezcan interesantes"

## Problem

Durante un evento en vivo, el operador necesita entender rápidamente el nivel de participación y qué canciones o personas están generando más actividad. Hoy el panel de administración ofrece moderación, historial y configuración, pero no hay una vista consolidada de métricas de participación. Sin estadísticas visibles, es difícil valorar el éxito del evento, detectar picos de actividad o reconocer a los participantes más activos.

## Goals

- Añadir en Admin un **panel plegable de estadísticas**, **plegado por defecto**, accesible junto al resto de secciones existentes.
- Mostrar **métricas de participación** del evento actual: usuarios activos, rankings de envíos y votos, y canciones más votadas.
- Incluir **indicadores resumen** útiles para el operador sin obligar a exportar datos ni consultar bases de datos externas.
- Mantener la información **legible en móvil y escritorio**, coherente con el estilo visual del Admin actual.

## Non-Goals

- Analítica histórica multi-evento con comparativas entre fechas o exportación a BI externo.
- Estadísticas en tiempo real para participantes o en el kiosk.
- Gráficos interactivos complejos (líneas temporales, mapas de calor) en la primera versión.
- Persistir preferencias de panel expandido/plegado entre dispositivos.
- Modificar límites de voto/búsqueda ni la lógica de cola.

## Clarifications

### Session 2026-08-04

- Q: ¿Cómo deben actualizarse las estadísticas cuando el panel está expandido? → A: **Carga al expandir** + botón **Actualizar**; sin auto-refresh continuo (ni SSE ni polling mientras está abierto).
- Q: ¿Qué ocurre con las estadísticas al vaciar historial? → A: **Solo datos actuales** — las métricas reflejan únicamente lo que sigue en el sistema; votos, envíos y rankings asociados a entradas eliminadas desaparecen de las estadísticas.
- Q: ¿Los contadores de estado de cola entran en la primera versión? → A: **Sí, v1 completa** — pendientes, en cola, sonando, reproducidas y rechazadas en el mismo panel.
- Q: ¿Cómo tratar empates en el puesto 10 de los rankings? → A: **Máximo 10 filas**; empates en el último puesto se desempatan **alfabéticamente** por nombre de participante o título de canción.
- Q: ¿Qué cuenta como «canción enviada» en el ranking de participantes? → A: **Todos los envíos** del participante, en cualquier estado (pendiente, en cola, sonando, reproducida o rechazada).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ver resumen de participación (Priority: P1)

Como operador en Admin, quiero abrir un panel de estadísticas y ver de un vistazo cuánta gente ha participado y cuánta actividad hay en el evento, para evaluar el engagement sin salir de la consola.

**Why this priority**: El contador de participantes y los totales globales responden la pregunta más frecuente del operador («¿cuánta gente está usando la jukebox?»).

**Independent Test**: Iniciar sesión como operador → expandir «Estadísticas» → verificar tarjetas o filas con totales de participantes, envíos y votos.

**Acceptance Scenarios**:

1. **Given** el operador abre Admin, **When** la página termina de cargar, **Then** el panel **Estadísticas** está **plegado** por defecto (Moderación sigue siendo la única sección expandida por defecto).
2. **Given** el panel Estadísticas está plegado, **When** pulso su cabecera para expandirlo, **Then** se despliega el contenido y las estadísticas se **cargan automáticamente** en ese momento (sin recargar la página).
3. **Given** el panel expandido, **When** reviso el resumen superior, **Then** veo al menos: **número de participantes únicos que han participado**, **total de canciones enviadas por participantes**, **total de votos emitidos** y **número de canciones distintas en la cola/historial con al menos un voto**.
4. **Given** no ha habido actividad de participantes, **When** abro Estadísticas, **Then** los totales muestran **cero** con mensaje o estado vacío claro (sin errores ni pantalla en blanco).

---

### User Story 2 — Rankings de participantes más activos (Priority: P1)

Como operador, quiero ver los 10 participantes que más canciones han enviado y los 10 que más votos han emitido, con el nombre visible y el recuento, para reconocer a la audiencia más activa.

**Why this priority**: Son métricas explícitamente solicitadas y de alto valor en eventos sociales.

**Independent Test**: Con datos de prueba (varios participantes con envíos y votos distintos) → expandir Estadísticas → comprobar orden descendente y límite de 10 filas por ranking.

**Acceptance Scenarios**:

1. **Given** hay participantes con envíos registrados, **When** consulto el ranking «Más canciones enviadas», **Then** veo hasta **10 filas** ordenadas de mayor a menor número de envíos, cada una con **nombre del participante** y **cantidad de envíos**.
2. **Given** hay participantes con votos registrados, **When** consulto el ranking «Más votos emitidos», **Then** veo hasta **10 filas** ordenadas de mayor a menor número de votos, cada una con **nombre del participante** y **cantidad de votos**.
3. **Given** hay empate en el puesto 10, **When** se muestra el ranking, **Then** se muestran **como máximo 10 filas** y los empatados en el último puesto se desempatan por orden **alfabético** (nombre del participante o título de la canción).
4. **Given** un participante solo ha votado pero nunca ha enviado canciones, **When** reviso los rankings, **Then** aparece en «Más votos emitidos» si entra en el top 10 y **no** aparece en «Más canciones enviadas».
5. **Given** menos de 10 participantes con actividad en una categoría, **When** muestro ese ranking, **Then** solo aparecen las filas existentes (sin relleno ficticio).

---

### User Story 3 — Canciones más votadas (Priority: P1)

Como operador, quiero ver las 10 canciones más votadas del evento con su título y número total de votos, para saber qué temas están resonando con la audiencia.

**Why this priority**: Complementa los rankings de personas y cierra el triángulo envío–voto–popularidad.

**Independent Test**: Crear entradas con distintos `vote_count` → verificar que el ranking muestra título, votos y orden correcto.

**Acceptance Scenarios**:

1. **Given** hay canciones con votos en el sistema, **When** consulto «Canciones más votadas», **Then** veo hasta **10 filas** con **título de la canción**, **número total de votos** y orden descendente por votos.
2. **Given** la misma canción de YouTube fue enviada más de una vez, **When** se calcula el ranking, **Then** los votos se **agregan por canción** (mismo vídeo = una sola fila con votos sumados).
3. **Given** una canción sin votos, **When** reviso el ranking, **Then** no aparece en la lista de más votadas.
4. **Given** hay empate en votos entre canciones, **When** se ordena el ranking, **Then** el desempate es por **título alfabético**; si varias canciones empatan en el puesto 10, se aplica el mismo criterio alfabético y se muestran como máximo **10 filas**.

---

### User Story 4 — Indicadores adicionales de actividad (Priority: P1)

Como operador, quiero ver otras métricas útiles del estado actual del evento (cola, pendientes, reproducciones) en el mismo panel, para tener contexto operativo junto a la participación.

**Why this priority**: Los contadores de cola complementan los rankings en la primera entrega y dan contexto operativo inmediato sin complejidad adicional.

**Independent Test**: Con cola en distintos estados → verificar que los contadores reflejan pendientes, en cola, sonando, reproducidas y rechazadas.

**Acceptance Scenarios**:

1. **Given** el panel Estadísticas expandido, **When** reviso la sección de actividad de cola, **Then** veo contadores separados para: **pendientes de revisión**, **en cola**, **sonando ahora** (0 o 1), **reproducidas** y **rechazadas**.
2. **Given** el operador vacía el historial desde Admin, **When** vuelvo a abrir o actualizo Estadísticas, **Then** los contadores de **reproducidas** y **rechazadas** reflejan el vaciado (disminuyen o pasan a cero según corresponda).
3. **Given** el panel está expandido, **When** pulso **Actualizar**, **Then** las cifras se recalculan con los datos más recientes sin recargar toda la página.
4. **Given** el panel está expandido, **When** ocurre actividad nueva en el evento (voto, envío, etc.), **Then** las cifras **no** se actualizan solas hasta pulsar **Actualizar** o **plegar y volver a expandir** el panel.
5. **Given** el panel está plegado, **When** ocurre actividad nueva, **Then** no se realizan peticiones de estadísticas en segundo plano.

---

### Edge Cases

- Participante con sesión dev u OAuth sin envíos ni votos: no cuenta como «ha participado».
- Participante eliminado o sin nombre visible: mostrar **nombre para mostrar**, si falta **parte local del email** (antes de `@`), si no **«Participante»**.
- Evento recién iniciado sin datos: panel funcional con ceros y textos de «sin datos aún».
- Solo canciones del operador (relleno, envío directo) sin participantes: totales de participantes en cero; rankings de participantes vacíos; canciones más votadas pueden incluir filler si recibió votos.
- Votos sobre entradas reproducidas o rechazadas: cuentan en totales y rankings **mientras esas entradas existan** en el sistema.
- Tras **vaciar historial**: desaparecen de las estadísticas los votos, envíos y posiciones en rankings ligados a entradas eliminadas; los contadores de reproducidas/rechazadas pasan a cero; participantes que solo votaron o enviaron canciones ya eliminadas pueden dejar de aparecer en rankings o en el conteo de «han participado» si ya no queda actividad registrada.
- Canciones **rechazadas** o **pendientes de revisión** enviadas por un participante **sí cuentan** en su total de envíos y en el ranking «Más canciones enviadas».
- Listas largas en móvil: rankings legibles sin desbordar horizontalmente (título truncado con tooltip o segunda línea si hace falta).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El panel Admin MUST incluir una sección plegable **Estadísticas**, **plegada por defecto**, usando el mismo patrón de acordeón que el resto de secciones (021).
- **FR-002**: Solo usuarios con acceso de **operador** MUST poder ver el panel y sus datos.
- **FR-003**: El sistema MUST mostrar el **número de participantes únicos que han participado**, definido como participantes con **al menos un envío de canción o al menos un voto** registrado en los datos actuales del evento.
- **FR-004**: El sistema MUST mostrar un ranking de hasta **10 participantes** con más **canciones enviadas**, con nombre visible y recuento por participante. Cada **envío atribuido al participante** cuenta, **independientemente del estado** (pendiente de revisión, en cola, sonando, reproducida o rechazada).
- **FR-005**: El sistema MUST mostrar un ranking de hasta **10 participantes** con más **votos emitidos**, con nombre visible y recuento de votos por participante.
- **FR-006**: El sistema MUST mostrar un ranking de hasta **10 canciones más votadas**, agregando votos **por vídeo de YouTube** (mismo identificador de vídeo = una fila), con título y total de votos.
- **FR-007**: El sistema MUST mostrar **totales globales** en el resumen: canciones enviadas por participantes, votos emitidos en total y participantes únicos (los mismos campos que sustentan FR-003, presentados como tarjetas de resumen).
- **FR-008**: El sistema MUST mostrar **contadores de estado de cola**: pendientes de revisión, en cola, sonando, reproducidas y rechazadas.
- **FR-009**: Al **expandir** el panel Estadísticas, el sistema MUST **cargar automáticamente** las métricas más recientes. El operador MUST poder **actualizar manualmente** con el botón **Actualizar** mientras el panel está expandido, sin recargar la página completa. **No** MUST haber auto-refresh continuo (SSE ni polling) mientras el panel permanece abierto.
- **FR-010**: Las estadísticas MUST basarse en los **datos actualmente almacenados** en el sistema (no en periodos históricos archivados fuera de la aplicación).
- **FR-011**: Tras **vaciar historial**, las estadísticas MUST reflejar **solo los datos que permanecen** en el sistema: se excluyen votos, envíos y canciones de entradas eliminadas; contadores de reproducidas/rechazadas MUST actualizarse en la siguiente carga o al pulsar **Actualizar**.
- **FR-012**: Cuando un ranking tenga menos de 10 elementos, el sistema MUST mostrar solo los existentes, con estado vacío explícito si no hay datos. Con **10 o más candidatos**, MUST mostrarse **como máximo 10 filas**; empates en el puesto 10 MUST desempatarse por orden **alfabético** (nombre del participante o título de la canción).
- **FR-013**: Los textos de la UI MUST estar en **español**, coherente con el resto del Admin.

### Key Entities

- **Participante**: Persona autenticada en `/participar`; atributos relevantes: nombre para mostrar, identificador interno.
- **Envío de canción**: Entrada de cola creada por un participante; cuenta para estadísticas en **cualquier estado** (pendiente, en cola, sonando, reproducida, rechazada).
- **Voto**: Acción de un participante sobre una entrada en cola votable.
- **Canción (vídeo)**: Identificador de YouTube y título; puede aparecer en varias entradas; votos agregables por vídeo.
- **Métrica resumen**: Valor numérico calculado (totales, contadores por estado).
- **Ranking**: Lista ordenada de hasta 10 elementos con etiqueta (nombre o título) y valor (recuento).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El operador puede localizar y expandir el panel Estadísticas en **menos de 10 segundos** en una visita habitual a Admin.
- **SC-002**: Tras expandir el panel, el operador ve **todas las métricas de la v1** (participantes, rankings, canciones más votadas y contadores de cola) **sin desplazarse más de dos pantallas** en un viewport móvil estándar.
- **SC-003**: Los totales y rankings coinciden con los datos reales del evento con **precisión del 100%** respecto a los registros subyacentes en pruebas de aceptación.
- **SC-004**: Tras pulsar actualizar, las cifras visibles reflejan cambios recientes (envío, voto o vaciado de historial) en **menos de 3 segundos** en condiciones normales de red local.
- **SC-005**: En eventos sin actividad, el operador recibe una experiencia clara (ceros o mensajes vacíos) **sin errores visibles** en el 100% de los casos de prueba definidos.

## Assumptions

- «Ha participado» = al menos un envío **o** al menos un voto; no basta con iniciar sesión sin actividad.
- Los envíos del operador (relleno, envío directo) **no** cuentan en rankings de participantes, pero sí pueden aparecer en canciones más votadas si reciben votos.
- El panel se ubica en Admin **después de Historial** y antes de Reserva de relleno, manteniendo Moderación como única sección expandida al cargar.
- No se requiere badge en la cabecera del panel plegado (como Tokens o Evento).
- Carga automática al **expandir** el panel + botón **Actualizar**; **sin** SSE ni polling mientras el panel está abierto (re-expandir también recarga).
- Empates en posición 10: **máximo 10 filas**; desempate **alfabético** por nombre de participante o título de canción.
- Tras **vaciar historial**, las estadísticas se recalculan sobre datos supervivientes (sin memoria histórica de entradas borradas).
- Los contadores de estado de cola (pendientes, en cola, sonando, reproducidas, rechazadas) forman parte de la **primera versión**, no de una iteración posterior.
- El recuento de **canciones enviadas** incluye **todos los estados** (pendiente, en cola, sonando, reproducida, rechazada).
- Títulos largos se truncan visualmente con accesibilidad preservada (texto completo disponible al foco o en segunda línea).
