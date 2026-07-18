---
id: 005-participant-voting
type: change
status: draft
modifies:
  - backend-api
  - app-core
depends_on:
  - 001-foundation-jukebox
  - 004-kiosk-display-queue
requires_contract_update: true
read_by_default: true
---

# Feature Specification: Participant Voting

**Feature Branch**: `005-participant-voting` (change id; git branch may differ, e.g. `002-participant-voting`, per `speckit.git.feature` sequential numbering — same convention as 004)

**Created**: 2026-07-18

**Status**: Implemented

**Input**: Votación de participantes en la cola: 2 votos por ventana rodante de 5 minutos, reordenar entradas `queued` por popularidad, UI de voto en `/participar`, y actualización en tiempo real en kiosk y móvil vía SSE.

## Clarifications

### Session 2026-07-18

- Q: ¿Google OAuth en este change? → A: No; change **006** entrega OAuth Google. En 005 se usa sesión de participante mínima (`jukebox_participant_session`) con bootstrap de desarrollo para pruebas hasta que exista OAuth.
- Q: ¿Qué canciones son votables? → A: Solo entradas en estado `queued`; la que está `playing` no recibe votos.
- Q: ¿Los 2 votos pueden ir a la misma canción? → A: Sí (baseline 001).
- Q: ¿Reordenación? → A: Tras cada voto válido, la cola `queued` se reordena por `vote_count DESC`, desempate `created_at ASC`; el display y `/participar` reflejan el nuevo orden vía SSE.
- Q: ¿Envío de canciones nuevas? → A: Fuera de alcance (006); en 005 el participante solo vota la cola visible/publicada.

## SDD Context

- Depends on: **004-kiosk-display-queue** (`queue_entries`, `vote_count`, SSE `revision`, display strip)
- Modifies contracts: `backend-api`, `app-core`
- Product rules from **001**: 2 votos / 5 min por participante; solo `queued` votable
- **006** sustituirá el bootstrap de participante de desarrollo por Google OAuth sin cambiar las reglas de voto

## Problem

Attendees can see the queue on the kiosk display but cannot influence playback order. The product promises democratic reordering by votes, yet `/participar` has no voting UI and the backend has no `votes` persistence or rate limits.

## Goals

- Participants cast up to 2 votes per rolling 5-minute window.
- Votes increment `vote_count` on `queued` entries and trigger queue reorder.
- Kiosk display and `/participar` update without manual refresh when votes change.
- Clear Spanish feedback when vote limits are exceeded or target is not votable.
- Automated tests for vote windows, limits, reorder, and SSE revision bumps.

## Non-Goals

- Google OAuth sign-in UI (006).
- Submitting new songs / `pending_review` (006).
- Web Push notifications (v1.1).
- Voting on `playing`, `pending_review`, or `played` entries.
- Operator/moderator vote controls.
- Changes to kiosk layout proportions (004).

## User Scenarios & Testing

> **Execution order**: US3 (participant session) is a prerequisite for US1–US4 even though listed below by product priority.

### User Story 1 — Cast votes on queued songs (Priority: P1)

As an authenticated participant on `/participar`, I see the current votable queue and can allocate my votes to reorder songs by popularity.

**Why this priority**: Core attendee value — influencing what plays next.

**Independent Test**: Dev participant session + seeded `queued` entries → vote twice (same or different songs) → counts increase; third vote within 5 minutes blocked with Spanish message.

**Acceptance Scenarios**:

1. **Given** a participant with 0 votes used in the current window and a `queued` entry, **When** I vote for it, **Then** its `vote_count` increases by 1 and the queue order may change.
2. **Given** I have used 2 votes in the last 5 minutes, **When** I try to vote again, **Then** I see a clear message that my vote limit is exhausted and no vote is recorded.
3. **Given** two `queued` entries where A has more votes than B, **When** I vote for B, **Then** B may move ahead of A if it overtakes A's count (tie-break by earlier `created_at` when equal).
4. **Given** a `playing` entry, **When** I view `/participar`, **Then** I cannot vote for it (no vote control shown).
5. **Given** I have 1 vote remaining, **When** I vote twice for the same song, **Then** both votes apply to that song (counts +2 total if both allowed).

---

### User Story 2 — Live updates on display and mobile (Priority: P1)

As an attendee at the event or on my phone, I see vote counts and queue order update within seconds after anyone votes.

**Why this priority**: Real-time feedback is essential for event engagement (product baseline **001**, real-time queue updates).

**Independent Test**: `/` and `/participar` open → participant votes → both surfaces update via SSE without reload.

**Acceptance Scenarios**:

1. **Given** the kiosk display is connected to SSE, **When** a participant votes, **Then** the queue strip reflects new counts/order within 5 seconds.
2. **Given** `/participar` is open, **When** another participant votes (or I vote in another tab), **Then** my queue list updates without manual refresh.
3. **Given** SSE disconnects on mobile, **When** the connection restores, **Then** I see consistent state matching the server.

---

### User Story 3 — Participant session for voting (Priority: P1)

As a developer or operator testing before OAuth ships, I can establish a participant session so voting flows are demonstrable end-to-end.

