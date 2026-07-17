---
id: 001-foundation-jukebox
type: change
status: implemented
modifies:
  - backend-api
  - app-core
  - ops-platform
requires_contract_update: true
read_by_default: true
---

# Feature Specification: amrn-jukebox Foundation

**Feature Branch**: `001-foundation-jukebox`

**Created**: 2026-07-17

**Status**: Implemented (001-foundation-jukebox, 2026-07-17)

**Input**: Collaborative YouTube jukebox for events, embedded in kiosk-screen as iframe, with moderated queue, participant voting, Google OAuth for public, separate operator login for moderation.

## Clarifications

### Session 2026-07-17 (brainstorming)

- Q: ¿Auth del moderador vs público? → A: Login separado usuario/contraseña para `/admin`; Google OAuth **solo** para `/participar`. Cookies distintas (`jukebox_session` vs `jukebox_participant_session`).
- Q: ¿Cuándo entra una canción en la cola? → A: Tras aprobación del moderador en `/admin`; antes queda en `pending_review`.
- Q: ¿Cómo previsualiza el moderador? → A: Botón abre `https://www.youtube.com/watch?v={id}` en nueva pestaña (no embebido en admin).
- Q: ¿Votos en la misma canción? → A: Sí, los 2 votos de la ventana pueden ir a la misma canción.
- Q: ¿Duplicados? → A: No en estados activos (`pending_review`, `queued`, `playing`); sí puede reenviarse tras `played`.
- Q: ¿Búsqueda por nombre? → A: v1 solo URL/ID; v1.1 YouTube Data API.
- Q: ¿Notificaciones? → A: v1 SSE + toast in-app; v1.1 Web Push.
- Q: ¿Cuándo `song.up_next`? → A: Al quedar literalmente próxima en reproducir (fin natural o skip del moderador), no al subir por votos.

## Scope of this change (001)

**In scope**: monorepo scaffold, SDD baseline, health API, placeholder Angular routes, compose/Docker/CI skeleton, active contracts documenting foundation + product baseline.

**Out of scope for 001** (deferred to changes 002+): OAuth, queue, voting, moderation workflows, YouTube player, SSE state, kiosk-screen repo changes.

## SDD Context

- Manifest entry: `specs/manifest.yml`
- Active contracts: `backend-api`, `app-core`, `ops-platform`
- Context pack: `context-pack.md`
- This change delivers the **monorepo scaffold** and locks the **product baseline** for subsequent changes.

## Product Summary

amrn-jukebox lets event attendees propose YouTube songs and vote to reorder the queue. A kiosk display shows the current video, participation QR, and live queue with vote counts. Moderators approve submissions before they enter the queue.

### Surfaces

| Route | Audience | Auth |
|-------|----------|------|
| `/` | Kiosk display | Embed token → operator session |
| `/participar` | Mobile attendees | Google OAuth |
| `/login` | Moderator | Username + password |
| `/admin` | Moderator | Operator session |

### Display layout (3 panels)

- **Panel A (2/3 width)**: YouTube player, now playing
- **Panel B (1/3 width)**: QR to `/participar`, participation instructions
- **Panel C (full width below)**: Queue (first N entries) + vote counts, SSE-updated

### Queue lifecycle

```text
submitted → pending_review → approved → queued → playing → played
                    ↘ rejected
```

- Songs enter `queued` only after moderator approval in `/admin`
- Moderator can open `https://www.youtube.com/watch?v={id}` in new tab from admin
- Voting: 2 votes per 5-minute rolling window per participant
- Reorder `queued` by `vote_count DESC`, tie-break `created_at ASC`
- `playing` entry is fixed; only `queued` entries are votable
- No duplicate active entries for same `youtube_video_id`
- Global `queued` limit: 100; per-user limits: 2 `pending_review`, 1 `queued`+`playing`

### Notifications (participant)

