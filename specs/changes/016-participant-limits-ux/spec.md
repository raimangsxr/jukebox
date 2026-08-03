---
id: 016-participant-limits-ux
type: change
status: draft
modifies:
  - backend-api
  - app-core
  - ops-platform
depends_on:
  - 005-participant-voting
  - 006-participant-oauth-submit
  - 008-youtube-text-search
  - 010-hardening-and-polish
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Indicador de conexión, admin móvil y normas de participación

**Feature Branch**: `016-participant-limits-ux`

**Created**: 2026-08-03

**Status**: Draft (implementation complete; pending manual quickstart sign-off)

**Input**: Corregir el indicador de conexión en vivo (esquina superior derecha) que se queda bloqueado mostrando «Reconectando…» y «Modo respaldo»; evitar scroll horizontal en moderación `/admin` en móvil; mostrar claramente las limitaciones del participante tras el primer login (antes de usar `/participar`) usando límites configurables por el operador vía variables de entorno.

## SDD Context

- Depends on: **005** (votación y límites de votos), **006** (OAuth y envío), **008** (búsqueda YouTube y rate limit), **010** (SSE, endurecimiento, editor de evento)
- Modifies contracts: `backend-api`, `app-core`, `ops-platform`
- Baseline: SSE en kiosk, admin y participante sin indicador de estado fiable; moderación en tabla ancha; participante entra directo a votar/enviar sin pantalla de normas; límites de búsqueda y votos fijos en código

## Problem

1. **Conexión en vivo**: Los usuarios ven textos superpuestos o truncados («Modo respaldo: actuali…», «Reconectando…») que no cambian aunque la app siga funcionando o reconecte. Genera desconfianza durante el evento.
2. **Admin en móvil**: La tabla de moderación obliga a scroll horizontal; no se ven bien título, metadatos y botones de cada canción pendiente.
3. **Participantes**: No conocen sus límites (envíos, búsquedas, votos) hasta chocar con un error. El operador no puede ajustar búsquedas/votos sin desplegar código.

## Goals

- Indicador de conexión **claro, en español, sin solapamientos** en kiosk, admin y participante.
- Reconexión automática con **modo respaldo** (actualización periódica) cuando SSE falla; el indicador refleja el estado real.
- Moderación en `/admin` **usable en móvil** sin scroll horizontal.
- Tras el **primer login** de la sesión, pantalla de **normas de participación** con límites actuales; al aceptar, acceso completo a `/participar`.
- Límites configurables por despliegue: envíos pendientes, búsquedas por 10 minutos, votos por 10 minutos.

## Non-Goals

- Cambiar reglas de votación más allá de hacer configurables el tope y la ventana de 10 minutos.
- Historial de aceptación de normas en servidor o por participante persistente entre dispositivos.
- Indicador de conexión en `/login` del operador.
- Rediseño completo del panel admin fuera de la sección de moderación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Indicador de conexión fiable (Priority: P1)

Como operador, participante o espectador del kiosk, quiero saber si la app está conectada en tiempo real o actualizándose por respaldo, para confiar en lo que veo durante el evento.

**Why this priority**: El bug reportado bloquea la percepción de fiabilidad del sistema en vivo.

**Independent Test**: Simular caída de SSE → ver un solo mensaje de estado → restaurar SSE → el indicador desaparece o muestra conexión estable.

**Acceptance Scenarios**:

1. **Given** la app está conectada por SSE, **When** recibo actualizaciones normales, **Then** no veo mensajes de error ni textos superpuestos en la esquina superior derecha.
2. **Given** SSE se interrumpe brevemente, **When** el cliente reintenta, **Then** veo únicamente «Reconectando…» (un solo mensaje, texto completo, sin truncar).
3. **Given** SSE sigue fallando tras varios reintentos, **When** entra modo respaldo, **Then** veo únicamente «Modo respaldo» y la cola/estado sigue actualizándose periódicamente.
4. **Given** estaba en modo respaldo, **When** SSE se restablece, **Then** el indicador vuelve al estado conectado (sin mensaje) en menos de 30 segundos.
5. **Given** estoy en kiosk, admin o participante autenticado, **When** uso la app, **Then** el indicador usa la misma semántica de estados en las tres superficies.

