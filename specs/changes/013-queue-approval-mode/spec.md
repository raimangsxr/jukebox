---
id: 013-queue-approval-mode
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 004-kiosk-display-queue
  - 006-participant-oauth-submit
  - 007-participant-notifications
  - 010-hardening-and-polish
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Selector de modo de cola (Moderado / Libre)

**Feature Branch**: `013-queue-approval-mode`

**Created**: 2026-07-30

**Status**: Implemented

**Input**: Añadir un selector de modo en el panel de administrador: modo Moderado (el administrador debe aprobar o denegar las canciones para que pasen a la cola) y modo Libre (cada canción enviada pasa directamente a la cola sin necesidad de ser aprobada).

## Clarifications

### Session 2026-07-30

- Q: ¿Debe existir un límite de envíos en modo Libre cuando no hay estado «pendiente de revisión»? → A: Aplicar el mismo tope numérico actual, contando las canciones `queued` del participante en Libre.
- Q: ¿Dónde ubicar el selector de modo en `/admin`? → A: Sección **Moderación**, arriba de la tabla de pendientes.
- Q: ¿Qué notificación recibe el participante al enviar en modo Libre? → A: Toast inmediato al enviar, mismo mensaje que «aprobada y en cola».
- Q: ¿Confirmación al cambiar de modo en `/admin`? → A: Diálogo de confirmación antes de guardar el cambio.
- Q: ¿Mostrar el modo activo en `/participar`? → A: Sin indicador visible; el participante deduce el modo por el comportamiento al enviar.

## SDD Context

- Depends on: **004-kiosk-display-queue** (cola, moderación, estados `pending_review` / `queued`), **006-participant-oauth-submit** (envío de participantes), **007-participant-notifications** (notificaciones al aprobar), **010-hardening-and-polish** (editor de evento y configuración persistente)
- Modifies contracts: `backend-api`, `app-core`
- Baseline actual: todas las canciones enviadas por participantes entran en `pending_review` y el operador debe aprobarlas o rechazarlas antes de que aparezcan en la cola reproducible

## Problem

En eventos con poca capacidad de moderación o alta confianza en los asistentes, obligar a aprobar cada canción ralentiza la experiencia y sobrecarga al operador. Hoy no existe forma de desactivar la moderación sin cambios manuales en base de datos o despliegue. Los operadores necesitan elegir por evento si quieren control total (Moderado) o flujo automático (Libre).

## Goals

- El operador puede elegir entre **Moderado** y **Libre** desde `/admin`.
- En **Moderado**, el comportamiento actual se mantiene: envíos → revisión pendiente → aprobación o rechazo → cola.
- En **Libre**, cada envío válido entra **directamente en la cola** sin pasar por revisión pendiente.
- El modo elegido **persiste** para el evento y se aplica de forma coherente a participantes, kiosk y panel de administración.
- Los participantes reciben **retroalimentación coherente** con el modo activo (p. ej. «en cola» de inmediato en Libre).

## Non-Goals

- Reglas distintas de votación, límites de duplicados o políticas de salto de canción (sin cambios salvo lo necesario para el nuevo modo).
- Moderación asistida, aprobación masiva o colas de revisión avanzadas.
- Modos adicionales (p. ej. «solo operador puede enviar», listas blancas/negras).
- Cambios en autenticación de operador o participante.
- Historial de cambios de modo o auditoría detallada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Elegir modo Moderado (Priority: P1)

Como operador en `/admin`, quiero activar el modo **Moderado** para que cada canción enviada por un participante requiera mi aprobación o denegación antes de entrar en la cola, manteniendo el control editorial del evento.

**Why this priority**: Es el comportamiento actual y el valor por defecto; debe seguir funcionando sin regresiones.

**Independent Test**: Activar Moderado → un participante envía una canción → la canción aparece en pendientes de revisión en admin y **no** en la cola del kiosk hasta aprobar.

**Acceptance Scenarios**:

