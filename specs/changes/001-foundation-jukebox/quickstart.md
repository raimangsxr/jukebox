# Quickstart: 001-foundation-jukebox

Local validation for the monorepo scaffold (change 001).

## Prerequisites

- Docker + Docker Compose
- OR: Python 3.12+, Node 24+, PostgreSQL 16

## Phase 1 — Environment

```bash
cd /path/to/amrn-jukebox
cp .env.example .env
# Edit JUKEBOX_OPERATOR_PASSWORD (≥12 chars) and JUKEBOX_SESSION_SECRET if needed
```

## Phase 2 — Compose smoke (requires Docker)

```bash
bash scripts/compose-smoke.sh
```

Or manually: `docker compose up --build` and verify:

| Check | Expected |
|-------|----------|
| http://localhost:8000/api/health | `{"status":"ok"}` |
| Response header | `content-security-policy: frame-ancestors 'none'` |
| http://localhost:4200 | Display placeholder (3-panel sketch) |
| http://localhost:4200/participar | Participate placeholder |
| http://localhost:4200/login | Login placeholder |
| http://localhost:4200/admin | Admin placeholder |

## Phase 3 — Native backend tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests -q
```

## Phase 4 — Frontend build

```bash
cd frontend
npm ci
npm run build
```

## Phase 5 — SDD artifacts

Confirm files exist:

```text
specs/manifest.yml
specs/changes/001-foundation-jukebox/spec.md
specs/changes/001-foundation-jukebox/checklists/requirements.md
specs/changes/001-foundation-jukebox/plan.md
specs/changes/001-foundation-jukebox/tasks.md
specs/changes/001-foundation-jukebox/analyze.md
```

## Out of scope for this quickstart

- Operator login flow
- Google OAuth
- Queue submit / vote / moderate
- Kiosk iframe embed in kiosk-screen
