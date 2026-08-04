# Feature Specification: Contador de reinicio de límites en participación

**Feature Branch**: `022-limit-reset-countdown`

**Created**: 2026-08-04

**Status**: Draft

**Input**: User description: "quiero añadir un contador de tiempo (minutos y segundos) restante para reiniciar el contador de votos disponibles en /participar. La idea es que el usuario tenga información muy clara de cuando va a poder recuperar el total de sus votos. Si no ha gastado ningun voto no debe mostrar nada. El reset de votos debe empezar a contar desde que se gasta el primer voto (cuando tienes el total disponible). Todo el sistema de votos y tiempos de reinicio debe ser coherente entre frontends y backend. Para los demás elementos limitados (búsquedas en Youtube) sigamos el mismo patrón, implementémoslo también en esta spec"

## Problem

Los participantes en `/participar` ven cuántos votos y búsquedas les quedan, pero no **cuándo** recuperarán el cupo completo tras haberlo usado. Los mensajes genéricos del tipo «espera unos minutos» generan incertidumbre durante el evento y aumentan la fricción al votar o buscar canciones.

Además, la lógica de ventana de reinicio debe ser **predecible y única**: el participante, el servidor y cualquier pantalla que muestre límites deben coincidir en el momento exacto en que se restaura el cupo.

## Clarifications

### Session 2026-08-04

- Q: ¿Cuándo debe mostrarse el contador de votos si el participante aún tiene votos restantes en la ventana (p. ej. 1 de 2)? → A: En cuanto gasta el **primer voto** de la ventana, aunque le queden votos por usar; el contador indica el tiempo hasta recuperar el cupo **completo**.
- Q: ¿Dónde debe mostrarse cada contador en `/participar`? → A: Votos en la **cabecera** junto a «X de Y votos»; búsquedas en la **subsección Buscar en YouTube** del panel Enviar canciones.
- Q: ¿Qué texto debe acompañar al contador MM:SS? → A: Sustituir «(cada 10 min)» por **«Cupo completo en MM:SS»** cuando la ventana está activa; sin ventana activa, solo «X de Y votos disponibles» (sin mención genérica de 10 min).
- Q: ¿Debe mostrarse el cupo restante de búsquedas como en votos? → A: Sí — **«X de Y búsquedas disponibles»** en la subsección Buscar en YouTube, más «Cupo completo en MM:SS» cuando la ventana esté activa.
- Q: ¿Qué ocurre en el cliente cuando el contador llega a `00:00`? → A: **Actualización automática** del estado del participante; desaparece el contador y se restaura el cupo visible sin recargar la página ni repetir la acción.

## Goals

- Mostrar un **contador en vivo** (minutos y segundos) en `/participar` que indique cuánto falta para recuperar el **cupo completo** de votos, cuando el participante ya ha consumido al menos uno en la ventana activa.
- Aplicar el **mismo patrón** al límite de **búsquedas en YouTube** (contador visible solo tras el primer consumo en la ventana activa).
- Definir una regla de ventana **coherente y autoritativa en el servidor**: el periodo de reinicio comienza al **primer consumo** realizado estando al cupo máximo; el cliente solo refleja esa verdad.
- **No mostrar** ningún contador cuando el participante está al cupo completo y no ha iniciado una ventana de consumo.

## Non-Goals

- Cambiar los topes configurables de votos o búsquedas por evento/despliegue (siguen siendo los ya existentes).
- Contador para el límite de **canciones pendientes** en cola/revisión (regla distinta, no es ventana temporal).
- Mostrar el contador en kiosk, admin u otras superficies salvo donde ya se informe del límite de votos de forma estática (p. ej. panel QR).
- Historial de consumos, notificaciones push o avisos sonoros al expirar la ventana.
- Permitir al operador configurar la duración de la ventana desde la UI (permanece la configuración de despliegue actual).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Contador de reinicio de votos (Priority: P1)

