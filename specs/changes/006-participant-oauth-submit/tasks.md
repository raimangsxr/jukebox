---
description: "Task list for 006-participant-oauth-submit"
---

# Tasks: Participant Google OAuth and Song Submit

**Input**: Design documents from `specs/changes/006-participant-oauth-submit/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/contract-deltas.md, quickstart.md

**Tests**: Included — spec SC-003/SC-004 require automated submit limits and vote regression after OAuth.

**Organization**: Tasks grouped by user story (US1–US4). US1 (OAuth) precedes US2 (submit); US3 (Mis canciones) follows submit API; US4 is vote regression after OAuth path exists.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Manifest + Contract Consolidation)

**Purpose**: Register change and merge contract deltas before code (Constitution II + IV)

- [x] T001 Register `006-participant-oauth-submit` in `specs/manifest.yml` as `draft` with `active.change` and `context_pack` pointing to `specs/changes/006-participant-oauth-submit/context-pack.md`
- [x] T002 Update `specs/contracts/backend-api/contract.md` from `specs/changes/006-participant-oauth-submit/contracts/contract-deltas.md` (Google OAuth routes, submit API, submissions list, env vars, auth policy)
- [x] T003 Update `specs/contracts/app-core/contract.md` from `specs/changes/006-participant-oauth-submit/contracts/contract-deltas.md` (`/participar` Google login, submit form, Mis canciones, status labels)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Participant profile migration, config, schemas, and test helpers shared by OAuth and submit

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Extend `Participant` model in `backend/app/models.py` with `google_sub` (unique nullable), `email`, `avatar_url` per `data-model.md`
- [x] T005 Create Alembic migration `backend/alembic/versions/0005_participant_google_profile.py`
- [x] T006 [P] Add `SubmitRequest`, `SubmissionListResponse`, and extend `ParticipantRead` (`email`, `avatar_url`) in `backend/app/schemas.py`
- [x] T007 [P] Add `JUKEBOX_GOOGLE_CLIENT_ID`, `JUKEBOX_GOOGLE_CLIENT_SECRET`, `JUKEBOX_GOOGLE_REDIRECT_URI`, `JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL` to `backend/app/config.py`
- [x] T008 [P] Extend `backend/tests/conftest.py` with Google OAuth HTTP mock helpers and `google_participant` upsert fixture
- [x] T009 Update `backend/tests/test_auth_policy.py` for 006 canonical routes (`GET /api/auth/google/login`, `GET /api/auth/google/callback` public; `POST /api/queue/submit`, `GET /api/participant/submissions` participant-protected)

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 — Sign in with Google (Priority: P1)

**Goal**: Participants authenticate via Google on `/participar` and receive `jukebox_participant_session`; production UI shows **Iniciar sesión con Google**.

**Independent Test**: `/participar` → Google login (or mocked callback in pytest) → `GET /api/participant/me` returns profile with `display_name`; session persists on refresh; operator cookie unaffected.

### Tests for User Story 1

- [x] T010 [US1] Add `backend/tests/test_oauth_google.py` covering login redirect, callback upsert by `google_sub`, profile reuse on second login, invalid `state` rejection, cookie set, redirect to return URL with `oauth_error` on failure

### Implementation for User Story 1

- [x] T011 [US1] Create `backend/app/services/google_oauth_service.py` (authorize URL + signed `state`, token exchange, userinfo fetch, upsert participant, set participant cookie)
- [x] T012 [US1] Create `backend/app/routers/auth_google.py` with `GET /api/auth/google/login` and `GET /api/auth/google/callback`
- [x] T013 [US1] Mount `auth_google` router in `backend/app/main.py`
- [x] T014 [P] [US1] Extend `frontend/src/app/services/participant.service.ts` with `startGoogleLogin()` (full redirect to `/api/auth/google/login`) and `parseOAuthReturnQuery()` for `oauth_error` / `oauth=ok`
- [x] T015 [US1] Update `frontend/src/app/participate/participate.component.ts` and `frontend/src/app/participate/participate.component.html`: **Iniciar sesión con Google** primary; **vote and submit controls disabled** when unauthenticated (SC-005); friendly empty state; authenticated header (name + avatar); dev-auth **hidden** unless `environment.allowDevParticipantAuth` or `?dev=1` (FR-011); Spanish OAuth error messages from `oauth_error` query
- [x] T016 [US1] Run `pytest backend/tests/test_oauth_google.py` and fix failures

**Checkpoint**: Google OAuth establishes participant session end-to-end

---

## Phase 4: User Story 2 — Submit a YouTube Song (Priority: P1) 🎯 MVP

**Goal**: Authenticated participant submits YouTube URL → `pending_review` with limits and duplicate checks; moderator sees entry in pending list.

**Independent Test**: Participant session (OAuth or dev-auth) + valid URL → `POST /api/queue/submit` → 201; third pending → 429; duplicate active video → 409; invalid URL → 422.

### Tests for User Story 2

- [x] T017 [US2] Add `backend/tests/test_participant_submit.py` covering success, 2 pending limit (429), 1 own queued/playing limit (429), duplicate (409), invalid YouTube (422), **oEmbed/metadata failure** on private/deleted video (422), **concurrent submits** (one 201, one 429, no corrupt counts), **re-submit after `played`** when no active duplicate, **re-submit after moderator reject** when under pending limit, 401 without session, `submitted_by_participant_id` set, revision bump

### Implementation for User Story 2

- [x] T018 [US2] Add `submit_as_participant` to `backend/app/services/queue_service.py` (per-participant limits, duplicate check, metadata fetch with **422 on oEmbed failure**, transaction-safe limit checks for concurrency, `bump_revision`)
- [x] T019 [US2] Add `POST /api/queue/submit` to `backend/app/routers/queue.py` with `CurrentParticipant` auth
- [x] T020 [P] [US2] Extend `frontend/src/app/services/participant.service.ts` with `submitSong(url)` calling `POST /api/queue/submit`
- [x] T021 [US2] Update `frontend/src/app/participate/participate.component.ts`, `frontend/src/app/participate/participate.component.html`, and `frontend/src/app/services/participant.service.ts` with submit form; add `mapSubmitError(detail)` mapping stable English API codes to Spanish per `contracts/contract-deltas.md`
- [x] T022 [US2] Run `pytest backend/tests/test_participant_submit.py` and fix failures

**Checkpoint**: Participants can submit songs subject to baseline limits

---

## Phase 5: User Story 3 — View My Submissions (Priority: P2)

**Goal**: **Mis canciones** lists participant submissions with Spanish status labels; updates after moderation via SSE revision.

**Independent Test**: Submit song → visible as **Pendiente de revisión** → operator approve → status **En cola** within seconds without full page reload.

### Tests for User Story 3

- [x] T023 [US3] Add `backend/tests/test_participant_submissions.py` covering `GET /api/participant/submissions` auth, ordering, only own entries, status fields including `rejection_reason`

### Implementation for User Story 3

- [x] T024 [US3] Add `GET /api/participant/submissions` to `backend/app/routers/participant.py` returning `SubmissionListResponse`
- [x] T025 [P] [US3] Extend `frontend/src/app/services/participant.service.ts` with `getSubmissions()` and `frontend/src/app/services/participant-state.service.ts` with `refreshSubmissions()` on init and SSE revision
- [x] T026 [US3] Add **Mis canciones** section to `frontend/src/app/participate/participate.component.html` with Spanish status badges (`pending_review`, `queued`, `playing`, `played`, `rejected`) and rejection reason
- [x] T027 [US3] Run submission list tests and fix failures

**Checkpoint**: US3 acceptance — Mis canciones visible and live-updating

---

## Phase 6: User Story 4 — Vote after OAuth (Priority: P1)

**Goal**: Voting from 005 works unchanged for Google-authenticated participants.

**Independent Test**: OAuth (or mocked) session → vote twice → limit enforced; SSE updates; no regression vs 005.

### Tests for User Story 4

- [x] T028 [US4] Add OAuth-session vote regression to `backend/tests/test_votes.py` (participant with `google_sub` via fixture votes on `queued`, limits, reorder) and run alongside existing 005 cases

### Implementation for User Story 4

- [x] T029 [US4] Verify `frontend/src/app/participate/participate.component.ts` vote flow unchanged after OAuth header/submit sections; confirm **SSE vote updates** when another participant votes while signed in via OAuth (US4.3); fix only if T028 fails

**Checkpoint**: SC-004 vote regression passes with OAuth identity

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, regression, ops notes, and change closure

- [x] T030 Run full `pytest backend/tests` including `test_oauth_google.py`, `test_participant_submit.py`, `test_participant_submissions.py`, `test_votes.py`, and 004/005 regression with zero failures
- [x] T031 Run `npm --prefix frontend run build` with zero errors
- [x] T032 Document `JUKEBOX_GOOGLE_*` env vars in `docker-compose.yml` or `.env.example` if present (ops note per contract-deltas)
- [x] T033 Execute manual validation per `specs/changes/006-participant-oauth-submit/quickstart.md`: OAuth (**SC-001** ≤30s), submit + Mis canciones (**SC-002** ≤3s), unauthenticated disabled controls (**SC-005**), limits, Mis canciones SSE, vote regression + **SSE after OAuth**, **operator moderation unchanged** (FR-012: approve/reject/skip/dev-submit)
- [x] T034 Mark change `implemented` in `specs/manifest.yml` and clear or update `active.change`
- [x] T035 Update implementation validation in `specs/changes/006-participant-oauth-submit/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start here
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — OAuth requires migration + config
- **Phase 4 (US2)**: Depends on Phase 2; **participant session** from US1 or dev-auth for tests
- **Phase 5 (US3)**: Depends on Phase 4 — submissions list needs submit data
- **Phase 6 (US4)**: Depends on Phase 3 — OAuth identity for regression
- **Phase 7 (Polish)**: Depends on US1–US4

