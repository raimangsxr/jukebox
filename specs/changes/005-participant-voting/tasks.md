---
description: "Task list for 005-participant-voting"
---

# Tasks: Participant Voting

**Input**: Design documents from `specs/changes/005-participant-voting/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: Included — spec SC-004 requires automated tests for vote limits, reorder rules, invalid targets, and SSE revision on vote.

**Organization**: Tasks grouped by user story (US1–US4) for independent implementation and validation. US3 (participant session) precedes US1 (voting); US2 (SSE) follows vote API; US4 is visibility polish + window roll-forward test.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Manifest + Contract Consolidation)

**Purpose**: Register change and merge contract deltas before code (Constitution II + IV)

- [x] T001 Register `005-participant-voting` in `specs/manifest.yml` as `draft` with `active.change` and `context_pack` pointing to `specs/changes/005-participant-voting/context-pack.md`
- [x] T002 Update `specs/contracts/backend-api/contract.md` from `specs/changes/005-participant-voting/contracts/contract-deltas.md` (participant session, vote endpoints, SSE dual-auth, dev-auth gating, persistence)
- [x] T003 Update `specs/contracts/app-core/contract.md` from `specs/changes/005-participant-voting/contracts/contract-deltas.md` (`/participar` vote UI, ParticipantService, ParticipantStateService, authInterceptor)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend models, participant session plumbing, vote service, migration, and test fixtures

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `Participant` and `Vote` models to `backend/app/models.py` per `data-model.md`
- [x] T005 [P] Add participant and vote Pydantic schemas (`ParticipantRead`, `ParticipantMeResponse`, `ParticipantStateResponse`, `VoteCreateRequest`, `VoteResponse`, `ParticipantDevAuthRequest`) to `backend/app/schemas.py`
- [x] T006 Create Alembic migration `backend/alembic/versions/0004_participants_and_votes.py` with index on `(participant_id, created_at)`
- [x] T007 Create `backend/app/services/participant_session.py` (signed `jukebox_participant_session` cookie via itsdangerous + `settings.session_secret` / env `JUKEBOX_SESSION_SECRET`)
- [x] T008 [P] Add `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH` to `backend/app/config.py` (default false)
- [x] T009 Add `get_current_participant` and `get_stream_subscriber` (operator **or** participant) to `backend/app/security.py`
- [x] T010 Create `backend/app/services/vote_service.py` (`count_votes_in_window`, `cast_vote` with limit check, `vote_count` increment, call `queue_service._recompute_positions`, `bump_revision`)
- [x] T011 [P] Extend `backend/tests/conftest.py` with fixtures for `participant`, `participant_session_cookie`, and multiple `queued` queue entries
- [x] T012 Update `backend/tests/test_auth_policy.py` asserting 005 canonical public routes (`POST /api/participant/dev-auth` when enabled remains public; vote/participant/me routes protected)

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 3 — Participant Session for Voting (Priority: P1)

**Goal**: Dev participant bootstrap creates `jukebox_participant_session`; `/participar` shows sign-in prompt without session and enables vote flow with session.

**Independent Test**: `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true` → `POST /api/participant/dev-auth` sets cookie → `GET /api/participant/me` returns participant; without session `/participar` shows Spanish sign-in copy and disabled vote actions.

### Tests for User Story 3

- [x] T013 [US3] Add `backend/tests/test_participant_auth.py` covering dev-auth gating, cookie set, `GET /api/participant/me` auth required, invalid cookie 401

### Implementation for User Story 3

- [x] T014 [US3] Create `backend/app/routers/participant.py` with conditional `POST /api/participant/dev-auth` and `GET /api/participant/me`
- [x] T015 [US3] Mount participant router in `backend/app/main.py`
- [x] T016 [P] [US3] Create `frontend/src/app/services/participant.service.ts` (`devAuth()`, `me()`, session state observable)
- [x] T017 [P] [US3] Update `frontend/src/app/auth.interceptor.ts` so 401 on `/api/participant/*` or `/api/votes` while on `/participar` does not navigate to `/login`
- [x] T018 [US3] Update `frontend/src/app/participate/participate.component.ts` and `frontend/src/app/participate/participate.component.html` with Spanish sign-in prompt (OAuth in 006), dev button "Entrar como participante (dev)", disabled vote area when unauthenticated
- [x] T019 [US3] Run `pytest backend/tests/test_participant_auth.py` and fix failures

**Checkpoint**: Participant session established end-to-end; `/participar` auth UX without OAuth

---

## Phase 4: User Story 1 — Cast Votes on Queued Songs (Priority: P1) 🎯 MVP

**Goal**: Authenticated participant votes on `queued` entries; counts increment; queue reorders; third vote within 5 minutes blocked with Spanish error.

**Independent Test**: Dev participant session + seeded `queued` entries → vote twice (same or different) → `vote_count` increases and order may change; third vote → 409 `vote limit exceeded`; vote on `playing` entry → 409 `entry not votable`.

### Tests for User Story 1

- [x] T020 [US1] Add `backend/tests/test_votes.py` covering cast vote success, same-entry double vote, limit exceeded, invalid target (`playing`/`pending_review`), stale target (entry promoted to `playing` before vote → 409 `entry not votable`), not found, reorder by vote_count, concurrent votes from two participants (consistent counts/order), participant session cannot call `POST /api/queue/skip` (401), operator cookie cannot vote without participant session

### Implementation for User Story 1

- [x] T021 [US1] Add `build_participant_state_response` to `backend/app/services/state_service.py` (all `queued` entries, `votes_remaining`, `now_playing`, `event_config`)
- [x] T022 [US1] Extend `backend/app/routers/participant.py` with `GET /api/participant/state`
- [x] T023 [US1] Create `backend/app/routers/votes.py` with `POST /api/votes` calling `vote_service.cast_vote`
- [x] T024 [US1] Mount votes router in `backend/app/main.py`
- [x] T025 [P] [US1] Create `frontend/src/app/services/participant-state.service.ts` with `GET /api/participant/state` bootstrap and `state$` observable (no SSE yet)
- [x] T026 [US1] Update `frontend/src/app/participate/participate.component.ts` and `frontend/src/app/participate/participate.component.html` with scrollable `queued` list, vote buttons, vote count badges, votes-remaining header "X de 2 votos disponibles" (FR-008), Spanish 409 errors (`vote limit exceeded`, `entry not votable`), empty queue state; no vote control for `now_playing`
- [x] T027 [US1] Run `pytest backend/tests/test_votes.py` and fix failures

**Checkpoint**: Core voting works via API and `/participar` UI; reorder and limits enforced

---

## Phase 5: User Story 2 — Live Updates on Display and Mobile (Priority: P1)

**Goal**: Kiosk queue strip and `/participar` update within seconds after any vote without page reload.

**Independent Test**: `/` (embed token) and `/participar` open → participant votes → both surfaces reflect new counts/order via SSE within 5 seconds.

### Tests for User Story 2

- [x] T028 [US2] Extend `backend/tests/test_sse.py` covering participant cookie auth on `GET /api/events/stream`, revision bump after `POST /api/votes`, operator SSE unchanged, reconnect delivers snapshot consistent with `GET /api/participant/state` after simulated disconnect

### Implementation for User Story 2

- [x] T029 [US2] Update `backend/app/routers/state.py` `events_stream` to use `get_stream_subscriber` instead of `CurrentUser` only (`GET /api/state` remains operator-only)
- [x] T030 [US2] Extend `frontend/src/app/services/participant-state.service.ts` with `EventSource` to `/api/events/stream` (credentials), reconnect backoff, merge queue/`now_playing`/`revision` from SSE into `state$` **without** overwriting `votes_remaining` (preserve from snapshot or last vote response per contract-deltas client merge rule)
- [x] T031 [US2] Wire `frontend/src/app/participate/participate.component.ts` to `ParticipantStateService` for live queue updates across tabs
- [x] T032 [US2] Run `pytest backend/tests/test_sse.py` and fix failures

**Checkpoint**: End-to-end live updates — vote on mobile updates kiosk strip without reload (SC-003)

---

## Phase 6: User Story 4 — Vote Visibility and Fairness (Priority: P2)

**Goal**: Participant sees how many votes remain in the current rolling window; count resets when window rolls forward.

**Independent Test**: UI shows "X de 2 votos disponibles" updating after each vote (delivered in US1 T026); pytest confirms limit resets when votes age past 5 minutes.

### Tests for User Story 4

- [x] T033 [US4] Extend `backend/tests/test_votes.py` with rolling-window expiry test (votes older than 5 minutes no longer count toward limit; third vote allowed after expiry)

### Implementation for User Story 4

- [x] T034 [US4] Verify US4 acceptance per `quickstart.md` Phase 4: votes-remaining badge updates after revisit to `/participar` and after window roll-forward (no additional UI unless T026 checkpoint failed)

**Checkpoint**: US4 acceptance — remaining votes visible, accurate, and window expiry verified

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, regression, and change closure

- [x] T035 Run full `pytest backend/tests` including `test_votes.py` (concurrent votes, stale target, participant cannot moderate), `test_participant_auth.py`, `test_sse.py` (reconnect consistency), `test_auth_policy.py`, and 004 regression (`test_queue.py`, `test_state.py`) with zero failures
- [x] T036 Run `npm --prefix frontend run build` with zero errors
- [x] T037 Execute manual validation per `specs/changes/005-participant-voting/quickstart.md` (vote flow, SC-001 latency ≤3s per vote, SSE cross-surface SC-003, SSE reconnect US2, operator moderation unchanged FR-011, 004 kiosk regression)
- [x] T038 Mark change `implemented` in `specs/manifest.yml` and clear or update `active.change`
- [x] T039 Update implementation validation in `specs/changes/005-participant-voting/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US3)**: Depends on Phase 2 — participant session required before voting
- **Phase 4 (US1)**: Depends on Phase 3 — MVP voting
- **Phase 5 (US2)**: Depends on Phase 4 — SSE needs vote-triggered `bump_revision`
- **Phase 6 (US4)**: Depends on Phase 4 — visibility builds on vote API responses
- **Phase 7 (Polish)**: Depends on US1–US4 completion

### User Story Dependencies

| Story | Depends on | Independent test without other stories |
|-------|------------|----------------------------------------|
| US3 | Foundational | Yes — dev-auth + me via curl; `/participar` sign-in UX |
| US1 | US3 | Yes — vote API + UI with participant session + queued fixtures |
| US2 | US1 | Yes — SSE revision bump on vote; kiosk updates with both surfaces open |
| US4 | US1 | Yes — votes_remaining display + window expiry pytest |

### Parallel Opportunities

- **Phase 1**: T002 and T003 — different contract files
- **Phase 2**: T005, T008, T011 parallel with adjacent tasks where noted
- **Phase 3**: T016 and T017 parallel after T015
- **Phase 4**: T025 parallel with T023–T024 once vote router contract known
- **Phase 5**: T030 parallel with T029 after T028 passes

### Parallel Example: User Story 3

```bash
# After T015 (participant router mounted):
Task T016: participant.service.ts
Task T017: auth.interceptor.ts
```

### Parallel Example: User Story 1

```bash
# After T024 (votes router mounted):
Task T025: participant-state.service.ts (bootstrap)
# Meanwhile T026 can proceed once T025 interface is defined
```

---

## Implementation Strategy

### MVP First (US1 + US2 + prerequisites)

1. Complete Phase 1–2 (T001–T012)
2. Complete Phase 3 US3 (T013–T019)
3. Complete Phase 4 US1 (T020–T027) — includes votes-remaining UI (FR-008)
4. Complete Phase 5 US2 (T028–T032) — SSE live updates (FR-006, SC-003)
5. **STOP and VALIDATE**: Vote + kiosk/mobile sync without reload; limits enforced

### Incremental Delivery

1. Setup + Foundational → models, vote service, participant session ready
2. US3 → participant session + sign-in UX
3. US1 → vote API + `/participar` vote UI with votes-remaining badge
4. US2 → SSE live updates on kiosk + mobile (required for P1 completion)
5. US4 → window roll-forward test + acceptance verification
6. Polish → regression + manifest closure

### Suggested MVP Scope

**T001–T032** (Setup + Foundational + US3 + US1 + US2). US4 (T033–T034) follows immediately before polish.

---

## Notes

- Reference: 004 `queue_service._recompute_positions`, `state_service.bump_revision`, `sse_hub`, `DisplayStateService` patterns
- Operator queue/moderation APIs from 004 MUST remain unchanged; participant cookie must not grant operator access
- `POST /api/participant/dev-auth` only when `JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH=true`
- Spanish UI throughout `/participar` (errors, sign-in prompt, votes remaining)
- FR-008 votes-remaining UI ships in US1 (T026); US4 (T034) is acceptance verification + window expiry test (T033)
- Google OAuth and song submit deferred to 006
- Kiosk display layout unchanged; vote counts on strip update via existing SSE when participants vote
