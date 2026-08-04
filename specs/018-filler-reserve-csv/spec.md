# Feature Specification: Exportar e importar reserva de relleno (CSV)

**Feature Branch**: `018-filler-reserve-csv`

**Created**: 2026-08-04

**Status**: Draft

**Input**: Me gustaría también poder exportar / importar las reservas de relleno (por ejemplo a CSV, con simplemente las URLs de las canciones). Es importante mantener el orden, tanto en fichero durante export y de nuevo a la app tras import.

## Clarifications

### Session 2026-08-04

- Q: ¿Qué debe ocurrir al importar un CSV sin URLs válidas (vacío, solo cabecera o líneas en blanco)? → A: **Permitir vaciar la reserva** si el fichero no tiene URLs válidas, pero **solo tras confirmación explícita** en el diálogo de importación.
- Q: ¿Qué formato de referencia debe escribirse al exportar cada canción? → A: **Siempre URL completa de YouTube** (`https://www.youtube.com/watch?v=VIDEO_ID`).
- Q: ¿Debe incluirse cabecera en el CSV exportado? → A: **Sí, siempre** la primera fila `url`; los datos empiezan en la línea 2.
- Q: ¿Cómo debe interpretarse el fichero al importar (delimitadores CSV)? → A: **Una URL por línea no vacía**; ignorar delimitadores de columna; omitir la cabecera `url` en la primera línea.
- Q: ¿Qué debe validar la vista previa antes de confirmar la importación? → A: **Validación completa** (formato, metadata YouTube, duplicados **dentro del fichero**, conflicto con **cola activa/pendiente**, límite de 50). El conteo mostrado es el definitivo si se confirma. **No** se rechazan filas por existir en la reserva actual (la importación la reemplaza).

## Problem

El operador puede gestionar la reserva de canciones de relleno una a una en Admin, pero no puede hacer copias de seguridad, compartir listas entre eventos ni editar lotes grandes fuera de la aplicación (por ejemplo en una hoja de cálculo). Sin exportación/importación, reconstruir una reserva larga tras un error o preparar un evento nuevo requiere trabajo manual repetitivo y aumenta el riesgo de perder el orden acordado para la inyección automática.

## Goals

- Permitir al operador **exportar** la reserva actual a un fichero CSV sencillo (solo URLs de canciones).
- Permitir al operador **importar** un fichero CSV para restaurar o cargar la reserva, **preservando el orden** de las filas.
- Mantener las mismas reglas de calidad y límites que la reserva manual (URLs válidas de YouTube, máximo de ítems, sin duplicados conflictivos).

## Non-Goals

- Exportar o importar la cola activa, el historial de reproducción o envíos de participantes.
- Soportar formatos distintos de CSV en esta versión (JSON, M3U, playlists de Spotify/YouTube).
- Incluir metadatos en el fichero (título, miniatura, duración, votos); solo URLs.
- Permitir que participantes exporten o importen reservas.
- Sincronización automática con almacenamiento en la nube o edición colaborativa del fichero.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Exportar reserva a CSV (Priority: P1)

Como operador en Admin, quiero descargar la reserva de relleno actual como un fichero CSV con las URLs en orden, para poder guardarla, editarla externamente o reutilizarla en otro momento.

**Why this priority**: La exportación es el primer paso para copia de seguridad y edición offline; no requiere importación para aportar valor inmediato.

**Independent Test**: Añadir varias canciones a la reserva en un orden conocido → exportar → abrir el fichero y verificar que las URLs aparecen en el mismo orden, una por fila.

**Acceptance Scenarios**:

1. **Given** la reserva tiene N canciones ordenadas, **When** pulso «Exportar CSV», **Then** se descarga un fichero cuya primera fila es la cabecera `url` y las filas siguientes (de arriba a abajo) corresponden a las posiciones 1..N de la reserva.
2. **Given** la reserva está vacía, **When** exporto, **Then** recibo un fichero con solo la cabecera `url` (sin filas de datos), sin error.
3. **Given** exporto la reserva, **When** reviso el contenido, **Then** cada fila de datos contiene la **URL completa de YouTube** (`https://www.youtube.com/watch?v=…`), una canción por fila.
4. **Given** no tengo sesión de operador, **When** intento exportar, **Then** la acción no está disponible (misma política de acceso que el resto de la reserva).

---

### User Story 2 — Importar CSV a la reserva (Priority: P1)

Como operador en Admin, quiero cargar un fichero CSV con URLs de YouTube y que la reserva quede configurada en ese orden, para restaurar una copia o preparar el evento rápidamente.