---

### User Story 2 — Moderación admin en móvil (Priority: P1)

Como operador desde el móvil, quiero revisar cada canción pendiente con su información y botones Aprobar/Rechazar sin desplazarme horizontalmente.

**Why this priority**: La moderación en evento suele hacerse desde el teléfono.

**Independent Test**: Abrir `/admin` en viewport ≤ 390px con pendientes → toda la info y acciones visibles en vertical.

**Acceptance Scenarios**:

1. **Given** hay canciones pendientes y abro `/admin` en móvil, **When** reviso la sección Moderación, **Then** no necesito scroll horizontal para ver título, duración, autor, enlace de previsualización, motivo de rechazo y botones.
2. **Given** una entrada pendiente en móvil, **When** pulso Aprobar o Rechazar, **Then** la acción funciona igual que en escritorio.
3. **Given** abro `/admin` en escritorio, **When** reviso moderación, **Then** sigo pudiendo usar la vista tabular actual (o equivalente densa).

---

### User Story 3 — Normas de participación tras login (Priority: P1)

Como participante que acaba de iniciar sesión, quiero ver claramente mis límites antes de votar o enviar canciones, para entender las reglas del evento.

**Why this priority**: Reduce frustración y abusos; comunica límites operativos configurados por el organizador.

**Independent Test**: Login → pantalla de normas con tres límites → Aceptar → UI completa de `/participar`.

**Acceptance Scenarios**:

1. **Given** no he aceptado las normas en esta sesión de navegador, **When** completo login (Google o dev), **Then** veo una pantalla en español con los límites de: canciones en cola/pendientes, búsquedas cada 10 minutos y votos cada 10 minutos.
2. **Given** veo la pantalla de normas, **When** pulso aceptar («Entendido, participar» o equivalente), **Then** accedo a la experiencia completa de `/participar` (votar, buscar, enviar).
3. **Given** ya acepté las normas en esta sesión, **When** vuelvo a `/participar` sin cerrar el navegador, **Then** no veo de nuevo la pantalla de normas.
4. **Given** cierro pestaña o inicio sesión nueva, **When** vuelvo a autenticarme, **Then** debo ver de nuevo la pantalla de normas.
5. **Given** el operador cambió límites en el despliegue, **When** un participante nuevo ve las normas, **Then** los números mostrados coinciden con la configuración activa del servidor.

---

### User Story 4 — Límites configurables por despliegue (Priority: P2)

Como operador de infraestructura, quiero ajustar los topes de envíos, búsquedas y votos sin cambiar código, para adaptar el evento a distintos tamaños de audiencia.

**Why this priority**: Habilita la pantalla de normas con valores reales; hoy parte de los límites están fijos.

**Independent Test**: Cambiar variables de entorno → reiniciar backend → normas y rechazos reflejan nuevos valores.

**Acceptance Scenarios**:

1. **Given** variables de entorno configuradas para los tres límites, **When** el backend arranca, **Then** aplica esos valores al validar envíos, búsquedas y votos.
2. **Given** un participante autenticado, **When** consulta su estado, **Then** recibe los máximos configurados para mostrar en UI (envíos, búsquedas/10 min, votos/10 min).
3. **Given** valores por defecto sin override, **When** despliego, **Then** se usan: 2 envíos pendientes, 10 búsquedas/10 min, 2 votos/10 min (paridad razonable con el comportamiento previo).

---

### Edge Cases