Como participante en `/participar`, quiero ver cuántos minutos y segundos faltan para recuperar todos mis votos cuando ya he gastado al menos uno, para saber exactamente cuándo podré volver a votar con el cupo completo.

**Why this priority**: Es el caso de uso principal descrito; reduce frustración en el momento de votación.

**Independent Test**: Participante con cupo completo → no ve contador → gasta un voto → aparece contador MM:SS → al llegar a cero el cupo vuelve al máximo y el contador desaparece.

**Acceptance Scenarios**:

1. **Given** el participante tiene el cupo completo de votos y no ha votado en la ventana actual, **When** mira la zona de votación, **Then** no ve ningún contador de reinicio de votos.
2. **Given** el participante tiene el cupo completo, **When** emite su primer voto de la ventana, **Then** aparece un contador en formato **minutos:segundos** (p. ej. `09:59`) indicando el tiempo restante para recuperar el cupo **completo**, aunque aún le queden votos por usar en esa ventana.
3. **Given** el participante ya ha gastado votos en la ventana activa, **When** observa el contador, **Then** el valor disminuye cada segundo de forma continua hasta llegar a `00:00`.
4. **Given** el contador de votos llega a `00:00`, **When** el sistema actualiza el estado del participante **automáticamente**, **Then** el cupo de votos vuelve al máximo configurado, el contador desaparece y no hace falta recargar la página.
5. **Given** el participante gasta su último voto disponible en la ventana, **When** intenta votar de nuevo, **Then** sigue viendo el contador con el tiempo restante coherente con el mensaje de límite agotado.

---

### User Story 2 — Contador de reinicio de búsquedas (Priority: P1)

Como participante que busca canciones en YouTube, quiero el mismo tipo de contador para mis búsquedas, para saber cuándo recuperaré todas mis búsquedas disponibles sin adivinar.

**Why this priority**: Misma necesidad de claridad en el otro límite temporal principal de participación.

**Independent Test**: Participante con búsquedas disponibles → sin contador → realiza una búsqueda → aparece contador → al expirar la ventana recupera el cupo y el contador desaparece.

**Acceptance Scenarios**:

1. **Given** el participante tiene el cupo completo de búsquedas y no ha buscado en la ventana actual, **When** mira la sección de búsqueda, **Then** no ve contador de reinicio de búsquedas.
2. **Given** el participante tiene el cupo completo de búsquedas, **When** mira la subsección Buscar en YouTube, **Then** ve **«X de Y búsquedas disponibles»** sin contador.
3. **Given** el participante tiene el cupo completo de búsquedas, **When** realiza su primera búsqueda de la ventana, **Then** aparece un contador MM:SS para recuperar el cupo **completo** de búsquedas, aunque aún le queden búsquedas por usar en esa ventana.
4. **Given** el participante agota las búsquedas de la ventana, **When** intenta buscar de nuevo, **Then** ve el mensaje de límite existente **y** el contador con el tiempo restante alineado con ese mensaje.
5. **Given** el participante puede pegar un enlace sin buscar, **When** no ha consumido búsquedas en la ventana, **Then** el contador de búsquedas sigue oculto (pegar enlace no inicia la ventana de búsquedas).

---

### User Story 3 — Coherencia servidor–cliente (Priority: P1)

Como participante, quiero que el tiempo mostrado coincida con lo que el sistema aplica al permitirme votar o buscar de nuevo, para confiar en el contador aunque recargue la página o use otro dispositivo con la misma sesión.

**Why this priority**: Sin coherencia, el contador es engañoso y empeora la experiencia.

**Independent Test**: Comparar el instante en que el servidor permite de nuevo la acción con el momento en que el contador llega a cero y desaparece; deben coincidir en la misma sesión tras recarga.

**Acceptance Scenarios**:

