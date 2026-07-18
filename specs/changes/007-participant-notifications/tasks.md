---
description: "Task list for 007-participant-notifications"
---

# Tasks: Participant In-App Notifications

**Input**: Design documents from `specs/changes/007-participant-notifications/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: Included — SC-003/SC-004 automated (backend + frontend filter/dedupe); SC-001/SC-002 timing via quickstart; SC-005 vote/submit with visible toast via quickstart Phase 4.

**Organization**: Tasks grouped by user story (US1–US4). US1/US2 deliver backend SSE emit; US3 delivers toast UX + client filter tests; US4 is regression.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Manifest + Contract Consolidation)

**Purpose**: Register change and merge contract deltas before code (Constitution II + IV)

- [x] T001 Register `007-participant-notifications` in `specs/manifest.yml` as `draft` with `active.change` and `context_pack` pointing to `specs/changes/007-participant-notifications/context-pack.md`
- [x] T002 Update `specs/contracts/backend-api/contract.md` from `specs/changes/007-participant-notifications/contracts/contract-deltas.md` (SSE `notification` event, `NotificationEventRead`, emit rules, broadcast + client filter)
- [x] T003 Update `specs/contracts/app-core/contract.md` from `specs/changes/007-participant-notifications/contracts/contract-deltas.md` (toast UX, Spanish copy, services)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: SSE notification wire format and emit helpers shared by US1 and US2

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `NotificationEventRead` to `backend/app/schemas.py` (`type`, `queue_entry_id`, `participant_id`, `title`; no `timestamp` on wire)
- [x] T005 Extend `backend/app/services/sse_hub.py` with `format_notification_event()` and `broadcast_notification()` (`event: notification`)
- [x] T006 Create `backend/app/services/notification_service.py` with `emit_song_approved(entry)` and `emit_song_up_next(entry)` (guard `submitted_by_participant_id`, call `broadcast_notification`)
- [x] T007 [P] Extend `backend/tests/conftest.py` with helper to parse `notification` events from SSE TestClient stream (non-blocking pattern per 005 `test_sse.py` lesson)

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — My Song Was Approved (Priority: P1)

**Goal**: Backend emits `song.approved` on moderator approve when `submitted_by_participant_id` is set. End-to-end Spanish toast validated in US3 + quickstart Phase 1.

**Independent Test (backend)**: `pytest` after approve → SSE `notification` with `type=song.approved`, `participant_id` = owner, correct `title`.

### Tests for User Story 1

- [x] T008 [US1] Add `backend/tests/test_notifications.py` covering `song.approved` on approve: payload `participant_id` equals `submitted_by_participant_id`; no emit when owner null; no emit on reject

### Implementation for User Story 1

- [x] T009 [US1] Call `emit_song_approved` from `backend/app/services/queue_service.py` `approve_entry` after successful commit
- [x] T010 [US1] Run `pytest backend/tests/test_notifications.py -k approved` and fix failures

**Checkpoint**: Backend emits `song.approved` correctly (toast UX in US3)

---

## Phase 4: User Story 2 — My Song Is Up Next (Priority: P1) 🎯 MVP backend

**Goal**: `song.up_next` when participant's song is literal next before `playing`; never on vote reorder or when already `playing`.

**Independent Test**: Owner song queued + other playing → skip → owner gets `song.up_next`; vote reorder alone does not emit; skip while owner's song already `playing` does not emit new `up_next`.

### Tests for User Story 2

- [x] T011 [US2] Extend `backend/tests/test_notifications.py` covering: `song.up_next` on `skip_or_advance` (moderator skip and idle-start paths); no `up_next` on vote reorder; no `up_next` when next entry has no owner; no `up_next` when participant's entry is already `playing` (edge case)

### Implementation for User Story 2

- [x] T012 [US2] Call `emit_song_up_next` from `backend/app/services/queue_service.py` `skip_or_advance` **before** promoting next `queued` entry to `playing` in **both** code paths (current `playing` → advance, and idle start when nothing is playing)
- [x] T013 [US2] Run `pytest backend/tests/test_notifications.py` and fix failures

**Checkpoint**: Both notification types emit from backend

---

## Phase 5: User Story 3 — Toast Experience on Mobile (Priority: P2)

**Goal**: Bottom Spanish toast FIFO queue, 8s auto-dismiss, manual dismiss, session dedupe, client `participant_id` filter on `/participar`.

**Independent Test**: Trigger approve + up_next → one toast at a time; non-owner events ignored; duplicate SSE delivery deduped; controls remain usable.

### Implementation for User Story 3

- [x] T014 [P] [US3] Add `NotificationEventRead` interface to `frontend/src/app/models/jukebox-state.ts` matching backend schema
- [x] T015 [US3] Create `frontend/src/app/services/notification-toast.service.ts` (FIFO queue, dedupe `type:queue_entry_id`, 8s auto-dismiss, manual dismiss, Spanish templates per `contracts/contract-deltas.md`)
- [x] T016 [P] [US3] Create `frontend/src/app/participate/notification-toast.component.ts`, `notification-toast.component.html`, and `notification-toast.component.css` (fixed bottom safe area, dismiss button)
- [x] T017 [US3] Extend `frontend/src/app/services/participant-state.service.ts` to listen for SSE `notification` events and forward to `NotificationToastService` only when `participant_id` matches current participant
- [x] T018 [US3] Mount `NotificationToastComponent` in `frontend/src/app/participate/participate.component.ts` and `frontend/src/app/participate/participate.component.html`; show toasts only when authenticated (no toast when signed out)

### Tests for User Story 3

- [x] T019 [US3] Add minimal Vitest setup in `frontend/package.json`, `frontend/vitest.config.ts`, and `frontend/tsconfig.spec.json`; create `frontend/src/app/services/notification-toast.service.spec.ts` covering FIFO, dedupe on duplicate `(type, queue_entry_id)` (reconnect-safe), and 8s auto-dismiss advancing queue
- [x] T020 [US3] Create `frontend/src/app/services/participant-state.service.spec.ts` covering `notification` listener: forwards to toast service when `participant_id` matches session; ignores when mismatch (SC-003 client filter)
- [x] T021 [US3] Run `npm --prefix frontend test` and `npm --prefix frontend run build` with zero errors

**Checkpoint**: US3 acceptance — toast UX live on `/participar` with automated client filter coverage

---

## Phase 6: User Story 4 — No Regression (Priority: P1)

**Goal**: Voting, Mis canciones SSE refresh, and kiosk display unchanged.

**Independent Test**: Vote + submit + SSE revision after notifications; `votes_remaining` merge preserved; display ignores `notification` events.

### Tests for User Story 4

- [x] T022 [US4] Extend `backend/tests/test_sse.py` confirming `state` events still work with notifications enabled; add note/test that stream may include `notification` lines without blocking reads
- [x] T023 [US4] Run `pytest backend/tests/test_votes.py backend/tests/test_participant_submit.py backend/tests/test_sse.py` regression subset

### Implementation for User Story 4

- [x] T024 [US4] Verify `frontend/src/app/services/display-state.service.ts` ignores unknown `notification` SSE events (continues `state` only); fix only if regression fails

**Checkpoint**: SC-004/SC-005 regression guard passes

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full validation and change closure

- [x] T025 Run full `pytest backend/tests` with zero failures
- [x] T026 Run `npm --prefix frontend test` and `npm --prefix frontend run build` with zero errors
- [x] T027 Execute manual validation per `specs/changes/007-participant-notifications/quickstart.md` including SC-001/SC-002 timing, SC-005 vote/submit with visible toast, reconnect dedupe, and playing no-up_next edge case
- [x] T028 Mark change `implemented` in `specs/manifest.yml` and clear or update `active.change`
- [x] T029 Update implementation validation in `specs/changes/007-participant-notifications/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2; sequential edits to `queue_service.py` after US1
- **Phase 5 (US3)**: Depends on Phase 3–4 for E2E; T014–T015 can start after T006 with mocked events
- **Phase 6 (US4)**: Depends on US1–US3
- **Phase 7 (Polish)**: Depends on US1–US4