**Why this priority**: Complementa la exportación y cumple el objetivo principal de edición por lotes con orden preservado.

**Independent Test**: Crear un CSV con 5 URLs en orden conocido → importar → verificar en Admin que la reserva muestra las mismas canciones en el mismo orden (posiciones 1..5).

**Acceptance Scenarios**:

1. **Given** un CSV válido con URLs en orden, **When** confirmo la importación, **Then** la reserva queda **reemplazada** por las canciones del fichero, respetando el orden fila a fila.
2. **Given** el fichero incluye la cabecera `url` en la primera línea, **When** importo, **Then** el sistema la omite y no la trata como canción.
3. **Given** el fichero contiene líneas en blanco, **When** importo, **Then** esas líneas se omiten sin alterar el orden de las URLs válidas.
4. **Given** el fichero tiene una URL por línea (sin depender de delimitador CSV regional), **When** importo, **Then** cada línea no vacía (tras omitir cabecera) se interpreta como una entrada en orden.
5. **Given** una URL del fichero no es válida o el vídeo no puede resolverse, **When** importo, **Then** la importación **no se aplica** (operación atómica), se informa qué filas fallaron y la reserva previa permanece intacta.
6. **Given** el fichero supera el límite máximo de la reserva o contiene duplicados (misma canción repetida o ya presente en cola activa), **When** importo, **Then** la importación se rechaza con mensaje claro y la reserva no cambia.
7. **Given** importo correctamente, **When** observo la reserva, **Then** las posiciones coinciden con el orden del fichero y la inyección automática usará la primera fila válida como siguiente candidata.

---

### User Story 3 — Confirmación y vista previa antes de importar (Priority: P2)

Como operador, quiero ver cuántas canciones se importarán y que se me advierta de que la importación sustituirá la reserva actual, para evitar pérdidas accidentales.

**Why this priority**: Reduce errores operativos sin bloquear el flujo principal de importación.

**Independent Test**: Seleccionar un fichero → ver resumen (número de filas válidas detectadas) → confirmar → reserva actualizada.

**Acceptance Scenarios**:

1. **Given** selecciono un fichero CSV, **When** el sistema lo analiza, **Then** veo cuántas entradas **válidas y listas para importar** contiene (tras validación completa) y un aviso de que la reserva actual será sustituida.
2. **Given** el análisis detecta filas inválidas, **When** veo la vista previa, **Then** se listan las líneas con error y no puedo confirmar la importación hasta corregir el fichero (o confirmar vaciado si no hay URLs válidas).
3. **Given** la reserva actual tiene canciones y cancelo la confirmación, **When** cierro el diálogo, **Then** la reserva permanece sin cambios.
4. **Given** el fichero no contiene ninguna URL válida (vacío, solo cabecera o líneas en blanco), **When** el sistema muestra la vista previa, **Then** indica que la reserva quedará vacía y requiere confirmación explícita antes de aplicar.
5. **Given** confirmo importar un fichero sin URLs válidas, **When** se completa la operación, **Then** la reserva queda vacía.

---

### Edge Cases

