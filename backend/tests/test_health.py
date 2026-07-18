from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import create_app


def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_csp_header(client):
    response = client.get("/api/health")
    assert response.headers.get("content-security-policy") == "frame-ancestors 'none'"


def test_health_custom_frame_ancestors(monkeypatch, db_session):
    monkeypatch.setenv("JUKEBOX_FRAME_ANCESTORS", "https://kiosk.example.com")
    get_settings.cache_clear()

    app = create_app()
    app.router.lifespan_context = None

    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    response = TestClient(app).get("/api/health")
    assert response.headers.get("content-security-policy") == (
        "frame-ancestors https://kiosk.example.com"
    )
    get_settings.cache_clear()