### User Story Dependencies

| Story | Depends on | Independent test without other stories |
|-------|------------|----------------------------------------|
| US1 | Foundational | Yes — pytest approve → SSE payload |
| US2 | Foundational | Yes — pytest skip → up_next payload + negatives |
| US3 | US1 + US2 (E2E) | Partial — T019/T020 unit tests with mocks |
| US4 | US1–US3 | Yes — regression tests with notifications enabled |

### Parallel Opportunities

- **Phase 1**: T002 and T003 — different contract files
- **Phase 2**: T007 parallel with T004–T006 after T005 interface known
- **Phase 5**: T014, T016 parallel after T015 API defined; T019 parallel with T020 after T015/T017
- **Phase 6**: T022 parallel with T024

### Parallel Example: User Story 3

```bash
# After T015 (NotificationToastService):
Task T016: notification-toast.component.*
Task T019: notification-toast.service.spec.ts
Task T020: participant-state.service.spec.ts (after T017)
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3)

1. Complete Phase 1–2 (T001–T007)
2. Complete Phase 3 US1 (T008–T010)
3. Complete Phase 4 US2 (T011–T013)
4. Complete Phase 5 US3 (T014–T021) — visible toasts + client tests
5. **STOP and VALIDATE**: quickstart Phases 1–3
6. Complete US4 + Polish

### Incremental Delivery

1. Setup + Foundational → SSE notification wire ready
2. US1 → `song.approved` backend
3. US2 → `song.up_next` backend
4. US3 → toast UI + SC-003 client tests
5. US4 → regression
6. Polish → manifest closure

### Suggested MVP Scope

**T001–T021** (Setup + Foundational + US1 + US2 + US3).

---

## Notes

- No Alembic migration for 007
- Delivery model: server **broadcasts** `notification` on shared SSE stream; `/participar` **filters** by `participant_id` (research.md)
- Do not block SSE tests on blocking stream iteration (005 lesson)
- Kiosk `/` and operator clients ignore `notification` SSE events
- Spanish toast copy in `contracts/contract-deltas.md`
- Natural end of playback: kiosk `display-state.service.ts` calls `POST /api/queue/skip` → same `skip_or_advance` emit path as moderator skip
