---
id: 004-kiosk-display-queue
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
  - 002-operator-auth-embed-tokens
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Kiosk Display, Queue and Moderation

**Feature Branch**: `004-kiosk-display-queue`

**Created**: 2026-07-18

**Status**: Implemented

**Input**: Sustituir los placeholders del display kiosk por componentes reales (reproductor, QR, cola con votos), ajustar el layout para que la franja de cola+votos ocupe ~10% de la altura, y entregar la API de cola con moderación para alimentar la pantalla en tiempo real.

## Clarifications

### Session 2026-07-18

- Q: ¿Proporción del panel de cola+votos? → A: ~10% de la altura visible del display; el 90% superior se reparte en reproductor (2/3 ancho) y QR+instrucciones (1/3 ancho).
- Q: ¿Sustituir el layout anterior de panel C a ancho completo? → A: Sí; la baseline de producto de 001 queda actualizada: la cola ya no es un panel inferior de ancho completo sino una franja compacta (~10% altura).
- Q: ¿Qué componentes dejan de ser placeholder en este change? → A: Reproductor de la canción en reproducción, QR hacia `/participar`, y lista de cola con contadores de votos en `/`.
- Q: ¿Envío y votación de participantes? → A: Fuera de alcance (changes 005–006); la cola se alimenta vía moderación y datos de prueba/seed para validación.
- Q: ¿Dónde modera el operador? → A: En `/admin`, sección de revisiones pendientes, con enlace de previsualización en YouTube en nueva pestaña (como en 001).

### Session 2026-07-18 (post-analyze remediation)

- Q: ¿Cómo arranca la primera reproducción si no hay `playing`? → A: `POST /api/queue/skip` es idempotente de inicio: si no hay `playing` pero sí hay entradas `queued`, promueve la primera por popularidad a `playing` (200). Solo devuelve 409 si no hay `playing` **y** la cola `queued` está vacía.
- Q: ¿QR en MVP/US1 o fase separada? → A: El panel QR se implementa junto con US1 (layout completo); US4 queda como criterio de aceptación/validación, no como fase de implementación separada.
- Q: ¿Botón skip en admin sin reproducción activa? → A: Mostrar **"Iniciar reproducción"** cuando hay `queued` y no hay `playing`; **"Saltar canción"** cuando hay `playing`; deshabilitado si no hay `queued` ni `playing`.
- Q: ¿`bull:config` / `bull:resize` en 004? → A: Diferido a change kiosk-screen dedicado; 004 solo aplica `--jukebox-app-height` desde `event_config.app_height_px`.

## SDD Context

- Depends on: **001-foundation-jukebox** (product baseline, `event_config`, data model), **002-operator-auth-embed-tokens** (operator session, embed token, display error UX)
- Modifies contracts: `backend-api`, `app-core`
- Reference: amrn-bull display + queue patterns; product rules from 001 (`queue_visible_count`, lifecycle, limits)
- Replaces placeholder display grid from 001 with functional kiosk UI

## Problem

After changes 001–003, the kiosk route `/` still shows placeholder text for the YouTube player, QR, and queue. Event attendees and operators cannot see a real jukebox experience on the display, and there is no queue persistence, moderation workflow, or live updates. The original 3-panel sketch allocated the full bottom row to the queue; operators want a compact queue strip (~10% height) so the player and participation QR dominate the screen.

## Goals

- Functional kiosk display at `/` with real components (not placeholder copy).
- Revised layout: **90% top** (player 2/3 + QR/instructions 1/3), **~10% bottom** (queue + vote counts).
- Backend queue model and moderation APIs so approved songs enter the playable queue.
- Live display updates when queue or now-playing changes (server-push to kiosk).
- Moderator UI in `/admin` to approve, reject, skip, and advance playback.
- Preserve existing embed-token and display-error behavior from 002.

## Non-Goals

- Participant Google OAuth and `/participar` submit/vote UI (changes 005–006).
- Web Push notifications (later change).
- YouTube text search (v1.1 per 001).
- kiosk-screen repo / `embed_app_family` wiring (later change).
- Multi-operator accounts, rate limiting, CSRF.
- Kubernetes manifest changes (003 already delivered).

## User Scenarios & Testing

### User Story 1 — Kiosk display with real layout (Priority: P1)

As an event attendee viewing the kiosk screen, I see the current YouTube video playing, a scannable QR to participate, and a compact strip showing upcoming songs with vote counts—without placeholder labels.