1. **Given** un participante con votos parcialmente consumidos, **When** recarga `/participar`, **Then** el contador se muestra con un valor coherente con el servidor (diferencia imperceptible para el usuario, ≤ 2 segundos).
2. **Given** dos pestañas con la misma sesión de participante, **When** gasta un voto en una pestaña, **Then** la otra pestaña refleja el contador y el cupo actualizado sin intervención manual.
3. **Given** el servidor rechaza un voto o búsqueda por límite, **When** el participante mira el contador, **Then** el tiempo restante mostrado es el mismo que usaría el servidor para aceptar la siguiente acción al expirar la ventana.
4. **Given** la ventana de reinicio se inició al primer consumo con cupo completo, **When** el participante consume más unidades antes de que expire, **Then** el contador sigue apuntando al mismo instante de recuperación del cupo completo (no se reinicia la ventana con cada consumo adicional).

---

### Edge Cases

- Participante con cupo completo que nunca consume: contador siempre oculto para ese límite.
- Participante que consume, espera a recuperar el cupo completo y vuelve a consumir: nueva ventana solo al **siguiente** primer consumo estando otra vez al cupo máximo.
- Reloj del dispositivo desincronizado: el valor mostrado se corrige en la siguiente sincronización con el servidor (al cargar estado, tras votar/buscar o en actualizaciones en vivo).
- Pestaña en segundo plano: al volver, el contador refleja el tiempo real restante, no el tiempo “congelado”.
- Al llegar a `00:00`, el cliente DEBE refrescar el estado del participante automáticamente (sin recarga manual) para ocultar el contador y mostrar el cupo restaurado.
- Límite configurado a 1 voto o 1 búsqueda: contador se comporta igual (aparece tras el primer y único consumo de la ventana).
- Búsqueda rechazada por consulta inválida o error de red: no debe consumir cupo ni iniciar/mostrar contador de búsquedas.
- Voto rechazado por canción no votable: no debe consumir cupo ni afectar el contador.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE calcular el instante de recuperación del cupo **completo** de votos a partir de una ventana temporal que **inicia** cuando el participante realiza su **primer voto** estando al cupo máximo; consumos adicionales dentro de esa ventana NO reinician el periodo.
- **FR-002**: El sistema DEBE calcular el instante de recuperación del cupo **completo** de búsquedas con la misma regla: ventana iniciada en la **primera búsqueda** con cupo completo; búsquedas adicionales en la misma ventana no reinician el periodo.
- **FR-003**: La duración de la ventana de reinicio DEBE ser la ya vigente para el evento (actualmente 10 minutos por límite), configurable por despliegue sin cambiar esta especificación.
- **FR-004**: En `/participar`, el sistema DEBE mostrar un contador **minutos:segundos** (`MM:SS`) para votos desde el **primer voto consumido** en la ventana activa (incluso si aún quedan votos por usar), hasta que se recupere el cupo completo; entonces el contador desaparece. Ubicación: **cabecera**, junto al texto de cupo de votos existente.
- **FR-005**: En `/participar`, el sistema DEBE mostrar un contador **MM:SS** para búsquedas con la misma regla de visibilidad: desde la **primera búsqueda** de la ventana (incluso si aún quedan búsquedas por usar) hasta recuperar el cupo completo. Ubicación: **subsección «Buscar en YouTube»** dentro del panel Enviar canciones.
- **FR-006**: Cuando el participante está al cupo completo y no hay ventana activa para un límite, el sistema NO DEBE mostrar contador para ese límite.
- **FR-007**: El servidor DEBE ser la fuente de verdad del instante de fin de ventana; el cliente DEBE derivar la cuenta atrás a partir de esa información y actualizarla en tiempo real entre sincronizaciones.
- **FR-008**: Tras cada acción que consuma voto o búsqueda, y al cargar o refrescar el estado del participante, el sistema DEBE devolver la información necesaria para mostrar el contador sin que el usuario tenga que recargar manualmente.
- **FR-009**: Los mensajes de error existentes por límite agotado (votos y búsquedas) DEBEN permanecer coherentes con el contador visible (mismo momento de recuperación).
- **FR-010**: Pegar un enlace de YouTube sin usar la búsqueda NO DEBE iniciar ni afectar la ventana ni el contador de búsquedas.
- **FR-011**: Acciones que no consumen cupo (voto inválido, búsqueda inválida, error previo al registro del consumo) NO DEBEN mostrar ni alterar el contador.
- **FR-012**: Cuando la ventana de votos está activa, el texto de cabecera DEBE mostrar «X de Y votos disponibles · Cupo completo en MM:SS» (sustituyendo el genérico «cada 10 min»); sin ventana activa, solo «X de Y votos disponibles».
- **FR-013**: La subsección Buscar en YouTube DEBE mostrar **«X de Y búsquedas disponibles»** de forma persistente (simétrico a votos). Cuando la ventana de búsquedas está activa, añadir **«Cupo completo en MM:SS»** con la misma convención que votos; sin ventana activa, no mostrar contador ni mención genérica de 10 min.
- **FR-014**: Al llegar el contador a `00:00`, el cliente DEBE solicitar o aplicar automáticamente una actualización del estado del participante para restaurar el cupo visible y ocultar el contador, sin exigir recarga de página ni nueva acción del usuario.

