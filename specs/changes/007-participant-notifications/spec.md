---
id: 007-participant-notifications
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
  - 004-kiosk-display-queue
  - 005-participant-voting
  - 006-participant-oauth-submit
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Participant In-App Notifications

**Feature Branch**: `004-participant-notifications` (git) | **Change id**: `007-participant-notifications` | **Date**: 2026-07-18

**Created**: 2026-07-18

**Status**: Implemented

**Input**: Notificaciones in-app en `/participar` cuando el moderador aprueba la canción del participante (`song.approved`) y cuando su canción queda literalmente próxima a sonar (`song.up_next`). Entrega en tiempo real con mensajes en español. Baseline producto 001 (v1 SSE + toast; Web Push en v1.1).

## Clarifications

### Session 2026-07-18 (defaults from product baseline 001)

- Q: ¿Qué canal de notificación en v1? → A: **Toast in-app** en `/participar` al recibir evento en tiempo real (baseline: v1 SSE + toast; **sin Web Push** en este cambio).
- Q: ¿Cuándo `song.up_next`? → A: Solo cuando la canción del participante queda **literalmente próxima** a reproducir (fin natural de la actual o skip del moderador), **no** al subir posiciones por votos.
- Q: ¿Quién recibe notificaciones? → A: Solo el participante **dueño** de la canción (`submitted_by_participant_id`); no notificar por canciones ajenas.
- Q: ¿Rechazo genera notificación? → A: **No** en v1; el estado **Rechazada** sigue visible en **Mis canciones** (006); toast solo para `approved` y `up_next`.
- Q: ¿Participante sin sesión o en otra pestaña? → A: Sin toast retroactivo; al volver a `/participar` autenticado, **solo** estado actual en Mis canciones / cola (**sin** banner resumen de eventos perdidos en 007).
- Q: ¿Cómo mostrar dos toasts seguidos? → A: **Cola secuencial** — un toast visible a la vez; al cerrar (o auto-dismiss), aparece el siguiente; ningún mensaje se pierde.
- Q: ¿Auto-dismiss de toasts? → A: **Sí, 8 segundos** por toast, con cierre manual siempre disponible; al auto-dismiss avanza la cola igual que al cerrar manualmente.
- Q: ¿Resumen al volver a `/participar`? → A: **No** en 007; solo listas actualizadas (Mis canciones / cola).
- Q: ¿Posición del toast? → A: **Parte inferior** de la pantalla (fixed bottom, zona segura); no cubrir de forma permanente votar/enviar.
- Q: ¿Evento duplicado (p. ej. reconexión SSE)? → A: **Suprimir duplicados** en la sesión de página: mismo `type` + `queue_entry_id` → como máximo **un** toast.

## SDD Context

- Depends on: **006-participant-oauth-submit** (participant identity, Mis canciones, submit attribution)
- Depends on: **004-kiosk-display-queue** (moderation approve, skip/advance, queue lifecycle)
- Depends on: **005-participant-voting** (SSE `/participar`, participant session)
- Modifies contracts: `backend-api`, `app-core`
- Product baseline **001** FR-P06: notifications on approve and up-next

## Problem

Participants who submit songs must watch **Mis canciones** or the votable queue to learn when a moderator approved their track or when it is about to play. At live events this causes missed moments and unnecessary screen checking. The product baseline promises timely in-app feedback for `song.approved` and `song.up_next`.

## Goals

- Participants see a clear **Spanish toast** when their submission is **approved** and enters the queue.
- Participants see a clear **Spanish toast** when **their** song is **next to play** (not merely higher in the queue).
- Notifications arrive in **near real time** while the participant is on `/participar` with an active session.
- Voting, Mis canciones, submit limits, and moderation flows from 004–006 remain unchanged.

## Non-Goals

- Web Push / service worker / permisos del navegador (v1.1).
- Email or SMS notifications.
- Notifications on **reject** (status UI in Mis canciones is enough for v1).
- Notifications for operator or kiosk display.
- Notifying when someone else's song is approved or up next.
- Toast when a song only **rises in queue order** due to votes (not `up_next`).
- Persistent notification inbox or history beyond the current page session.
- Catch-up banner or summary toast for events missed while away from `/participar` (lists reflect truth; no retroactive toast in 007).

