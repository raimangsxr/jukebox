# Tasks: 001-foundation-jukebox

## Phase A — SDD gates (Spec Kit)

- [x] A001 `/speckit.specify` — `spec.md` with user stories and requirements
- [x] A002 `/speckit.clarify` — clarifications session 2026-07-17 in `spec.md`
- [x] A003 `/speckit.checklist` — `checklists/requirements.md`
- [x] A004 `/speckit.plan` — `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/contract-deltas.md`
- [x] A005 `/speckit.tasks` — this file
- [x] A006 `/speckit.analyze` — `analyze.md`

## Phase B — SDD scaffolding (specs repo structure)

- [x] B001 `specs/manifest.yml` + constitution
- [x] B002 Baseline contracts: `backend-api`, `app-core`, `ops-platform`
- [x] B003 `context-pack.md`
- [x] B004 Copy `.specify/` tooling and Spec Kit commands from amrn-bull
- [x] B005 `.specify/feature.json` for `specs/changes/` layout

## Phase C — Implement gate (`/speckit.implement`)

- [x] C001 Backend scaffold: FastAPI, health, bootstrap, Alembic 0001, pytest
- [x] C002 Frontend scaffold: Angular 22, routes, placeholders, Tailwind, build
- [x] C003 Ops: docker-compose, Dockerfiles, nginx, CI workflow, README
- [x] C004 Compose smoke: `scripts/compose-smoke.sh` (run locally when Docker daemon is up)
- [x] C005 `pytest backend/tests` — 6 tests pass (health + bootstrap)
- [x] C006 `npm --prefix frontend run build` passes
- [x] C007 Manifest: change 001 marked `implemented`
- [x] C008 Contracts consolidated from `contract-deltas.md`

## Phase D — Deferred (require new change specs)

- [ ] D001 002 — Operator auth + embed tokens
- [ ] D002 003 — Event config + SSE skeleton
- [ ] D003 004 — Queue + moderation
- [ ] D004 005 — Voting
- [ ] D005 006 — Google OAuth + participar
- [ ] D006 007 — Display + YouTube player
- [ ] D007 008 — Notifications
- [ ] D008 009 — kiosk-screen integration
