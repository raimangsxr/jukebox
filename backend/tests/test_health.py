def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_csp_header(client):
    response = client.get("/api/health")
    assert response.headers.get("content-security-policy") == "frame-ancestors 'none'"


def test_health_custom_frame_ancestors(monkeypatch):
    from importlib import reload

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    monkeypatch.setenv("JUKEBOX_FRAME_ANCESTORS", "https://kiosk.example.com")

    import app.config as config_module
    import app.main as main_module
    import app.middleware as middleware_module

    reload(config_module)
    reload(middleware_module)
    reload(main_module)

    from app.bootstrap import ensure_event_config, ensure_operator
    from app.config import get_settings
    from app.database import Base, get_db
    from app.main import create_app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = Session()
    settings = get_settings()
    ensure_operator(
        db,
        username=settings.operator_username,
        password=settings.operator_password,
    )
    ensure_event_config(db)

    app = create_app()
    app.router.lifespan_context = None

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.headers.get("content-security-policy") == (
        "frame-ancestors https://kiosk.example.com"
    )
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()