## User Scenarios & Testing

### User Story 1 — My song was approved (Priority: P1)

As a participant on `/participar`, I receive an in-app notification when a moderator approves **my** submitted song so I know it entered the queue without staring at Mis canciones.

**Why this priority**: Core value of `song.approved`; closes the loop after submit (006).

**Independent Test**: **Backend** — approve emits SSE `song.approved` with owner `participant_id` (`pytest`). **E2E** — participant on `/participar` sees Spanish approval toast within 5s (US3 + quickstart Phase 1); Mis canciones shows **En cola**.

**Acceptance Scenarios**:

1. **Given** I am signed in and have a song in `pending_review`, **When** a moderator approves it, **Then** I see a toast indicating my song was approved (title or clear reference).
2. **Given** I am signed in, **When** a moderator approves **another** participant's song, **Then** I do **not** receive an approval toast.
3. **Given** I am signed in, **When** a moderator rejects my song, **Then** I do **not** receive an approval toast; Mis canciones shows **Rechazada**.
4. **Given** I am not signed in, **When** an approval occurs, **Then** no participant toast is shown (only sign-in prompt).

---

### User Story 2 — My song is up next (Priority: P1)

As a participant, I am notified when **my** queued song becomes the **next** track to play so I can pay attention before it starts.

**Why this priority**: Baseline `song.up_next`; high impact at events.

**Independent Test**: My song in `queued` → current track ends or moderator skips → my song is next → toast on `/participar` before playback starts.

**Acceptance Scenarios**:

1. **Given** my song is in `queued` and another song is `playing`, **When** the playing song ends naturally and mine is next, **Then** I see an up-next toast before or as playback transitions.
2. **Given** my song is in `queued`, **When** the moderator skips the current song and mine is next, **Then** I see an up-next toast.
3. **Given** my song is in `queued` but **not** literally next (another song still ahead), **When** vote reorder moves my song up, **Then** I do **not** receive an up-next toast until I am actually next.
4. **Given** the up-next song was submitted by another participant, **When** advance occurs, **Then** I do not receive an up-next toast.

---

### User Story 3 — Toast experience on mobile (Priority: P2)

As a participant on a phone, I can read and dismiss notifications without them blocking voting or submit actions.

**Why this priority**: `/participar` is primarily mobile via QR.

**Independent Test**: Trigger approval and up-next toasts on a narrow viewport → readable Spanish text, dismissible, vote/submit remain usable.

**Acceptance Scenarios**:

1. **Given** a toast is visible, **When** I dismiss it manually or **8 seconds** elapse, **Then** it disappears, does not reappear for the same event, and the next queued toast (if any) is shown.
2. **Given** two events occur in short succession, **When** both apply to me, **Then** toasts appear **one at a time in a queue** (dismiss or auto-dismiss reveals the next; no message dropped).
3. **Given** a toast is shown, **When** I vote or submit, **Then** core controls remain reachable (toast anchored **bottom** does not permanently cover primary actions).

---

### User Story 4 — No regression on existing flows (Priority: P1)

As a participant, voting, Mis canciones updates, and SSE queue refresh continue to work after notifications are added.

**Why this priority**: 005/006 regression guard.

**Independent Test**: OAuth session → vote → submit → SSE updates still work; notification layer does not break `votes_remaining` merge or submissions list refresh.

**Acceptance Scenarios**:

1. **Given** I am signed in, **When** I vote after receiving a toast, **Then** vote limits and queue order behave per 005.
2. **Given** SSE revision bumps, **When** Mis canciones or queue updates, **Then** lists refresh as in 006 without duplicate broken state.

---

### Edge Cases