- Fichero con codificación distinta (p. ej. BOM de Excel): el sistema debe interpretar UTF-8 de forma tolerante cuando sea posible.
- Fichero editado con delimitador regional (`;` en Excel europeo) o en editor de texto: cada **línea no vacía** (salvo cabecera `url`) cuenta como una URL; no se exige parsing CSV estricto por columnas.
- Misma canción expresada con URL completa y con ID corto en filas distintas: tratar como duplicado según las reglas actuales de identificación de vídeo.
- Importar un CSV exportado previamente desde la misma app: debe reproducir el mismo orden sin pasos manuales extra.
- Importar un CSV sin URLs válidas: la reserva puede quedar vacía solo si el operador confirma explícitamente en el diálogo de importación; cancelar deja la reserva intacta.
- Reserva al límite (50 ítems): exportación completa; importación que exceda el límite se rechaza.
- Canción del CSV ya en cola activa o pendiente de moderación: importación rechazada con indicación de conflicto.
- Operador importa mientras otro operador edita la reserva (escenario poco frecuente): gana la última operación confirmada; sin bloqueo optimista en v1 (documentado, no requiere UI especial).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir al operador autenticado **exportar** la reserva de relleno actual a un fichero descargable en formato CSV con cabecera `url` en la primera fila.
- **FR-002**: El fichero exportado MUST listar **una URL completa de YouTube por fila de datos** (`https://www.youtube.com/watch?v=VIDEO_ID`), en el **mismo orden** que la reserva (primera fila de datos = posición 1). La importación acepta URL completa o ID de vídeo.
- **FR-003**: El sistema MUST permitir al operador autenticado **importar** un fichero CSV para configurar la reserva.
- **FR-004**: Tras una importación exitosa, la reserva MUST reflejar el **orden de las filas del fichero** (de arriba a abajo → posiciones 1..N).
- **FR-005**: La importación MUST **reemplazar** por completo la reserva existente tras confirmación del operador (no fusionar ni añadir al final por defecto). Si el fichero no contiene URLs válidas, la reserva resultante es **vacía**, aplicable solo tras confirmación explícita en el diálogo de importación.
- **FR-006**: La importación MUST ser **atómica**: si cualquier fila no puede procesarse, ningún cambio parcial se aplica a la reserva. La vista previa MUST ejecutar la **misma validación completa** que la importación final (véase FR-007); si hay errores bloqueantes, la confirmación no está disponible (salvo vaciado explícito sin URLs válidas).
- **FR-007**: El sistema MUST validar cada línea del fichero con: referencia YouTube válida, metadata resoluble, límite ≤50 filas válidas, **sin duplicados de `youtube_video_id` dentro del fichero**, y **sin conflicto con cola activa** (`pending_review`, `queued`, `playing`). **No** se rechaza una fila por existir en la reserva actual en base de datos (la importación reemplaza la reserva). Esta validación MUST completarse en la vista previa antes de permitir confirmar.
- **FR-008**: El sistema MUST interpretar el fichero como **una URL por línea no vacía** (omitir cabecera `url` en la primera línea y líneas en blanco), sin depender del delimitador CSV regional.
- **FR-009**: En caso de error de validación, el sistema MUST informar al operador de forma comprensible (p. ej. número de fila y motivo) sin exponer detalles técnicos internos.
- **FR-010**: Participantes sin sesión de operador MUST NOT poder exportar ni importar la reserva.
- **FR-011**: Tras importación exitosa, el operador MUST ver la reserva actualizada en Admin sin recargar manualmente la página (actualización coherente con el resto del panel).
- **FR-012**: La exportación MUST estar disponible desde la misma sección Admin de «Reserva de relleno» donde se gestiona la reserva hoy.

### Key Entities

- **Reserva de relleno**: lista ordenada de canciones de ambiente del operador; cada ítem tiene posición explícita usada por inyección automática y encolado manual.
- **Fichero CSV de reserva**: documento de intercambio con una columna de URLs completas de YouTube en exportación; en importación se aceptan URL completa o ID de vídeo. El orden de filas es la fuente de verdad del orden de la reserva tras importar.
- **Fila de importación**: una línea del fichero candidata a convertirse en ítem de reserva; se valida por completo en vista previa antes de habilitar la confirmación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un operador puede exportar una reserva de 20 canciones y verificar en menos de 1 minuto que el fichero mantiene el orden exacto de la pantalla Admin.
- **SC-002**: Un operador puede importar un CSV de hasta 50 URLs válidas y tener la reserva lista para usar en menos de 3 minutos (incluyendo vista previa con validación completa y confirmación), con el mismo orden que el fichero.
- **SC-006**: En el 100% de los intentos con al menos una fila inválida detectada en vista previa, el operador ve el número de línea y motivo antes de confirmar, y la confirmación permanece bloqueada hasta corregir el fichero (excepto vaciado explícito sin URLs válidas).
- **SC-003**: En el 100% de los casos con al menos una fila inválida, la reserva previa permanece idéntica tras el intento de importación (sin sustitución parcial).
- **SC-004**: El 90% de los operadores completan exportación + reimportación de una lista de prueba sin necesitar soporte, usando solo las etiquetas y mensajes en español del panel.
- **SC-005**: Tras importar un CSV exportado previamente desde la misma aplicación, el orden de reproducción candidato (posición 1 de reserva) coincide con el de antes de exportar.

## Assumptions

- La reserva de relleno y sus límites (máximo 50 ítems, reglas de duplicado) ya existen y se reutilizan sin cambios de negocio.
- El formato de intercambio usa cabecera `url` en exportación; en importación se lee **una URL por línea** (no CSV estricto por columnas); codificación UTF-8.
- «Reemplazar reserva» es el comportamiento esperado al importar (copia de seguridad / restauración), no una fusión incremental.
- La validación de vídeos (existencia/metadata) se ejecuta en la vista previa y al confirmar, con las mismas reglas que al añadir manualmente en Admin.
- Solo operadores con sesión en Admin acceden a exportar/importar; no se requiere nuevo rol.
- Depende de la feature de reserva de relleno (017) ya disponible en Admin.
