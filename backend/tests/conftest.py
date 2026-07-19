import os

os.environ.setdefault("JUKEBOX_OPERATOR_USERNAME", "op")
os.environ.setdefault("JUKEBOX_OPERATOR_PASSWORD", "operator-test-password-1234")
os.environ.setdefault("JUKEBOX_SESSION_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("JUKEBOX_COOKIE_SECURE", "false")
os.environ.setdefault("JUKEBOX_FRAME_ANCESTORS", "'none'")

import asyncio
import json
from collections.abc import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.bootstrap import ensure_event_config, ensure_jukebox_runtime, ensure_operator
from app.config import get_settings
from app.database import Base, get_db
from app.main import create_app
from app.models import (
    ApiToken,
    JukeboxRuntime,
    Participant,
    QueueEntry,
    QueueEntryStatus,
    User,
    Vote,
)
from app.security import generate_token, hash_token
from app.services.state_service import get_or_create_runtime
from app.services import sse_hub


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
    ensure_jukebox_runtime(db_session)
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


@pytest.fixture
def sample_video_id() -> str:
    return "dQw4w9WgXcQ"


def _make_queue_entry(
    db_session: Session,
    *,
    video_id: str,
    status: QueueEntryStatus,
    vote_count: int = 0,
    title: str = "Test Song",
    submitted_by_participant_id: str | None = None,
) -> QueueEntry:
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        status=status,
        original_query=video_id,
        vote_count=vote_count,
        position=1 if status == QueueEntryStatus.queued else None,
        submitted_by_participant_id=submitted_by_participant_id,
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


@pytest.fixture
def pending_entry(db_session: Session, sample_video_id: str) -> QueueEntry:
    return _make_queue_entry(
        db_session, video_id=sample_video_id, status=QueueEntryStatus.pending_review
    )


@pytest.fixture
def queued_entry(db_session: Session) -> QueueEntry:
    return _make_queue_entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.queued,
        vote_count=3,
    )


@pytest.fixture
def playing_entry(db_session: Session) -> QueueEntry:
    entry = _make_queue_entry(
        db_session,
        video_id="9bZkp7q19f0",
        status=QueueEntryStatus.playing,
        vote_count=1,
        title="Playing Song",
    )
    runtime = get_or_create_runtime(db_session)
    runtime.now_playing_entry_id = entry.id
    db_session.commit()
    return entry


@pytest.fixture
def participant(db_session: Session) -> Participant:
    row = Participant(id=str(uuid4()), display_name="Test Participant")
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def second_queued_entry(db_session: Session) -> QueueEntry:
    return _make_queue_entry(
        db_session,
        video_id="kJQP7kiw5Fk",
        status=QueueEntryStatus.queued,
        vote_count=0,
        title="Second Song",
    )


@pytest.fixture
def dev_participant_client(client: TestClient, monkeypatch):
    monkeypatch.setenv("JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH", "true")
    get_settings.cache_clear()
    response = client.post(
        "/api/participant/dev-auth",
        json={"display_name": "Voter"},
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def google_oauth_settings(monkeypatch):
    monkeypatch.setenv("JUKEBOX_GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("JUKEBOX_GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "JUKEBOX_GOOGLE_REDIRECT_URI",
        "http://testserver/api/auth/google/callback",
    )
    monkeypatch.setenv(
        "JUKEBOX_PARTICIPANT_OAUTH_RETURN_URL",
        "http://localhost:4200/participar",
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def google_profile() -> dict:
    return {
        "sub": "google-sub-123",
        "name": "Google User",
        "email": "user@example.com",
        "picture": "https://example.com/avatar.jpg",
    }


@pytest.fixture
def google_participant(db_session: Session, google_profile: dict) -> Participant:
    row = Participant(
        id=str(uuid4()),
        google_sub=google_profile["sub"],
        display_name=google_profile["name"],
        email=google_profile["email"],
        avatar_url=google_profile["picture"],
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


@pytest.fixture
def google_oauth_client(client: TestClient, google_oauth_settings, monkeypatch, google_profile):
    from app.services import google_oauth_service

    def _fake_exchange(code: str) -> dict:
        assert code == "auth-code"
        return {"access_token": "access-token"}

    def _fake_userinfo(access_token: str) -> dict:
        assert access_token == "access-token"
        return google_profile

    monkeypatch.setattr(google_oauth_service, "exchange_code_for_tokens", _fake_exchange)
    monkeypatch.setattr(google_oauth_service, "fetch_google_userinfo", _fake_userinfo)
    return client


def parse_sse_message(raw: str) -> tuple[str | None, dict | None]:
    event_type: str | None = None
    data: dict | None = None
    for line in raw.strip().split("\n"):
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data = json.loads(line[6:])
    return event_type, data


async def _collect_sse_events(
    queue: asyncio.Queue[str],
    *,
    event_type: str | None = None,
    timeout: float = 2.0,
) -> list[tuple[str | None, dict | None]]:
    collected: list[tuple[str | None, dict | None]] = []
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            break
        try:
            message = await asyncio.wait_for(queue.get(), timeout=min(0.2, remaining))
        except asyncio.TimeoutError:
            continue
        parsed_type, payload = parse_sse_message(message)
        if event_type is None or parsed_type == event_type:
            collected.append((parsed_type, payload))
    return collected


def collect_sse_events_after(
    action: Callable[[], None],
    *,
    event_type: str | None = None,
    timeout: float = 2.0,
) -> list[tuple[str | None, dict | None]]:
    queue = sse_hub.subscribe()
    try:
        action()
        return asyncio.run(
            _collect_sse_events(queue, event_type=event_type, timeout=timeout)
        )
    finally:
        sse_hub.unsubscribe(queue)


@pytest.fixture
def youtube_api_keys(monkeypatch):
    monkeypatch.setenv("JUKEBOX_YOUTUBE_API_KEYS", "key-one,key-two")
    get_settings.cache_clear()
    from app.services.search_rate_limiter import reset_for_tests
    from app.services.youtube_api_key_pool import get_youtube_api_key_pool
    from app.services.youtube_api_key_usage_service import reset_for_tests as reset_usage

    get_youtube_api_key_pool().reset_for_tests()
    reset_for_tests()
    reset_usage()
    yield
    get_settings.cache_clear()
    get_youtube_api_key_pool().reset_for_tests()
    reset_for_tests()
    reset_usage()


def make_youtube_search_response(
    items: list[dict],
    *,
    next_page_token: str | None = None,
) -> dict:
    payload: dict = {"items": items}
    if next_page_token:
        payload["nextPageToken"] = next_page_token
    return payload


def make_youtube_search_item(
    video_id: str,
    *,
    title: str = "Test Video",
    channel: str = "Test Channel",
) -> dict:
    return {
        "id": {"videoId": video_id},
        "snippet": {
            "title": title,
            "channelTitle": channel,
            "thumbnails": {
                "default": {"url": f"https://i.ytimg.com/vi/{video_id}/default.jpg"}
            },
        },
    }
