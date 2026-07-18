---
id: 006-participant-oauth-submit
type: change
status: implemented
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
  - 004-kiosk-display-queue
  - 005-participant-voting
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Participant Google OAuth and Song Submit

**Feature Branch**: `006-participant-oauth-submit` (change id; git branch may differ, e.g. `003-participant-oauth-submit`, per `speckit.git.feature` numbering)

**Created**: 2026-07-18

**Status**: Draft

**Input**: Google OAuth en `/participar` para identificar asistentes, y envío de enlaces de YouTube a `pending_review` para moderación. Sustituye el flujo de desarrollo de 005 como experiencia principal de acceso público, manteniendo votación y SSE existentes.

## Clarifications

### Session 2026-07-18 (defaults from product baseline 001)

- Q: ¿Proveedor OAuth? → A: **Google únicamente** en `/participar` (baseline FR-P01).
- Q: ¿Qué puede enviar el participante? → A: Enlace o ID de YouTube (mismas reglas de parseo que moderación); búsqueda por texto queda fuera de alcance (v1.1).
- Q: ¿Límites de envío? → A: Máx. **2** entradas `pending_review` por participante; máx. **1** canción activa propia en `queued`+`playing` combinadas; sin duplicados de `youtube_video_id` en estados activos (`pending_review`, `queued`, `playing`).
- Q: ¿Qué pasa con el dev-auth de 005? → A: Permanece **solo para desarrollo/pruebas**, detrás de `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` (default false); la UI de producción muestra **Iniciar sesión con Google**.
- Q: ¿Cambian las reglas de voto? → A: No; 005 sigue vigente (2 votos / 5 min, solo `queued`).
- Q: ¿Idioma de errores API vs UI? → A: API devuelve `detail` en **inglés estable** (códigos programáticos); el frontend **traduce a español** en `/participar` (ver contract-deltas tabla de mapeo).

## SDD Context

- Depends on: **005-participant-voting** (`participants`, `jukebox_participant_session`, vote API, `/participar` vote UI, SSE)
- Depends on: **004-kiosk-display-queue** (`queue_entries`, moderation, `submitted_by_participant_id` column)
- Modifies contracts: `backend-api`, `app-core`
- Product baseline **001**: OAuth solo en `/participar`; moderación obligatoria antes de `queued`; límites por participante y cola global

## Problem

Attendees can vote on the queue but cannot sign in with their Google account or submit songs. The `/participar` page still relies on a dev-only bootstrap for identity, and there is no public path to add songs to `pending_review`. The product promise — scan QR, sign in, submit and vote — is incomplete.

## Goals

- Participants authenticate with Google on `/participar` and receive a stable participant session.
- Authenticated participants submit YouTube links that enter `pending_review` for operator approval.
- Participants see their submission status (pending, approved, rejected, playing, played) in Spanish.
- Voting and live SSE updates from 005 continue to work with OAuth-established sessions.
- Clear Spanish errors for limits, duplicates, and invalid YouTube references.

## Non-Goals

- Operator/moderator Google login (operator remains username/password on `/login`).
- YouTube text search (v1.1).
- Web Push or in-app notifications on approve/up-next (007+).
- Changes to vote limits, reorder rules, or kiosk display layout.
- Removing dev participant bootstrap (kept for tests behind env flag).
- Embed-token or kiosk iframe protocol changes.

## User Scenarios & Testing

### User Story 1 — Sign in with Google (Priority: P1)

As an attendee on `/participar`, I sign in with my Google account so the jukebox knows who I am for voting and submissions.

**Why this priority**: Identity is required for submit limits and attribution; replaces dev-only auth in production.

**Independent Test**: Open `/participar` → tap Google sign-in → return authenticated → session persists on refresh → can call participant APIs without dev bootstrap.

**Acceptance Scenarios**:

