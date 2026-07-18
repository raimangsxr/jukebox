---
description: "Task list for 004-kiosk-display-queue"
---

# Tasks: Kiosk Display, Queue and Moderation

**Input**: Design documents from `specs/changes/004-kiosk-display-queue/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: Included — spec SC-005 requires automated tests for queue transitions, moderation limits, and SSE revision broadcast.

**Organization**: Tasks grouped by user story (US1–US4) for independent implementation and validation. QR panel ships in US1 (US4 is acceptance-only).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Manifest + Contract Consolidation)

**Purpose**: Register change and merge contract deltas before code (Constitution II + IV)

- [x] T001 Register `004-kiosk-display-queue` in `specs/manifest.yml` as `draft` with `active.change` and `context_pack` (verify matches current manifest)
- [x] T002 Update `specs/contracts/backend-api/contract.md` from `specs/changes/004-kiosk-display-queue/contracts/contract-deltas.md` (state, SSE, queue endpoints, skip idle-start semantics, auth policy, persistence)
- [x] T003 Update `specs/contracts/app-core/contract.md` from `specs/changes/004-kiosk-display-queue/contracts/contract-deltas.md` (display layout 90/10, components, services, admin moderation controls)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend models, services, migration, and test fixtures

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `QueueEntry`, `JukeboxRuntime`, and `queue_entry_status` enum to `backend/app/models.py` per `data-model.md`
- [x] T005 [P] Add queue and state Pydantic schemas (`QueueEntryRead`, `StateResponse`, `PendingListResponse`, `RejectBody`) to `backend/app/schemas.py`
- [x] T006 Create Alembic migration `backend/alembic/versions/0003_queue_and_runtime.py`
- [x] T007 [P] Create `backend/app/services/youtube_meta.py` (YouTube id/url parse + oEmbed fetch with fallback title)
- [x] T008 Create `backend/app/services/queue_service.py` (approve, reject, skip/advance with idle-start, duplicate check, 100-cap, position recompute)
- [x] T009 Create `backend/app/services/state_service.py` (`build_state_response`, `bump_revision`, event_config subset)
- [x] T010 Extend `backend/app/bootstrap.py` with idempotent `ensure_jukebox_runtime()`
- [x] T011 [P] Add `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT` to `backend/app/config.py` (default false)
- [x] T012 Extend `backend/tests/conftest.py` with fixtures for `pending_review`, `queued`, and `playing` queue entries
- [x] T013 Update `backend/tests/test_auth_policy.py` asserting 004 canonical public routes (state/queue/SSE remain protected)

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — Kiosk Display with Real Layout (Priority: P1) 🎯 MVP

**Goal**: `/` shows functional 90/10 layout with YouTube player, QR panel, and queue strip driven by `GET /api/state` — no placeholder labels.

**Independent Test**: Authenticated embed session + seeded `playing`/`queued` entries → display renders player, QR, queue strip; layout ~10% strip height at 720px; empty/idle states when no playback.

### Tests for User Story 1

- [x] T014 [US1] Add `backend/tests/test_state.py` covering `GET /api/state` (auth required, revision, now_playing, ordered queue strip, queue_visible_count cap)

### Implementation for User Story 1

- [x] T015 [US1] Create `backend/app/routers/state.py` with `GET /api/state` using `state_service.build_state_response`
- [x] T016 [US1] Mount state router in `backend/app/main.py`
- [x] T017 [P] [US1] Create `frontend/src/app/services/display-state.service.ts` with initial `GET /api/state` load and `state$` observable
- [x] T018 [P] [US1] Create `frontend/src/app/display/youtube-player.component.ts` and `frontend/src/app/display/youtube-player.component.html` (IFrame API, idle state, plays `now_playing.youtube_video_id`)
- [x] T019 [P] [US1] Create `frontend/src/app/display/queue-strip.component.ts` and `frontend/src/app/display/queue-strip.component.html` (compact rows: title truncate, vote badge, optional thumbnail when `thumbnail_url` present)
- [x] T020 [P] [US1] Add QR dependency (`qrcode` or `angularx-qrcode`) to `frontend/package.json`
- [x] T021 [P] [US1] Create `frontend/src/app/display/qr-panel.component.ts` and `frontend/src/app/display/qr-panel.component.html` (QR to `origin + '/participar'`, event title/subtitle, Spanish instructions)
- [x] T022 [US1] Refactor `frontend/src/app/display/display.component.ts` and `frontend/src/app/display/display.component.html` to wire layout shell, `DisplayStateService`, player, QR panel, and queue strip (preserve 002 error panel)
- [x] T023 [US1] Update `frontend/src/app/display/display.component.css` for flex column 90/10, top grid 2fr/1fr, `--jukebox-app-height` from state
- [x] T024 [US1] Run `pytest backend/tests/test_state.py` and fix failures

**Checkpoint**: Kiosk display shows real player + QR + queue data; zero placeholder strings (SC-003)

---

## Phase 4: User Story 2 — Moderator Reviews Submissions (Priority: P1)

**Goal**: Moderator approves/rejects `pending_review` entries from `/admin`; **Iniciar reproducción** / **Saltar canción** advance playback; Spanish errors for cola llena/duplicado.

**Independent Test**: `dev-submit` or fixture → pending list in admin → approve → entry `queued`; reject → `rejected`; 100 queued blocks approve; **Iniciar reproducción** starts first `queued`; **Saltar** advances when `playing`.

### Tests for User Story 2

- [x] T025 [US2] Add `backend/tests/test_queue.py` covering pending list, approve, reject, skip-when-playing, idle-start-via-skip, duplicate block, queue-full 409, nothing-to-advance 409, dev-submit gating

### Implementation for User Story 2

- [x] T026 [US2] Create `backend/app/routers/queue.py` with `GET /api/queue/pending`, `POST /api/queue/{id}/approve`, `POST /api/queue/{id}/reject`, `POST /api/queue/skip` (idle-start + advance), conditional `POST /api/queue/dev-submit`
- [x] T027 [US2] Mount queue router in `backend/app/main.py` and wire `bump_revision` on state-changing operations
- [x] T028 [P] [US2] Create `frontend/src/app/services/queue-admin.service.ts` (pending, approve, reject, skip/advance API calls)
- [x] T029 [US2] Add **Moderación** section to `frontend/src/app/admin/admin.component.ts` and `frontend/src/app/admin/admin.component.html` (pending table, approve/reject, **Iniciar reproducción** when idle+queued, **Saltar canción** when playing, disabled when empty, YouTube preview `target="_blank"`, Spanish 409 messages)
- [x] T030 [US2] Run `pytest backend/tests/test_queue.py` and fix failures

**Checkpoint**: Full moderation workflow via API and admin UI; tokens + logout from 002 unchanged

---

## Phase 5: User Story 3 — Live Display Updates (Priority: P1)

**Goal**: Kiosk updates player and queue strip within seconds of moderation actions without page reload.

**Independent Test**: `/` open via embed token → moderator approves, starts playback, or skips in `/admin` → display updates via SSE without manual refresh.

### Tests for User Story 3

- [x] T031 [US3] Add `backend/tests/test_sse.py` covering `GET /api/events/stream` auth, initial state event, revision bump on approve/skip, vote_count change via test fixture, heartbeat

### Implementation for User Story 3

- [x] T032 [US3] Extend `backend/app/routers/state.py` with `GET /api/events/stream` (SSE subscriber registry, revision-filtered events, 30s heartbeat, `X-Accel-Buffering: no`)
- [x] T033 [US3] Extend `frontend/src/app/services/display-state.service.ts` with `EventSource` to `/api/events/stream` (credentials), reconnect backoff, merge into `state$`
- [x] T034 [US3] Wire `frontend/src/app/display/youtube-player.component.ts` `onEnded` to call `POST /api/queue/skip` via `DisplayStateService` (no-op safely if queue empty — handle 409 gracefully)
- [x] T035 [US3] Run `pytest backend/tests/test_sse.py` and fix failures

**Checkpoint**: End-to-end live kiosk — approve/start/skip/end-of-video reflected on display without reload

---

## Phase 6: User Story 4 — QR Drives Participation (Priority: P2)

**Goal**: Validate QR acceptance criteria (implementation delivered in US1 T020–T022).

**Independent Test**: Load `/` → scan QR or open encoded URL → lands on `/participar`; panel shows `event_config.name` and instructions.

- [x] T036 [US4] Verify QR acceptance per `specs/changes/004-kiosk-display-queue/quickstart.md` Phase 2 (no additional implementation unless US1 checkpoint failed)

**Checkpoint**: US4 acceptance confirmed — QR panel functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, regression, and change closure

- [x] T037 Run full `pytest backend/tests` including `test_auth_policy.py`, `test_state.py`, `test_queue.py`, `test_sse.py` with zero failures
- [x] T038 Run `npm --prefix frontend run build` with zero errors
- [x] T039 Execute manual validation per `specs/changes/004-kiosk-display-queue/quickstart.md` (layout SC-001, live update SC-002, moderation start/skip, QR, 002 display-error regression)
- [x] T040 Mark change `implemented` in `specs/manifest.yml` and clear or update `active.change`
- [x] T041 Update implementation validation in `specs/changes/004-kiosk-display-queue/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — MVP target (full layout including QR)
- **Phase 4 (US2)**: Depends on Phase 2 — can parallel US1 backend after T008–T009
- **Phase 5 (US3)**: Depends on Phase 3 + Phase 4 (state + revision bumps from moderation)
- **Phase 6 (US4)**: Depends on Phase 3 (verification only)
- **Phase 7 (Polish)**: Depends on US1–US4 completion