**Why this priority**: The display is the primary public surface; placeholders block any real event demo.

**Independent Test**: Open `/` with a valid embed session; verify player area, QR, and queue strip render real content (not "próximamente" / fraction labels). Layout uses ~10% height for the queue strip on a 720px-tall viewport.

**Acceptance Scenarios**:

1. **Given** an authenticated kiosk session and a song marked `playing`, **When** I open `/`, **Then** the player area shows that video and metadata (title).
2. **Given** queued entries exist, **When** I view the bottom strip, **Then** I see up to `queue_visible_count` entries (default 8) ordered by popularity, each with its vote count.
3. **Given** a standard kiosk height (e.g. 720px), **When** the layout renders, **Then** the queue strip occupies approximately 10% of vertical space and the top area ~90% split 2/3 player and 1/3 QR.
4. **Given** the display error state from 002 (invalid token or expired session), **When** an error is active, **Then** the error panel still replaces normal content; layout rules do not apply.

---

### User Story 2 — Moderator reviews submissions (Priority: P1)

As the event moderator, I open `/admin` and approve or reject songs waiting in `pending_review` before they enter the public queue.

**Why this priority**: No song may enter the queue without moderator approval (product rule FR-P02).

**Independent Test**: Seed a `pending_review` entry; moderator approves via `/admin`; entry moves to `queued`; **Iniciar reproducción** starts playback; entry appears on kiosk strip after refresh/SSE.

**Acceptance Scenarios**:

1. **Given** entries in `pending_review`, **When** I open the moderation section in `/admin`, **Then** I see title, submitter info (if available), and a control to open the YouTube preview in a new tab.
2. **Given** a `pending_review` entry and fewer than 100 `queued` songs, **When** I approve it, **Then** its status becomes `queued` with a position among queued entries.
3. **Given** a `pending_review` entry, **When** I reject it with an optional reason, **Then** its status becomes `rejected` and it does not appear on the display.
4. **Given** 100 songs already `queued`, **When** I try to approve another, **Then** approval is blocked with a clear Spanish message.

---

### User Story 3 — Live display updates (Priority: P1)

As a kiosk viewer, I see the queue strip and now-playing info update without manually refreshing when a moderator changes the queue or playback advances.

**Why this priority**: SSE is a product requirement (FR-P03) and essential for event use.

**Independent Test**: With `/` open, moderator approves a song or skips current track; display updates within a few seconds.

**Acceptance Scenarios**:

1. **Given** the kiosk display is open, **When** a moderator approves a new song, **Then** the queue strip updates to include it without a full page reload.
2. **Given** a song is `playing`, **When** the moderator skips to the next queued song, **Then** the player area and queue strip reflect the new now-playing and reordered queue.
3. **Given** vote counts change on queued entries (via future participant voting or test hooks), **When** the server broadcasts an update, **Then** the strip shows updated counts.

---

### User Story 4 — QR drives participation (Priority: P2)

As an attendee near the kiosk, I scan the QR code and land on `/participar` ready to join when participant flows ship in later changes.

**Why this priority**: QR is part of the display component set; full participation is deferred but the link must work. **Implementation ships with US1 layout**; this story tracks acceptance validation.

**Independent Test**: Scan or open QR URL; browser navigates to `/participar` on the same deployment origin.

**Acceptance Scenarios**:

1. **Given** the kiosk display is loaded, **When** I scan the QR, **Then** I reach `/participar` (placeholder participation page acceptable until change 006).
2. **Given** `event_config` name/subtitle, **When** I view the QR panel, **Then** I see brief Spanish instructions to scan and participate.

---

### Edge Cases

- Cola vacía: la franja inferior muestra estado vacío claro (sin errores); el reproductor puede mostrar pantalla de espera.
- Sin entrada `playing`: reproductor en estado idle con mensaje; la cola sigue visible si hay entradas `queued`.
- Duplicado activo: no se puede aprobar o encolar un `youtube_video_id` ya presente en `pending_review`, `queued` o `playing`.
- Token embed inválido o sesión caducada: comportamiento 002 sin cambios (mensaje estático, sin login en `/`).
- Desconexión SSE en kiosk: reintento automático; al reconectar, estado consistente con el servidor.
- Admin sin reproducción: botón **Iniciar reproducción** visible solo si hay `queued`; **Saltar** solo si hay `playing`; deshabilitado si cola vacía e idle.
- `POST /api/queue/skip` con cola vacía e idle: 409 `nothing to advance`.
- `queue_visible_count` configurable: el display nunca muestra más de N entradas en la franja, aunque haya más en cola.