1. **Given** I am not signed in, **When** I open `/participar`, **Then** I see a prominent **Iniciar sesión con Google** action and voting/submit controls are disabled.
2. **Given** I complete Google sign-in successfully, **When** I return to `/participar`, **Then** I see my display name (and avatar when available) and can vote per 005 rules.
3. **Given** I already have a participant row from a prior event login with the same Google account, **When** I sign in again, **Then** the same participant identity is reused (`google_sub` stable).
4. **Given** Google sign-in fails or is cancelled, **When** I land back on `/participar`, **Then** I see a clear Spanish error and remain unauthenticated.
5. **Given** I am signed in as participant, **When** I use operator `/admin` in another tab, **Then** operator and participant sessions do not conflict (separate cookies).

---

### User Story 2 — Submit a YouTube song (Priority: P1)

As a signed-in participant, I paste a YouTube link so moderators can review and optionally add it to the queue.

**Why this priority**: Core attendee value alongside voting — contributing songs to the event.

**Independent Test**: OAuth session + valid YouTube URL → submit → entry appears in `pending_review` with my participant linked → moderator sees it in `/admin` pending list.

**Acceptance Scenarios**:

1. **Given** I am authenticated and under submit limits, **When** I submit a valid YouTube URL, **Then** a `pending_review` entry is created with title/thumbnail resolved and `submitted_by_participant_id` set.
2. **Given** I already have 2 entries in `pending_review`, **When** I try to submit another, **Then** I receive a clear Spanish message that my pending limit is reached and no new entry is created.
3. **Given** I already have a song in `queued` or `playing` that I submitted, **When** I try to submit another, **Then** I am blocked with a clear Spanish message (limit 1 active own song in queue/playback).
4. **Given** the same `youtube_video_id` is already active in the queue, **When** I submit it, **Then** I receive a duplicate error and no new entry is created.
5. **Given** I submit an invalid or unparseable YouTube reference, **When** the server validates it, **Then** I see a Spanish validation error and nothing is persisted.
6. **Given** I am not authenticated, **When** I attempt to submit, **Then** the action is unavailable or returns unauthorized without creating an entry.

---

### User Story 3 — View my submissions (Priority: P2)

As a participant, I see the status of songs I have submitted so I know whether they are waiting, in the queue, playing, or rejected.

**Why this priority**: Reduces confusion at events; pairs with submit flow.

**Independent Test**: Submit song → see `pending_review` in "Mis canciones" → after moderator approve/reject, status updates without full page reload (SSE or refresh).

**Acceptance Scenarios**:

1. **Given** I have submitted songs, **When** I open `/participar`, **Then** I see a **Mis canciones** list with title, status label in Spanish, and timestamp or position hint where relevant.
2. **Given** a moderator approves my submission, **When** state updates, **Then** my list shows the new status (`en cola` / `queued`) within seconds without manual refresh.
3. **Given** a moderator rejects my submission with a reason, **When** I view **Mis canciones**, **Then** I see `rechazada` and the reason when provided.
4. **Given** I have no submissions, **When** I view the section, **Then** I see a friendly empty state.

---

### User Story 4 — Vote after OAuth (Priority: P1)

As a Google-authenticated participant, I can still vote on the `queued` list exactly as in change 005.

**Why this priority**: Regression guard — OAuth must not break the voting MVP.

**Independent Test**: OAuth sign-in → vote twice on `queued` entries → limits and reorder behave per 005; third vote blocked.

**Acceptance Scenarios**:

1. **Given** I signed in with Google, **When** I vote on a `queued` entry, **Then** vote counts and order update as in 005.
2. **Given** I used 2 votes in the rolling window, **When** I try again, **Then** I see the same Spanish limit message as 005.
3. **Given** I am signed in, **When** another participant votes, **Then** my view updates via SSE without reload.

---

### Edge Cases