- SSE cae y vuelve varias veces en pocos segundos: el indicador no acumula mensajes ni queda en «Reconectando» permanente si ya hay conexión.
- Participante acepta normas pero pierde sesión antes de enviar: al re-login ve normas de nuevo (nueva sesión de navegador).
- Admin con lista vacía de pendientes en móvil: mensaje vacío legible sin tabla rota.
- Límite de búsqueda alcanzado: mensaje existente en español; participante puede seguir pegando URL.
- Límite de votos alcanzado: mensaje en español coherente con el máximo mostrado en normas.
- Kiosk sin participante autenticado: indicador de conexión visible; sin pantalla de normas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar un indicador de estado de conexión en español en kiosk (`/`), admin (`/admin`) y participante autenticado (`/participar`).
- **FR-002**: En conexión SSE estable, el indicador NO DEBE mostrar mensajes de alerta (estado conectado implícito o discreto).
- **FR-003**: Durante reintentos SSE, el indicador DEBE mostrar exactamente un mensaje: «Reconectando…», sin solaparse con otros textos.
- **FR-004**: Si SSE no se restablece, el sistema DEBE pasar a modo respaldo con actualización periódica del estado y mostrar exactamente un mensaje: «Modo respaldo» (sin truncar).
- **FR-005**: Al restablecer SSE desde modo respaldo, el indicador DEBE volver al estado conectado y dejar de mostrar mensajes de alerta.
- **FR-006**: La sección de moderación en `/admin` DEBE ser usable en pantallas móviles sin scroll horizontal obligatorio para ver información y acciones de cada pendiente.
- **FR-007**: Tras autenticación de participante, si no ha aceptado normas en la sesión actual, el sistema DEBE mostrar pantalla de normas antes del resto de `/participar`.
- **FR-008**: La pantalla de normas DEBE listar en español: máximo de canciones pendientes/en cola, máximo de búsquedas por 10 minutos y máximo de votos por 10 minutos, con los valores vigentes del servidor.
- **FR-009**: Al aceptar las normas, el participante DEBE acceder a la UI completa de `/participar` en la misma ruta.
- **FR-010**: La aceptación de normas DEBE persistir solo durante la sesión del navegador (p. ej. almacenamiento de sesión); nueva sesión exige nueva aceptación.
- **FR-011**: El backend DEBE leer `JUKEBOX_MAX_PENDING_SUBMISSIONS_PER_PARTICIPANT`, `JUKEBOX_MAX_SEARCHS_10MINUTES_PER_PARTICIPANT` y `JUKEBOX_MAX_VOTES_10MINUTES_PER_PARTICIPANT` para aplicar y exponer límites.
- **FR-012**: La ventana rodante para búsquedas y votos DEBE ser de 10 minutos, alineada con el nombre de las variables de entorno.
- **FR-013**: Los mensajes de error al superar límites DEBEN seguir en español y ser coherentes con los máximos mostrados en normas.
- **FR-014**: Los cambios NO DEBEN romper SSE, votación, envío, moderación ni kiosk existentes.

### Key Entities

- **Estado de conexión en vivo**: `conectado` | `reconectando` | `respaldo` — refleja canal SSE vs actualización periódica.
- **Normas de participación**: Conjunto de tres límites numéricos mostrados al participante antes del uso.
- **Aceptación de normas**: Marca en sesión de navegador que desbloquea la UI de participación.
- **Límites de despliegue**: Configuración del operador vía variables de entorno para envíos, búsquedas y votos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En prueba de desconexión/reconexión SSE, el 100 % de las transiciones muestran un solo mensaje de estado, nunca dos superpuestos.
- **SC-002**: Ningún texto del indicador queda truncado en viewports de 320px–428px de ancho.
- **SC-003**: En móvil (≤ 390px), el 100 % de las entradas pendientes muestran título, metadatos y acciones sin scroll horizontal.
- **SC-004**: El 100 % de participantes nuevos en sesión ven la pantalla de normas antes de votar o enviar.
- **SC-005**: Los tres límites mostrados en normas coinciden con los valores devueltos por el servidor en el 100 % de los casos de prueba.
- **SC-006**: Tras aceptar normas, el participante accede a votar/enviar en menos de 2 segundos sin recargar manualmente.
- **SC-007**: Cero regresiones en flujos P1 de votación, envío, moderación y reproducción kiosk en suite de pruebas existente.

## Assumptions

- La ruta de participación sigue siendo `/participar` (no `/participant`).
- Aceptación de normas es por sesión de navegador, no persistida en base de datos.
- Valores por defecto: 2 envíos, 10 búsquedas/10 min, 2 votos/10 min si no hay override en entorno.
- El indicador en esquina superior derecha es suficiente; no se pide panel de diagnóstico detallado.
- En escritorio, la tabla de moderación puede mantenerse; en móvil se usa layout vertical (tarjetas).