| Event | Trigger |
|-------|---------|
| `song.approved` | Moderator approves |
| `song.up_next` | Song becomes next to play (natural end or moderator skip) |

v1: in-app SSE + toast on `/participar`. v1.1: Web Push.

### YouTube input

- v1: URL, short URL, shorts URL, 11-char video ID
- v1.1: text search via YouTube Data API

### Kiosk embed

- `embed_app_family: amrn_jukebox` in kiosk-screen (separate change)
- Reuse `bull:resize`, `bull:ping`, `bull:config` protocol (CHG-042)
- Density precedence: embed override > `event_config.app_height_px` > 720

## User Scenarios & Testing

### User Story 1 — Monorepo scaffold (Priority: P1, this change)

As a developer, I can run backend tests, start compose, and build the Angular app with placeholder routes for display, participar, login, and admin.

**Independent Test**: `pytest backend/tests` passes; `npm run build` in frontend succeeds; `docker compose up` starts postgres, migrate, backend, frontend.

**Acceptance Scenarios**:

1. **Given** a fresh clone, **When** `pip install -e "backend[dev]" && pytest backend/tests`, **Then** health test passes.
2. **Given** frontend dependencies installed, **When** `npm run build`, **Then** production build completes.
3. **Given** `.env` with required secrets, **When** `docker compose up`, **Then** backend serves `GET /api/health` and frontend serves on port 4200.

---

### User Story 2 — Kiosk display (Priority: P1, future change)

Display shows 3-panel layout with YouTube player, QR, and live queue via SSE.

---

### User Story 3 — Participant submit + vote (Priority: P1, future change)

Authenticated Google user submits YouTube link and votes on queued songs.

---

### User Story 4 — Moderation (Priority: P1, future change)

Operator approves/rejects `pending_review` entries from `/admin` with YouTube preview link.

---

### User Story 5 — Notifications (Priority: P2, future change)

Participant receives in-app notifications on approve and up-next.

## Edge Cases

- Cola global llena (100 `queued`) al aprobar → bloquear aprobación hasta liberar hueco.
- Participante con 2 `pending_review` intenta otro envío → `429` con mensaje claro.
- Voto sobre canción `playing` o `pending_review` → `409`.
- Vídeo no embeddable o privado al enviar → rechazo con mensaje al participante.
- Display sin conexión SSE → mantener último frame y reconectar (patrón bull).
- Moderador y participante en el mismo navegador → cookies separadas sin conflicto.

## Functional Requirements

### This change (001)

- **FR-001**: Repository MUST provide `backend/` and `frontend/` monorepo layout aligned with amrn-bull.
- **FR-002**: Backend MUST expose unauthenticated `GET /api/health` returning `{"status":"ok"}`.
- **FR-003**: Frontend MUST register routes `/`, `/participar`, `/login`, `/admin` with placeholder views.
- **FR-004**: `specs/manifest.yml` and active contracts MUST exist before feature implementation changes.

### Product baseline (changes 002+, documented here)

- **FR-P01**: Separate operator login and participant Google OAuth.
- **FR-P02**: Moderator approval required before `queued`.
- **FR-P03**: SSE for display and participant updates.
- **FR-P04**: Kiosk embed tokens + `bull:config` density protocol.
- **FR-P05**: 2 votes / 5 min per participant; reorder by popularity.
- **FR-P06**: Notifications on approve and up-next.

## Success Criteria (this change)

- **SC-001**: Backend health endpoint returns 200 with CSP header.
- **SC-002**: Angular app builds with routes `/`, `/participar`, `/login`, `/admin`.
- **SC-003**: SDD manifest, contracts, checklist, plan, tasks, and analyze artifacts exist.
- **SC-004**: Specification quality checklist passes with no open `[NEEDS CLARIFICATION]` markers.

## Assumptions

- Single operator account per deployment (like amrn-bull).
- Spanish UI copy.
- PostgreSQL in compose and production; SQLite in unit tests.