- OAuth callback con `state` inválido o CSRF fallido → rechazar con mensaje genérico, sin sesión.
- Cuenta Google sin email verificado o perfil mínimo → aceptar con `display_name` de Google; email almacenado si Google lo provee.
- Envío concurrente que supera límites → solo una petición gana; la otra recibe error de límite sin datos corruptos.
- Vídeo privado, eliminado o no embeddable → rechazo al enviar con mensaje comprensible (no `pending_review` silencioso).
- Participante con envío `pending_review` y moderador rechaza → el participante puede enviar otro si está bajo el límite de 2.
- Reenvío del mismo vídeo tras `played` → permitido si no hay duplicado activo.
- Cola global llena (100 `queued`) al aprobar → mensaje al moderador (004); el participante sigue viendo `pending_review` hasta aprobación.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow participants to authenticate via **Google OAuth** on `/participar` and establish `jukebox_participant_session`.
- **FR-002**: System MUST persist `google_sub` (unique), `email`, `display_name`, and optional `avatar_url` on the participant profile.
- **FR-003**: System MUST reuse an existing participant row when `google_sub` matches on subsequent logins.
- **FR-004**: Authenticated participants MUST be able to submit a YouTube URL or video id creating a `pending_review` `queue_entry` linked to their `participant_id`.
- **FR-005**: System MUST enforce max **2** `pending_review` entries per participant; further submits return a clear Spanish error.
- **FR-006**: System MUST enforce max **1** combined `queued`+`playing` entry per participant (submitted by them); further submits blocked with clear Spanish error.
- **FR-007**: System MUST block duplicate `youtube_video_id` in active statuses (`pending_review`, `queued`, `playing`) on participant submit.
- **FR-008**: `/participar` MUST show **Mis canciones** with submission status in Spanish for the authenticated participant.
- **FR-009**: Successful submit MUST bump realtime revision so kiosk and `/participar` reflect new pending state where applicable (moderation list / participant list).
- **FR-010**: Voting behavior from **005** MUST remain unchanged for OAuth-authenticated participants.
- **FR-011**: `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` dev bootstrap MUST remain available for tests (default false) and MUST NOT be the primary production UI.
- **FR-012**: Operator auth, moderation APIs, and embed-token kiosk flow from **002–004** MUST remain unchanged.
- **FR-013**: Active contracts MUST document OAuth routes, submit API, participant profile fields, and `/participar` submit UI.

### Key Entities

- **`participant`**: Extended with Google profile (`google_sub`, `email`, `avatar_url`); same session cookie as 005.
- **`queue_entry`**: Participant submit sets `submitted_by_participant_id`; lifecycle unchanged from 004.
- **`oauth_state`**: Short-lived CSRF/state for OAuth redirect (ephemeral; implementation detail deferred to plan).

## Success Criteria

### Measurable Outcomes

- **SC-001**: A participant can complete Google sign-in and see the vote/submit UI in under 30 seconds on a typical mobile connection.
- **SC-002**: A valid YouTube submit appears in moderator pending list and in **Mis canciones** within 3 seconds.
- **SC-003**: 100% of submit attempts over limits (2 pending, 1 active queued/playing, duplicate video) are rejected with understandable Spanish feedback.
- **SC-004**: After OAuth login, voting scenarios from 005 (2 votes, reorder, SSE) pass without regression.
- **SC-005**: Without Google sign-in, `/participar` offers no active vote or submit controls (only sign-in prompt).

## Assumptions

- Single Google Cloud OAuth client per deployment; secrets via `JUKEBOX_` env vars.
- Spanish UI throughout.
- YouTube metadata fetch uses same rules as operator dev-submit (004 oEmbed / parse).
- Participant submit does not auto-approve; moderator approval still required (baseline FR-P02).
- Email from Google is stored for support/display but not used for email notifications in this change.
- `/participar` remains public route without Angular operator guards.
- Bull sibling apps use similar OAuth redirect-to-backend-callback pattern; details in plan phase.

## Scope boundary vs downstream changes

| Topic | This change (006) | Later |
|-------|-------------------|-------|
| Google OAuth sign-in | Yes | — |
| YouTube link submit | Yes | — |
| Mis canciones status UI | Yes | — |
| Voting (005) | Unchanged | — |
| Dev participant bootstrap | Kept for tests | Optional removal later |
| Notifications (`song.approved`, up-next) | No | 007+ |
| YouTube text search | No | v1.1 |
| Web Push | No | v1.1 |
