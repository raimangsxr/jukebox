# Context Pack: 001-foundation-jukebox

## Mandatory reads

1. `specs/manifest.yml`
2. `specs/changes/001-foundation-jukebox/spec.md`
3. `specs/changes/001-foundation-jukebox/checklists/requirements.md`
4. `specs/changes/001-foundation-jukebox/plan.md`
5. `specs/changes/001-foundation-jukebox/analyze.md`
6. `specs/contracts/backend-api/contract.md`
7. `specs/contracts/app-core/contract.md`
8. `specs/contracts/ops-platform/contract.md`

## Reference repos (patterns only)

- `amrn-bull` — monorepo layout, operator auth, embed tokens, SSE, iframe protocol
- `amrn-escalabirras-dual` — dual-surface Angular app, embed density override
- `kiosk-screen` CHG-042 — `embed_app_family`, `bull:config` density protocol

## Code entrypoints (this change)

- `backend/app/main.py`
- `backend/app/bootstrap.py`
- `frontend/src/app/app.routes.ts`
- `docker-compose.yml`

## Tests

- `backend/tests/test_health.py`
- `npm --prefix frontend run build`

## SDD gate status

See `checklists/requirements.md` — gates 1–6 complete; implement gate (7) in progress.

## Out of scope for this change

- Google OAuth, queue, voting, moderation, YouTube player, Web Push
- kiosk-screen repo changes

## Do not read by default

- `specs/archive/**`
- Consolidated changes in sibling repos
