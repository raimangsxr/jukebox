# amrn-jukebox

Collaborative YouTube jukebox for events: attendees propose songs and vote to reorder the queue; a kiosk display shows the current video, participation QR, and live playlist. Moderators approve submissions before they enter the queue.

Monorepo layout matches [amrn-bull](https://github.com/) and **amrn-escalabirras-dual**:

- `backend/` — FastAPI + Alembic + PostgreSQL (`JUKEBOX_` env prefix)
- `frontend/` — Angular 22 standalone SPA
- `specs/` — SDD manifest, contracts, and change specs

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| Service  | URL |
|----------|-----|
| Frontend | http://localhost:4200 |
| Backend  | http://localhost:8000/api/health |

### Local dev (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest tests
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm ci
npm start
```

## Routes (foundation)

| Path | Purpose |
|------|---------|
| `/` | Kiosk display (3-panel layout placeholder) |
| `/participar` | Mobile participation (Google OAuth planned) |
| `/login` | Operator login |
| `/admin` | Moderation + event config + embed tokens |

## SDD

Start from `specs/manifest.yml`. Active change: **001-foundation-jukebox**.

See `AGENTS.md` for agent workflow.