### Key Entities

- **Ventana de límite (votos o búsquedas)**: Periodo fijo que comienza en el primer consumo con cupo completo y termina al recuperarse el cupo íntegro; asociada a un participante y a un tipo de límite.
- **Instante de recuperación**: Momento en el que el participante vuelve a tener el cupo máximo para ese límite; base del contador MM:SS.
- **Cupo restante**: Unidades disponibles ahora (votos o búsquedas); complementario al contador (p. ej. «1 de 2 votos» + contador cuando aplica).
- **Estado de límites del participante**: Conjunto expuesto al cliente con cupos máximos, restantes y, cuando corresponda, instante o segundos restantes hasta recuperación completa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En pruebas con usuarios, el 90 % puede indicar en menos de 5 segundos cuándo podrá volver a votar con cupo completo cuando el contador está visible.
- **SC-002**: En el 100 % de los casos con cupo completo sin consumo previo en la ventana, no se muestra contador de votos ni de búsquedas.
- **SC-003**: El momento en que el contador llega a cero y desaparece coincide con la primera acción permitida de recuperación del cupo completo en el servidor, con margen ≤ 2 segundos en condiciones normales de red.
- **SC-004**: Tras recargar la página con una ventana activa, el contador mostrado difiere del valor del servidor en ≤ 2 segundos.
- **SC-005**: Reducción perceptible de consultas del tipo «¿cuánto falta para votar?» durante eventos piloto (validación cualitativa con operadores).
- **SC-006**: Al expirar el contador (`00:00`), el cupo restaurado y la desaparición del contador ocurren en menos de 3 segundos sin intervención del usuario.

## Assumptions

- Se mantienen los topes y la duración de ventana de **016-participant-limits-ux** (votos y búsquedas por periodo de 10 minutos, valores configurables por despliegue).
- El contador se muestra en español, junto a la información de cupo ya existente: votos en **cabecera**, búsquedas en la **subsección Buscar en YouTube**.
- La sesión de participante actual (OAuth o dev) identifica de forma unívoca al usuario para aplicar ventanas.
- Las actualizaciones en vivo existentes del participante (p. ej. tras votar) se reutilizan para refrescar límites sin exigir nueva infraestructura de notificaciones.
- El límite de canciones pendientes queda fuera de alcance; solo votos y búsquedas siguen el patrón de contador.
- Si hoy la ventana en servidor es de tipo «deslizante» (rolling), esta feature **sustituye** esa semántica por ventana fija desde el primer consumo con cupo completo, alineada con lo pedido por negocio.