### User Story Dependencies

| Story | Depends on | Independent test without other stories |
|-------|------------|----------------------------------------|
| US1 | Foundational | Yes — mocked Google callback + `GET /api/participant/me` |
| US2 | Foundational (+ session) | Yes — dev-auth or OAuth fixture + submit API |
| US3 | US2 | Yes — submissions API + UI after seeded submit |
| US4 | US1 | Yes — vote API with OAuth participant fixture |

### Parallel Opportunities

- **Phase 1**: T002 and T003 — different contract files
- **Phase 2**: T006, T007, T008 parallel after T004–T005
- **Phase 3**: T014 parallel with T012–T013 after T011 interface known
- **Phase 4**: T020 parallel with T018–T019
- **Phase 5**: T025 parallel with T024

### Parallel Example: User Story 1

```bash
# After T013 (auth_google mounted):
Task T014: participant.service.ts OAuth redirect
# T015 participate UI can proceed once T014 API shape is defined
```

### Parallel Example: User Story 2

```bash
# After T019 (submit route mounted):
Task T020: participant.service.ts submitSong()
Task T021: participate submit form UI
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US4)

1. Complete Phase 1–2 (T001–T009)
2. Complete Phase 3 US1 (T010–T016)
3. Complete Phase 4 US2 (T017–T022)
4. Complete Phase 6 US4 (T028–T029) — P1 vote regression before shipping OAuth
5. **STOP and VALIDATE**: Google login + submit with limits + vote regression
6. Demo full `/participar` attendee flow

### Incremental Delivery

1. Setup + Foundational → migration + config ready
2. US1 → Google OAuth production login
3. US2 → submit API + form (core P1 value)
4. US4 → vote regression confirmation (P1 — do not defer past MVP)
5. US3 → Mis canciones + SSE refresh
6. Polish → manifest closure

### Suggested MVP Scope

**T001–T029** (Setup + Foundational + US1 + US2 + US4). US3 (P2) follows immediately after MVP.

---

## Notes

- Reference: 005 `participant_session.py`, `ParticipantStateService`, 004 `queue_service.create_pending_entry`, `youtube_meta.py`
- Dev-auth remains for pytest when Google credentials unavailable
- Do not block SSE streaming tests on blocking `EventSource` reads (005 lesson)
- Operator `POST /api/queue/dev-submit` and moderation unchanged
- Spanish UI throughout `/participar`