1. **Given** el modo es **Moderado**, **When** un participante envía una canción válida, **Then** la canción queda en estado de revisión pendiente, visible en la sección de moderación de `/admin`, y **no** aparece en la cola reproducible del kiosk.
2. **Given** el modo es **Moderado** y hay una canción pendiente, **When** el operador la aprueba, **Then** pasa a la cola y el kiosk se actualiza en tiempo real.
3. **Given** el modo es **Moderado** y hay una canción pendiente, **When** el operador la rechaza, **Then** no entra en la cola y el participante ve el estado rechazado en «Mis canciones».
4. **Given** un operador no autenticado, **When** intenta cambiar el modo, **Then** se le deniega el acceso (misma protección que el resto de funciones de administración).

---

### User Story 2 — Elegir modo Libre (Priority: P1)

Como operador en `/admin`, quiero activar el modo **Libre** para que las canciones enviadas por participantes entren automáticamente en la cola sin esperar mi aprobación, agilizando eventos informales o de alta participación.

**Why this priority**: Es el nuevo valor principal del feature; sin Libre no se cumple el objetivo de negocio.

**Independent Test**: Activar Libre → participante envía canción → aparece en cola del kiosk sin intervención del operador; la tabla de pendientes no recibe nuevos envíos.

**Acceptance Scenarios**:

1. **Given** el modo es **Libre**, **When** un participante envía una canción válida, **Then** la canción entra **directamente** en la cola reproducible y el kiosk la muestra sin acción del operador.
2. **Given** el modo es **Libre**, **When** un participante envía una canción válida, **Then** en «Mis canciones» ve un estado acorde a «en cola» (no «pendiente de revisión») y recibe de inmediato el mismo toast que en Moderado al aprobar («ha sido aprobada y está en cola»).
3. **Given** el modo es **Libre**, **When** un participante envía una canción válida, **Then** **no** se crea una entrada nueva en la lista de revisión pendiente de `/admin`.
4. **Given** el modo es **Libre** y la canción entra en cola, **When** le toca reproducirse o recibe votos, **Then** se comporta igual que cualquier otra canción ya en cola (votación, notificación «próxima», etc.).
5. **Given** el modo es **Libre** y el participante ya tiene el máximo de canciones `queued` permitido (mismo tope numérico que las pendientes en Moderado), **When** intenta enviar otra, **Then** el envío se rechaza con un mensaje claro de límite alcanzado.

---

### User Story 3 — Cambiar de modo durante el evento (Priority: P2)

Como operador, quiero poder cambiar entre Moderado y Libre durante el evento para adaptarme al ambiente, sin perder canciones ya en cola ni en reproducción.

**Why this priority**: Flexibilidad operativa real; secundario respecto a que cada modo funcione correctamente.

**Independent Test**: Con canciones en cola y pendientes, cambiar modo → verificar que cola/reproducción no se alteran y que solo los **nuevos** envíos siguen la regla del modo activo.

**Acceptance Scenarios**:

1. **Given** hay canciones en cola o reproduciéndose, **When** cambio el modo, **Then** las canciones ya en cola o en reproducción **no** se eliminan ni cambian de posición.
2. **Given** hay canciones en revisión pendiente y cambio de **Moderado** a **Libre**, **When** reviso `/admin`, **Then** las pendientes existentes **siguen** visibles hasta que las apruebe o rechace manualmente; los **nuevos** envíos van directo a cola.
3. **Given** el modo es **Libre** y cambio a **Moderado**, **When** un participante envía una canción, **Then** vuelve al flujo de revisión pendiente.
4. **Given** cambio el modo, **When** guardo la selección tras confirmar en el diálogo, **Then** el cambio se refleja en tiempo real para participantes y kiosk conectados (sin recargar manualmente la página).

---

### User Story 4 — Selector visible en el panel de administración (Priority: P2)

Como operador, quiero ver claramente qué modo está activo y poder cambiarlo con una acción simple, para no confundirme durante el evento.

