# Feature Specification: Construir reserva de relleno (playlist, CSV incremental y vaciar)

**Feature Branch**: `019-filler-reserve-playlist`

**Created**: 2026-08-04

**Status**: Draft

**Input**: Quiero permitir añadir a la lista de reserva también una playlist de YouTube y que de ahí se cojan todas las canciones. Tanto importar CSV como añadir una lista de reproducción, deben añadir las canciones a la lista, no sustituir el contenido actual. La idea es poder ir construyendo una lista con otros trozos y playlists. También añade un botón para «Vaciar» la lista de reserva en caso de que queramos empezar de cero.

## Clarifications

### Session 2026-08-04

- Q: Si una canción del lote (playlist o CSV) está en la cola activa o pendiente de moderación, ¿rechazar todo el lote u omitir solo las en conflicto? → A: **Omitir solo las en conflicto** y añadir el resto del lote en orden.
- Q: Si una playlist incluye vídeos no disponibles o no resolubles, ¿rechazar todo el lote u omitir solo los fallidos? → A: **Omitir solo los no resolubles** y añadir el resto del lote en orden.
- Q: Si el lote aporta más canciones nuevas de las que caben en la reserva, ¿rechazar todo el lote o añadir solo las que quepan? → A: **Añadir solo las que quepan** (en orden del lote) hasta el límite; vista previa indica omitidas por capacidad.
- Q: ¿Sigue siendo válido vaciar la reserva importando un CSV vacío/sin URLs añadibles, además del botón «Vaciar»? → A: **Solo el botón «Vaciar»** vacía la reserva; CSV sin URLs añadibles se rechaza en vista previa sin efecto.
- Q: Si el operador pega una URL de un solo vídeo en el campo de playlist, ¿rechazar o añadir ese vídeo? → A: **Añadir ese único vídeo** al final de la reserva (equivalente a playlist de 1 canción).

## Problem

Hoy el operador puede exportar e importar la reserva de relleno por CSV, pero la importación **sustituye** la lista entera. Eso impide combinar varias fuentes (un CSV parcial, una playlist de YouTube, canciones añadidas a mano) en una sola reserva ordenada. Tampoco existe una forma rápida de cargar todas las canciones de una playlist de YouTube ni de reiniciar la reserva de un solo golpe cuando se quiere empezar de cero.

## Goals

- Permitir al operador **añadir** canciones desde una **playlist de YouTube** a la reserva existente, respetando el orden de la playlist.
- Cambiar la importación CSV para que **añada** canciones al final de la reserva actual en lugar de reemplazarla.
- Ofrecer un botón **«Vaciar»** con confirmación para eliminar toda la reserva y empezar de cero.
- Mantener las reglas de calidad y límites existentes (referencias YouTube válidas, máximo de ítems, conflictos con cola activa).

## Non-Goals

- Sincronizar la reserva con cambios posteriores en la playlist de YouTube (carga puntual al confirmar).
- Soportar playlists de otras plataformas (Spotify, Apple Music, etc.).
- Fusionar o reordenar automáticamente al añadir; las nuevas canciones van **al final** de la reserva actual salvo reordenación manual posterior.
- Permitir que participantes sin sesión de operador añadan playlists, importen CSV o vacíen la reserva.
- Usar importación CSV vacía o sin URLs añadibles como sustituto del botón «Vaciar» (solo «Vaciar» vacía la reserva).
- Sustituir la exportación CSV existente ni cambiar su formato.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Añadir playlist de YouTube a la reserva (Priority: P1)

Como operador en Admin, quiero pegar la URL de una playlist de YouTube y añadir todas sus canciones a la reserva actual, para cargar rápidamente un bloque de ambiente sin perder lo que ya tenía.

**Why this priority**: Es la capacidad nueva principal que el operador pidió y aporta valor inmediato para montar eventos.

**Independent Test**: Tener 3 canciones en reserva → pegar URL de playlist con 5 vídeos en orden conocido → confirmar → verificar que la reserva tiene 8 canciones, las 3 originales primero y las 5 de la playlist después, en el orden de la playlist.

**Acceptance Scenarios**:

