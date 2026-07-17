# jukebox-backend

FastAPI service for [amrn-jukebox](../README.md).

## Local dev (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # edit passwords
pytest tests
uvicorn app.main:app --reload --port 8000
```

## Migrations

```bash
alembic -c alembic.ini upgrade head
```

## Tests

```bash
pytest tests
```