**Why this priority**: UX del control; el backend puede funcionar sin UI clara, pero el operador no podría usar la función.

**Independent Test**: Abrir `/admin` → localizar selector → cambiar modo → ver confirmación visual del modo activo y persistencia tras recargar.

**Acceptance Scenarios**:

1. **Given** estoy en `/admin` autenticado, **When** abro el panel, **Then** veo en la sección **Moderación** (arriba de la tabla de pendientes) un control que muestra el modo actual (**Moderado** o **Libre**) y permite cambiarlo.
2. **Given** selecciono un modo distinto, **When** confirmo el cambio en el diálogo de confirmación, **Then** el modo activo mostrado coincide con el guardado y persiste tras recargar `/admin`.
3. **Given** el modo es **Libre**, **When** miro la sección de moderación, **Then** veo un mensaje claro de que los nuevos envíos no requieren revisión (la sección puede mostrar pendientes heredadas si las hay).
4. **Given** el modo es **Moderado**, **When** miro la sección de moderación, **Then** el flujo de aprobar/rechazar permanece disponible como hoy.

---

### Edge Cases

- Envío duplicado (mismo vídeo ya en cola o pendiente): se rechaza con el mismo mensaje que hoy, independientemente del modo.
- Cambio de modo con participantes enviando simultáneamente: cada envío sigue la regla del modo **vigente en el momento del envío**.
- Modo por defecto en instalación nueva o tras despliegue: **Moderado** (comportamiento actual).
- En **Libre**, el tope numérico de envíos por participante cuenta las canciones en estado `queued` (no `pending_review`); al alcanzar el límite, el envío se rechaza igual que en Moderado.
- En **Moderado**, el tope sigue contando solo entradas `pending_review` (comportamiento actual).
- Operador rechaza una pendiente heredada tras pasar a Libre: el rechazo funciona igual que en Moderado.
- Operador cancela el diálogo de confirmación al cambiar modo: el modo activo permanece sin cambios.
- Kiosk y `/participar` sin sesión de operador: solo **leen** el modo indirectamente a través del comportamiento de envío y estados; no pueden cambiarlo ni ven un indicador explícito del modo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE ofrecer dos modos de cola: **Moderado** y **Libre**.
- **FR-002**: El modo por defecto DEBE ser **Moderado**.
- **FR-003**: Solo operadores autenticados DEBEN poder consultar y cambiar el modo activo.
- **FR-004**: El modo activo DEBE persistir entre reinicios del servicio y recargas de página.
- **FR-005**: En modo **Moderado**, cada envío válido de participante DEBE crear una entrada en revisión pendiente y NO DEBE entrar en la cola hasta aprobación explícita del operador.
- **FR-006**: En modo **Libre**, cada envío válido de participante DEBE entrar directamente en la cola reproducible sin pasar por revisión pendiente.
- **FR-007**: En modo **Libre**, los envíos nuevos NO DEBEN aparecer en la lista de revisión pendiente de `/admin`.
- **FR-008**: Aprobar y rechazar DEBEN seguir disponibles para entradas que ya estén en revisión pendiente, independientemente del modo actual.
- **FR-009**: Cambiar el modo NO DEBE eliminar, reordenar ni alterar canciones ya en cola o en reproducción.
- **FR-010**: Cambiar el modo NO DEBE auto-aprobar ni auto-rechazar entradas ya en revisión pendiente; solo afecta a envíos **posteriores** al cambio.
- **FR-011**: El panel `/admin` DEBE mostrar el modo activo y permitir cambiarlo en la sección **Moderación** (arriba de la tabla de pendientes), con etiquetas en español (**Moderado** / **Libre**).
- **FR-012**: En modo **Libre**, la sección de moderación DEBE indicar que los nuevos envíos no requieren revisión.
- **FR-013**: Los participantes DEBEN ver en «Mis canciones» un estado coherente con el modo (p. ej. «en cola» de inmediato en Libre; «pendiente de revisión» en Moderado).
- **FR-014**: Las actualizaciones de cola y estados DEBEN propagarse en tiempo real a kiosk, `/participar` y `/admin` tras un envío o cambio de modo, sin recarga manual.
- **FR-015**: Las reglas existentes de vídeo duplicado DEBEN aplicarse en ambos modos.
- **FR-016**: En modo **Libre**, al enviar una canción válida el participante DEBE recibir de inmediato el mismo toast de aprobación que en Moderado («ha sido aprobada y está en cola») y la entrada DEBE figurar como «en cola» en «Mis canciones»; en Moderado, el toast solo aparece tras aprobación explícita del operador.
- **FR-017**: En modo **Libre**, el sistema DEBE aplicar el mismo tope numérico de envíos por participante que en Moderado, contando las canciones en estado `queued` del participante; al superar el tope, el envío DEBE rechazarse con mensaje de límite alcanzado (misma semántica que el límite de pendientes hoy).
- **FR-018**: En modo **Moderado**, el tope por participante DEBE seguir contando solo entradas `pending_review` (sin cambio respecto al comportamiento actual).
- **FR-019**: Al seleccionar un modo distinto en `/admin`, el sistema DEBE mostrar un diálogo de confirmación antes de persistir el cambio; cancelar DEBE dejar el modo anterior sin cambios.
- **FR-020**: `/participar` NO DEBE mostrar un indicador explícito del modo activo; el participante conoce el modo únicamente por el comportamiento al enviar (pendiente de revisión vs. en cola inmediata).