1. **Given** la reserva tiene N canciones, **When** introduzco una URL de playlist válida y confirmo, **Then** las canciones de la playlist se **añaden al final** de la reserva, conservando el orden de la playlist y las N posiciones existentes sin cambios.
2. **Given** la playlist incluye vídeos no disponibles o no resolubles, **When** confirmo la operación, **Then** esos vídeos se **omiten** y el resto del lote se añade en orden; la vista previa indica cuántos se omiten por no ser resolubles.
3. **Given** añadir la playlist dejaría más canciones nuevas de las que caben en la reserva, **When** confirmo, **Then** se añaden **solo las que quepan** en orden de la playlist y el resto se omiten por capacidad; la vista previa indica cuántas se añadirán y cuántas se omiten por límite.
4. **Given** una canción de la playlist ya está en la reserva, **When** confirmo, **Then** esa canción se **omite** (no se duplica) y el resto se añade en orden; la vista previa indica cuántas son nuevas y cuántas se omiten por duplicado en reserva.
5. **Given** una o más canciones de la playlist están en la cola activa o pendiente de moderación, **When** confirmo, **Then** esas canciones se **omiten** y el resto del lote se añade en orden; la vista previa indica cuántas se omiten por conflicto con cola.
6. **Given** no tengo sesión de operador, **When** intento añadir una playlist, **Then** la acción no está disponible.
7. **Given** pego una URL de un solo vídeo (no de playlist) en el campo de playlist, **When** confirmo, **Then** se añade **ese único vídeo** al final de la reserva, aplicando las mismas reglas de omisión (reserva, cola, no resoluble, capacidad).

---

### User Story 2 — Importar CSV añadiendo al final (Priority: P1)

Como operador, quiero que al importar un CSV las canciones se **añadan** al final de la reserva actual, para poder ir construyendo la lista con varios ficheros o trozos editados por separado.

**Why this priority**: Cambia un comportamiento clave de la importación CSV ya existente y es necesario para el flujo de «construir» la reserva.

**Independent Test**: Reserva con 2 canciones → importar CSV con 3 URLs en orden → confirmar → reserva con 5 canciones, orden original 1–2 y nuevas 3–5 según el fichero.

**Acceptance Scenarios**:

1. **Given** la reserva tiene N canciones y un CSV válido con M URLs, **When** confirmo la importación, **Then** la reserva queda con N+M canciones (o menos si hay omisiones por duplicado en reserva), con las nuevas **después** de las existentes y en el orden del fichero.
2. **Given** el CSV incluye una URL ya presente en la reserva, **When** confirmo, **Then** esa fila se omite sin duplicar; las demás se añaden en orden.
3. **Given** el fichero contiene duplicados de la misma canción entre sí, **When** importo, **Then** la operación se rechaza (atómica) con indicación de las filas duplicadas y la reserva no cambia.
4. **Given** N+M superaría el límite máximo tras contar solo canciones nuevas, **When** confirmo, **Then** se añaden solo las que quepan al final de la reserva (en orden del fichero) y el resto se omiten por capacidad; la vista previa indica ambos conteos.
5. **Given** una fila del CSV tiene una referencia con formato inválido, **When** confirmo, **Then** la operación se rechaza por completo (error bloqueante) y la reserva no cambia.
6. **Given** una fila del CSV tiene referencia válida pero el vídeo no se puede resolver, **When** confirmo, **Then** esa fila se **omite** y el resto se añade en orden; la vista previa indica cuántas filas se omiten por no ser resolubles.
7. **Given** selecciono un CSV, **When** veo la vista previa, **Then** se indica que las canciones se **añadirán** al final (no que sustituirán la reserva) y cuántas entradas nuevas se incorporarán.
8. **Given** una o más filas del CSV corresponden a canciones en la cola activa o pendiente de moderación, **When** confirmo, **Then** esas filas se **omiten** y el resto se añade en orden; la vista previa indica cuántas se omiten por conflicto con cola.

---

### User Story 3 — Vaciar la reserva (Priority: P2)

Como operador, quiero un botón «Vaciar» que elimine toda la reserva de relleno, para poder empezar de cero sin importar un fichero vacío ni borrar canción a canción.

**Why this priority**: Complementa el flujo incremental; sin vaciar, reconstruir desde cero sería tedioso.

**Independent Test**: Reserva con varias canciones → pulsar «Vaciar» → confirmar → reserva vacía; cancelar en otro intento → sin cambios.

**Acceptance Scenarios**:

1. **Given** la reserva tiene al menos una canción, **When** pulso «Vaciar» y confirmo, **Then** la reserva queda **vacía** y la UI se actualiza sin recargar la página.
2. **Given** pulso «Vaciar», **When** cancelo la confirmación, **Then** la reserva no cambia.
3. **Given** la reserva ya está vacía, **When** observo el botón «Vaciar», **Then** está deshabilitado o no realiza acción destructiva sin contenido.
4. **Given** no tengo sesión de operador, **When** intento vaciar, **Then** la acción no está disponible.