### User Story Dependencies

| Story | Depends on | Independent test without other stories |
|-------|------------|----------------------------------------|
| US1 | Foundational | Yes — `GET /api/state` + full display via DB fixtures |
| US2 | Foundational | Yes — queue API + admin moderation via dev-submit/fixtures |
| US3 | US1 display + US2 revision bumps | Yes — SSE test with approve/start/skip triggering events |
| US4 | US1 (implementation) | Yes — QR verification only |

### Parallel Opportunities

- **Phase 1**: T002 and T003 — different contract files
- **Phase 2**: T005, T007, T011 parallel with adjacent tasks where noted
- **Phase 3**: T017–T021 parallel after T016
- **Phase 4**: T028 parallel with T026 once router contract known

### Parallel Example: User Story 1

```bash
# After T016 (state router mounted):
Task T017: display-state.service.ts
Task T018: youtube-player.component.ts
Task T019: queue-strip.component.ts
Task T020: package.json QR dependency
Task T021: qr-panel.component.ts
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1–2 (T001–T013)
2. Complete Phase 3 (T014–T024)
3. **STOP and VALIDATE**: Kiosk shows real player + QR + queue strip from API; no placeholders
4. Demo display with seeded queue data

### Incremental Delivery

1. Setup + Foundational → backend queue/state ready
2. US1 → full snapshot display including QR (MVP kiosk visual)
3. US2 → moderation workflow with start/skip controls
4. US3 → live SSE updates (production-ready kiosk)
5. US4 → QR acceptance verification
6. Polish → regression + manifest closure

### Suggested MVP Scope

**T001–T024** (Setup + Foundational + US1).

---

## Notes

- Reference: amrn-bull `GET /api/state` + SSE patterns
- Preserve 002 display error UX on `/` (no `/login` redirect on kiosk failures)
- `POST /api/queue/skip`: advance when `playing`; **start** when idle + `queued`; 409 when idle + empty
- `POST /api/queue/dev-submit` only when `JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT=true`
- Spanish UI strings throughout admin moderation and idle states
- `/participar` remains placeholder page until change 006 — QR link is still valid
- `bull:config` / `bull:resize` deferred — see contract-deltas deferred section
- Post-analyze remediation applied 2026-07-18 (issues I1, I2, C2, U1–U3, C1, G1–G2, A1)