### Key Entities

- **Modo de cola**: Configuración del evento con valor `moderado` o `libre`; determina si los envíos requieren aprobación antes de la cola.
- **Entrada de cola**: Canción enviada; puede estar en revisión pendiente, en cola, reproduciéndose, reproducida o rechazada según el ciclo de vida existente.
- **Operador**: Usuario con sesión de administración que configura el modo y modera en Moderado.
- **Participante**: Usuario que envía canciones; experimenta el flujo según el modo activo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un operador puede identificar y cambiar el modo activo en `/admin` en menos de 30 segundos, sin documentación externa.
- **SC-002**: En modo **Libre**, el 100 % de los envíos válidos aparecen en la cola del kiosk en menos de 5 segundos desde el envío, sin intervención del operador.
- **SC-003**: En modo **Moderado**, el 100 % de los envíos válidos permanecen fuera de la cola hasta una acción explícita de aprobar o rechazar.
- **SC-004**: Tras cambiar el modo, los clientes conectados (kiosk, participante, admin) reflejan el comportamiento correcto en el siguiente envío sin recargar la página.
- **SC-005**: Cero regresiones en flujos existentes de votación, reproducción, salto de canción y notificaciones en modo **Moderado** (paridad con el comportamiento actual).
- **SC-006**: El 95 % de los operadores de prueba interpretan correctamente qué modo está activo tras ver el selector (prueba de usabilidad con al menos 5 usuarios o revisión guiada documentada).

## Assumptions

- El modo es **único por evento** (configuración singleton del evento actual), no por operador ni por participante.
- **Moderado** es el valor por defecto para preservar el comportamiento actual en despliegues existentes.
- El selector se ubica en la sección **Moderación** de `/admin`, arriba de la tabla de pendientes, con etiquetas en español.
- En **Libre**, el tope numérico existente se reutiliza contando canciones `queued` del participante; no se introduce un tope configurable distinto ni nuevo en este change.
- Las entradas en revisión pendiente al cambiar a **Libre** permanecen hasta decisión manual del operador (no se auto-aprueban).
- En **Libre**, el toast de aprobación se muestra al enviar (mismo texto que en Moderado tras aprobar); la notificación «próxima en cola» sigue el flujo existente cuando corresponda.
- `/participar` no muestra indicador del modo activo; no se añade banner ni badge informativo en este change.