---

### User Story 4 — Vista previa y confirmación (Priority: P2)

Como operador, quiero ver una vista previa antes de añadir una playlist o un CSV, para saber cuántas canciones nuevas entrarán y detectar errores antes de aplicar cambios.

**Why this priority**: Reduce errores al combinar varias fuentes y mantiene paridad con el flujo de importación CSV existente.

**Independent Test**: Seleccionar playlist o CSV → revisar resumen (nuevas, omitidas, errores) → confirmar o cancelar según corresponda.

**Acceptance Scenarios**:

1. **Given** introduzco una playlist o selecciono un CSV, **When** el sistema analiza el contenido, **Then** veo cuántas canciones **nuevas** se añadirán, cuántas se omitirán por ya estar en reserva, cuántas por conflicto con cola activa, cuántas por no ser resolubles, cuántas por capacidad, y si hay errores bloqueantes.
2. **Given** hay errores bloqueantes, **When** veo la vista previa, **Then** no puedo confirmar hasta corregir la fuente o cancelar.
3. **Given** un CSV no contiene ninguna URL añadible (vacío, solo cabecera o líneas en blanco), **When** veo la vista previa, **Then** se rechaza sin efecto en la reserva y se indica que no hay canciones que añadir (vaciar la reserva requiere el botón «Vaciar»).
4. **Given** cancelo el diálogo, **When** cierro la vista previa, **Then** la reserva permanece sin cambios.

---

### Edge Cases

- Playlist privada, eliminada o URL no reconocible como playlist ni vídeo válido: rechazo con mensaje comprensible; reserva intacta.
- URL de un solo vídeo en el campo de playlist: se trata como lote de 1 canción y se añade al final si es añadible.
- Playlist vacía o lote sin ninguna canción añadible tras omitir duplicados, conflictos de cola y no resolubles: rechazo en vista previa; nada que añadir.
- Playlist muy larga respecto a huecos libres en reserva (límite 50): se añaden las que quepan en orden; el resto se omiten por capacidad (vista previa obligatoria).
- Reserva ya al límite (50 ítems): no se puede añadir ninguna canción nueva hasta liberar espacio o vaciar; la vista previa indica cero añadibles.
- Misma canción en playlist y ya en reserva: se omite; no cuenta para el límite de huecos nuevos.
- Duplicados dentro del mismo CSV o dentro de la misma playlist: rechazo atómico (misma canción dos veces en el lote).
- Canción del lote en cola activa (`pending_review`, `queued`, `playing`): se **omite**; el resto del lote se añade si no hay otros errores bloqueantes.
- Vaciar con inyección automática activa: la reserva queda vacía; la cola y la reproducción actual no se ven afectadas.
- CSV sin ninguna URL añadible (vacío, solo cabecera o líneas en blanco): rechazo en vista previa sin cambiar la reserva; vaciar solo mediante botón «Vaciar».
- Operador añade playlist y otro importa CSV casi a la vez: gana la última operación confirmada; sin bloqueo optimista en v1.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir al operador autenticado **añadir canciones desde una URL de playlist de YouTube** a la reserva de relleno.
- **FR-002**: Las canciones obtenidas de una playlist MUST añadirse **al final** de la reserva existente, en el **mismo orden** que aparecen en la playlist.
- **FR-003**: La importación CSV MUST **añadir** canciones al final de la reserva existente (comportamiento actual de sustitución total queda **obsoleto** para esta feature).
- **FR-004**: El sistema MUST ofrecer un control **«Vaciar»** en la sección Admin de reserva de relleno que elimine **todas** las entradas de la reserva tras **confirmación explícita** del operador.
- **FR-005**: Tanto la adición por playlist como por CSV MUST ser **atómica solo ante errores bloqueantes** (p. ej. duplicados dentro del lote, referencia con formato inválido en CSV, playlist inaccesible, lote sin ninguna canción añadible). Las entradas omitibles (ya en reserva, en cola activa, no resolubles, o en exceso por capacidad) MUST excluirse del lote sin impedir la adición del resto hasta el límite máximo.
- **FR-006**: El sistema MUST validar cada candidato con: referencia YouTube válida, contenido resoluble cuando aplique, y sin duplicados de la misma canción **dentro del lote**. Las canciones **ya presentes en la reserva**, en **cola activa** (`pending_review`, `queued`, `playing`), **no resolubles**, o **en exceso por capacidad** MUST omitirse sin error; las añadibles MUST respetar el límite máximo total de la reserva.
- **FR-007**: La vista previa MUST ejecutar la misma validación que la confirmación y mostrar: número de canciones nuevas a añadir, número omitidas por duplicado en reserva, por conflicto con cola activa, por no ser resolubles, por capacidad, y errores bloqueantes por línea o por vídeo cuando aplique.
- **FR-008**: Para CSV, el sistema MUST seguir interpretando **una URL por línea no vacía** (cabecera `url` opcional en primera línea, líneas en blanco ignoradas), sin cambiar el formato de exportación existente.
- **FR-009**: Para playlist, el sistema MUST aceptar URLs de playlist de YouTube en los formatos habituales que el operador pueda copiar del navegador. Si la URL corresponde a **un solo vídeo**, MUST tratarse como lote de una canción y añadirse al final con las mismas reglas de omisión y capacidad.
- **FR-010**: Tras confirmar playlist, CSV incremental o vaciado, el operador MUST ver la reserva actualizada en Admin sin recargar manualmente la página.
- **FR-011**: Participantes sin sesión de operador MUST NOT poder añadir playlists, importar CSV ni vaciar la reserva.
- **FR-012**: El botón «Vaciar» MUST requerir confirmación con advertencia de acción irreversible; cancelar MUST dejar la reserva intacta. MUST ser la **única** acción que elimina toda la reserva (la importación CSV sin URLs añadibles MUST NOT vaciar la reserva).
- **FR-013**: En caso de error, el sistema MUST informar de forma comprensible (motivo y, si aplica, posición en fichero o identificador de vídeo) sin exponer detalles técnicos internos.