**Why this priority**: Voting requires `participant_id`; OAuth arrives in 006 but 005 must be testable independently.

**Independent Test**: Dev participant bootstrap creates session cookie → `/participar` shows vote UI; without session, user sees prompt to identify (placeholder until 006 OAuth button).

**Acceptance Scenarios**:

1. **Given** `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`, **When** I call the dev participant bootstrap endpoint, **Then** I receive `jukebox_participant_session` and can vote.
2. **Given** no participant session, **When** I open `/participar`, **Then** I see Spanish copy explaining that sign-in is required to vote (OAuth in 006), and vote actions are disabled.
3. **Given** a participant session, **When** I call vote API without operator cookie, **Then** requests succeed (participant auth separate from operator).

---

### User Story 4 — Vote visibility and fairness (Priority: P2)

As a participant, I understand how many votes I have left in the current window.

**Why this priority**: Reduces confusion and support burden at events.

**Independent Test**: UI shows "X de 2 votos disponibles" updating after each vote; resets after window elapses (test with clock fixture).

**Acceptance Scenarios**:

1. **Given** I have not voted, **When** I open `/participar`, **Then** I see 2 votes available in the current window.
2. **Given** I used 1 vote, **When** I return to `/participar`, **Then** I see 1 vote remaining until the 5-minute window rolls forward.

---

### Edge Cases

- Voto sobre entrada que dejó de ser `queued` (pasó a `playing` o se eliminó): rechazar con mensaje claro, sin corromper contadores.
- Empate en `vote_count`: orden por `created_at ASC` (más antigua primero entre empatadas).
- Ventana rodante: votos de hace más de 5 minutos no cuentan para el límite de 2.
- Participante sin sesión: API devuelve 401; UI no expone botones de voto activos.
- Cola vacía en `queued`: mensaje vacío amigable; sin errores.
- Voto concurrente de dos participantes: contadores y orden consistentes (sin votos perdidos).

## Requirements

### Functional Requirements

- **FR-001**: System MUST persist votes linked to `participant_id` and `queue_entry_id` with timestamp.
- **FR-002**: A participant MUST be limited to 2 votes per rolling 5-minute window (votes older than 5 minutes do not count toward the limit).
- **FR-003**: A participant MAY cast both votes in the window on the same `queued` entry.
- **FR-004**: Vote target MUST be a `queue_entry` in status `queued`; other statuses are rejected.
- **FR-005**: Each valid vote MUST increment `vote_count` on the target entry and recompute order among `queued` entries (`vote_count DESC`, `created_at ASC`).
- **FR-006**: Each valid vote MUST bump `jukebox_runtime.revision` and broadcast SSE to subscribers (display and `/participar`).
- **FR-007**: `/participar` MUST list votable queue entries with title, vote count, and vote action (when participant session present).
- **FR-008**: `/participar` MUST show remaining votes in the current window and Spanish errors for limit exceeded or invalid target.
- **FR-009**: Participant vote endpoints MUST require `jukebox_participant_session`, not operator session.
- **FR-010**: Dev-only participant bootstrap MUST be gated by `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` (default false) until 006 OAuth.
- **FR-011**: Operator endpoints from 004 MUST remain unchanged; participants cannot approve, skip, or moderate.
- **FR-012**: Active contracts MUST document participant vote API, session cookie, and `/participar` vote UI.

### Key Entities

- **`participant`**: Attendee identity (minimal row until 006 enriches with Google profile).
- **`vote`**: One vote event (participant, queue entry, timestamp).
- **`queue_entry`**: Existing; `vote_count` denormalized field updated on vote.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A participant can cast 2 votes and see updated counts on `/participar` in under 3 seconds per vote.
- **SC-002**: A third vote within 5 minutes is blocked 100% of the time with understandable Spanish feedback.
- **SC-003**: After votes change order, kiosk queue strip matches `/participar` ordering within 5 seconds without page reload.
- **SC-004**: Automated tests cover vote limits, reorder rules, invalid targets, and SSE revision on vote.
- **SC-005**: Without participant session, `/participar` shows no active vote controls (only sign-in prompt).

## Assumptions

- Single event per deployment.
- Spanish UI throughout.
- `participants` table introduced in 005 with minimal fields (`id`, `display_name` placeholder); 006 adds `google_sub`, email, avatar.
- Rolling window computed from `votes.created_at` (no separate window table required for v1).
- Display SSE from 004 is reused; `/participar` may subscribe to the same stream or a participant-scoped snapshot endpoint.
- Vote list on `/participar` shows the same ordering rules as the kiosk strip (may show more than `queue_visible_count` entries or match it — default: show all `queued`, scroll on mobile).

## Scope boundary vs downstream changes

| Topic | This change (005) | Later |
|-------|-------------------|-------|
| Vote API + limits + reorder | Yes | — |
| `/participar` vote UI | Yes | — |
| Dev participant session | Yes | Replaced by Google OAuth in 006 |
| Google OAuth sign-in | No | 006 |
| Submit songs | No | 006 |
| Notifications (`song.approved`, `song.up_next`) | No | 007+ |
| Web Push | No | v1.1 |
