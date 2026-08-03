# Tasks: 016-participant-limits-ux

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 1 — Backend limits (P1)

- [x] T001 Add `max_searchs_10minutes_per_participant` and `max_votes_10minutes_per_participant` to `backend/app/config.py`
- [x] T002 Wire search rate limiter to settings + 10-minute window in `search_rate_limiter.py`
- [x] T003 Wire vote cap to settings + 10-minute window in `vote_service.py`
- [x] T004 Expose `max_searches_10_minutes` and `max_votes_10_minutes` in `ParticipantStateResponse` via `state_service.py` + `schemas.py`
- [x] T005 Update `backend/.env.example`, `deploy/k8s/configmap.yaml`, `deploy/k8s/backend.yaml`
- [x] T006 Fix `test_votes.py` window rollover (11 min) and `test_rate_limiter.py` dynamic limit

## Phase 2 — Live connection UX (P1)

- [x] T007 Create `frontend/src/app/services/live-connection.ts` (SSE + reconnect + polling fallback)
- [x] T008 Create `frontend/src/app/components/live-status.component.ts` (single Spanish badge)
- [x] T009 Refactor `DisplayStateService` to use `LiveConnectionManager` + `connectionStatus$`
- [x] T010 Refactor `ParticipantStateService` similarly; preserve SSE merge fields
- [x] T011 Add `<app-live-status>` to display, admin, participate templates
- [x] T012 Add `live-connection.spec.ts` vitest smoke test

## Phase 3 — Admin mobile (P1)

- [x] T013 Split moderation pending list: cards `< md`, table `≥ md` in `admin.component.html`
- [x] T014 Add `overflow-x: hidden` on `.admin-main` in `admin.component.css`

## Phase 4 — Participant rules (P1)

- [x] T015 Extend `ParticipantStateResponse` TS model with new max fields
- [x] T016 Add onboarding gate + rules UI in `participate.component.ts/html`
- [x] T017 Use `sessionStorage` key `jukebox.participantRulesAccepted`
- [x] T018 Update `votesRemainingLabel()` to use dynamic `max_votes_10_minutes`

## Phase 5 — Contracts & SDD (P2)

- [x] T019 Update `specs/contracts/backend-api/contract.md` and `ops-platform/contract.md`
- [x] T020 Create change folder SDD artifacts (spec, plan, tasks, analyze)
- [x] T021 Update `specs/manifest.yml` active change + entry for 016

## Phase 6 — Verification

- [x] T022 Run backend pytest subset + frontend build
- [ ] T023 Manual quickstart walkthrough per spec acceptance scenarios
- [x] T024 Verification report — see [verification.md](./verification.md)