## Requirements

### Functional Requirements

- **FR-001**: `/` MUST render a functional kiosk layout replacing placeholder text: player (~2/3 top width), QR panel (~1/3 top width), queue strip (~10% viewport height, full width).
- **FR-002**: The queue strip MUST list up to `queue_visible_count` entries in `queued` status, ordered by `vote_count` descending, tie-break `created_at` ascending.
- **FR-003**: Each queue strip row MUST show song title and vote count; optional thumbnail per design consistency with admin.
- **FR-004**: The player area MUST play the single `playing` entry via YouTube embed; when none, show an idle state in Spanish.
- **FR-005**: The QR panel MUST encode the deployment origin + `/participar` and show short Spanish participation instructions plus event title from `event_config`.
- **FR-006**: Backend MUST persist `queue_entries` and `jukebox_runtime` (now playing, revision) per 001 data model.
- **FR-007**: Moderator MUST approve/reject `pending_review` entries from `/admin`; approve transitions to `queued` respecting global limit 100.
- **FR-008**: Moderator MUST be able to advance playback via `POST /api/queue/skip`: (a) when `playing`, mark current as `played` and promote next `queued` by popularity; (b) when idle but `queued` entries exist, promote top `queued` to `playing` (start); (c) return 409 only when there is nothing `playing` and no `queued` entries.
- **FR-009**: Display MUST receive live updates via server-push (SSE) when queue, vote counts, or now-playing change.
- **FR-010**: Queue and moderation endpoints MUST require operator authentication (`jukebox_session`); public read of queue on display uses the embed-established session from 002.
- **FR-011**: Rejecting MUST set status `rejected` and optional `rejection_reason` (max 200 chars).
- **FR-012**: Preview in admin MUST open `https://www.youtube.com/watch?v={id}` in a new browser tab (not embedded in admin).
- **FR-013**: Active contracts and product baseline MUST document the revised display proportions (~10% queue strip, superseding 001 full-width panel C).

### Key Entities

- **`queue_entry`**: A submitted song with YouTube id, metadata, status lifecycle, vote count, and position among queued.
- **`jukebox_runtime`**: Singleton tracking `now_playing_entry_id` and monotonic `revision` for SSE.
- **`event_config`**: Existing singleton; `queue_visible_count` controls strip length.

## Success Criteria

### Measurable Outcomes

- **SC-001**: On a 720px-tall kiosk viewport, the queue strip height is between 8% and 12% of the visible app area in manual QA.
- **SC-002**: Moderator can approve a pending song and see it on the kiosk display within 5 seconds without manual browser refresh.
- **SC-003**: 100% of display areas (player, QR, queue strip) show real data or intentional empty/idle states—zero placeholder label strings from 001.
- **SC-004**: Approve/reject/skip flows complete with clear Spanish feedback; blocked approval at 100 queued shows an understandable message.
- **SC-005**: Automated tests cover queue state transitions (including idle-start via skip), moderation limits, and SSE revision broadcast; display integration validated manually per quickstart (Constitution V).

## Assumptions

- Single event per deployment; `event_config` id=1.
- Test and demo data can seed `pending_review` entries until participant submit ships in 006.
- Spanish UI copy throughout.
- `queue_visible_count` default remains 8 unless changed in `event_config`.
- Embed session from 002 is sufficient for display to call protected read/SSE endpoints.
- YouTube IFrame playback follows standard embed policies; autoplay with sound may require prior user gesture in non-kiosk browsers (kiosk iframe exempt per deployment).
- Participant voting API/UI deferred to 005; vote counts may be zero or test-seeded in 004.

## Scope boundary vs downstream changes

| Topic | This change (004) | Later |
|-------|-------------------|-------|
| Display layout + components | Yes | — |
| Queue persistence + moderation | Yes | — |
| SSE to kiosk | Yes | Participant SSE/toasts in 005+ |
| Participant submit + OAuth | Seed/test only | 006 |
| Participant voting | Test hooks only | 005 |
| Web Push | No | v1.1 |
| kiosk-screen embed family / `bull:config` listeners | No | dedicated change |