- Aprobación mientras el participante no está en `/participar` → sin toast; al volver, estado correcto en Mis canciones **sin** resumen banner.
- Varias aprobaciones seguidas de canciones propias → un toast por evento distinto en **cola secuencial**, sin duplicar el mismo evento.
- `up_next` inmediatamente tras `approved` si la cola estaba vacía → ambos eventos en cola; mensajes distinguibles mostrados **uno tras otro** (no stack simultáneo).
- Canción propia en `playing` → no `up_next` toast (ya está sonando).
- Participante con dev-auth u OAuth → mismo comportamiento de notificación.
- Pérdida breve de conexión SSE → reconexión existente (005); toasts solo para eventos **nuevos** tras reconectar; **sin** re-toast del mismo `(type, queue_entry_id)` ya mostrado en la sesión.

## Requirements

### Functional Requirements

- **FR-001**: System MUST broadcast a `song.approved` notification (with owning `participant_id` in payload) when their `pending_review` entry transitions to `queued` via moderator approval; `/participar` shows toast only to the matching participant.
- **FR-002**: System MUST broadcast a `song.up_next` notification (with owning `participant_id` in payload) when their `queued` entry becomes the literal next track to play (after natural end of current or moderator skip/advance); `/participar` shows toast only to the matching participant.
- **FR-003**: Notifications MUST NOT be sent for entries where `submitted_by_participant_id` is null or does not match the target participant.
- **FR-004**: `/participar` MUST display participant notifications as **Spanish toasts** with song title or equivalent clear reference, anchored to the **bottom** of the viewport (safe area) without permanently obscuring vote or submit controls.
- **FR-005**: System MUST NOT send `song.up_next` when the song only changes position within `queued` due to voting reorder.
- **FR-006**: System MUST NOT send approval toasts on moderator **reject**.
- **FR-007**: Participants MUST be able to dismiss visible toasts manually at any time; each toast MUST also **auto-dismiss after 8 seconds**; when multiple events are pending, **only one toast is visible at a time** and subsequent toasts appear in **FIFO order** after dismiss or auto-dismiss.
- **FR-008**: Notification delivery MUST use the existing realtime channel available to authenticated participants on `/participar` (no separate polling requirement for v1); duplicate deliveries of the same `(type, queue_entry_id)` in one page session MUST NOT produce a second toast.
- **FR-009**: Voting, submit, Mis canciones, OAuth, and operator moderation from **004–006** MUST remain unchanged.
- **FR-010**: Active contracts MUST document notification event types, participant targeting rules, and toast UX on `/participar`.

### Key Entities

- **`notification_event`**: Ephemeral delivery unit with `type` (`song.approved` | `song.up_next`), `queue_entry_id`, `participant_id`, `title` on the SSE wire. No `timestamp` field in v1; no server persistence or inbox.
- **`queue_entry`**: Existing; `submitted_by_participant_id` determines notification ownership.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A participant on `/participar` sees an approval toast within **5 seconds** of moderator approve in typical LAN/Wi‑Fi conditions.
- **SC-002**: A participant sees an up-next toast before or within **3 seconds** of their song becoming next to play.
- **SC-003**: **0%** of approval/up-next toasts are shown to the wrong participant in automated tests: backend payload targets owner; frontend ignores events where `participant_id` ≠ current session.
- **SC-004**: **100%** of vote-only reorder events do **not** trigger `up_next` toasts (negative test coverage).
- **SC-005**: Participants complete a vote or submit action successfully while a toast is visible or within **2 seconds** after dismiss/auto-dismiss (no blocking regression).

## Assumptions

- Spanish UI throughout `/participar`.
- One event per distinct state transition; **dedupe** by `(notification type, queue_entry_id)` for the current `/participar` page session (reconnect-safe).
- Operator moderation and skip semantics remain as in 004.
- Web Push deferred to v1.1 per baseline 001.
- No email field usage for delivery in this change.

## Scope boundary vs downstream changes

| Topic | This change (007) | Later |
|-------|-------------------|-------|
| `song.approved` toast | Yes | — |
| `song.up_next` toast | Yes | — |
| In-app realtime delivery | Yes | — |
| Web Push | No | v1.1 |
| Reject toast | No | Optional later |
| Notification history/inbox | No | Optional later |
| Notification dedupe on reconnect | Yes | — |
| YouTube text search | No | v1.1 |