### Key Entities

- **Reserva de relleno**: lista ordenada de canciones de ambiente del operador; posiciones usadas por inyección automática y encolado manual; límite máximo de ítems.
- **Lote de adición**: conjunto de canciones procedentes de un CSV o de una playlist que se validan y confirman juntos; se añaden al final de la reserva en orden de origen.
- **Playlist de YouTube (origen)**: lista externa referenciada por URL; el orden de sus vídeos define el orden relativo de las entradas nuevas en la reserva. Una URL de vídeo individual se trata como origen de un lote de 1 ítem.
- **Fichero CSV de reserva**: documento de intercambio con URLs de canciones; en esta feature actúa como fuente de un lote incremental, no como reemplazo de la reserva completa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un operador puede añadir una playlist de 10 canciones a una reserva con 5 existentes y verificar en menos de 2 minutos que la reserva tiene 15 entradas en el orden esperado (5 originales + 10 nuevas).
- **SC-002**: Un operador puede importar dos CSV distintos de forma secuencial y construir una reserva combinada sin perder el orden relativo de cada fichero, en menos de 5 minutos para hasta 50 canciones totales.
- **SC-003**: En el 100% de los intentos con al menos un error bloqueante en el lote, la reserva previa permanece idéntica tras cancelar o tras un rechazo en vista previa.
- **SC-004**: Un operador puede vaciar una reserva de 20 canciones con confirmación en menos de 30 segundos y comprobar que la lista queda vacía.
- **SC-005**: El 90% de los operadores completan «reserva inicial + playlist + CSV adicional» sin soporte, usando solo etiquetas y mensajes en español del panel.
- **SC-006**: La vista previa muestra en el 100% de los casos el conteo de canciones nuevas vs omitidas (reserva, cola activa, no resolubles y capacidad) antes de permitir confirmar un lote válido.

## Assumptions

- La reserva de relleno, sus límites (máximo 50 ítems) y la exportación CSV ya existen (features 017 y 018).
- «Añadir al final» es el comportamiento por defecto; el operador puede reordenar manualmente después si lo necesita.
- Omitir entradas no añadibles (reserva, cola, no resolubles, capacidad) facilita construir listas por partes sin perder el contenido válido del lote.
- Rechazar el lote completo solo ante errores **bloqueantes** (duplicados dentro del lote, formato inválido, playlist inaccesible, cero canciones añadibles) mantiene integridad de datos sin penalizar listas imperfectas o parcialmente llenas.
- Solo operadores con sesión en Admin acceden a estas acciones; no se requiere nuevo rol.
- La carga de playlist es puntual al confirmar; no hay suscripción a cambios futuros en YouTube.
- Vaciar la reserva no elimina entradas de la cola activa ni detiene la reproducción en curso.
- Importar CSV sin canciones añadibles no sustituye al botón «Vaciar»; el operador debe usar «Vaciar» explícitamente para empezar de cero.
