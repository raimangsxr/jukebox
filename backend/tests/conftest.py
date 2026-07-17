import os

os.environ.setdefault("JUKEBOX_OPERATOR_USERNAME", "op")
os.environ.setdefault("JUKEBOX_OPERATOR_PASSWORD", "operator-test-password-1234")
os.environ.setdefault("JUKEBOX_SESSION_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("JUKEBOX_COOKIE_SECURE", "false")
os.environ.setdefault("JUKEBOX_FRAME_ANCESTORS", "'none'")

from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.bootstrap import ensure_event_config, ensure_operator
from app.config import get_settings
from app.database import Base, get_db
from app.main import create_app
from app.models import ApiToken, User
from app.security import generate_token, hash_token


OPERATOR_USERNAME = os.environ["JUKEBOX_OPERATOR_USERNAME"]
OPERATOR_PASSWORD = os.environ["JUKEBOX_OPERATOR_PASSWORD"]


def _create_test_app(db_session: Session) -> TestClient:
    app = create_app()
    app.router.lifespan_context = None

    def _override() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    TestingSession = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, future=True
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session):
    settings = get_settings()
    ensure_operator(
        db_session,
        username=settings.operator_username,
        password=settings.operator_password,
    )
    ensure_event_config(db_session)
    return _create_test_app(db_session)


@pytest.fixture
def operator_credentials() -> dict[str, str]:
    return {"username": OPERATOR_USERNAME, "password": OPERATOR_PASSWORD}


@pytest.fixture
def authed_client(client: TestClient, operator_credentials: dict[str, str]):
    response = client.post("/api/auth/login", json=operator_credentials)
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def embed_token(db_session: Session, operator_credentials: dict[str, str]) -> dict[str, str]:
    user = (
        db_session.query(User)
        .filter(User.username == operator_credentials["username"])
        .one()
    )
    plaintext = generate_token()
    row = ApiToken(
        id=str(uuid4()),
        user_id=user.id,
        label="pytest-embed",
        token_hash=hash_token(plaintext),
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return {"plaintext": plaintext, "id": row.id}
