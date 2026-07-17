"""Bootstrap and persistence tests for foundation scaffold."""

from app.bootstrap import ensure_event_config, ensure_operator
from app.config import get_settings
from app.models import EVENT_CONFIG_SINGLETON_ID, EventConfig, User


def test_bootstrap_creates_operator(db_session):
    settings = get_settings()
    created = ensure_operator(
        db_session,
        username=settings.operator_username,
        password=settings.operator_password,
    )
    assert created is True
    user = db_session.query(User).filter(User.username == settings.operator_username).one()
    assert user.password_hash


def test_bootstrap_operator_is_idempotent(db_session):
    settings = get_settings()
    ensure_operator(
        db_session,
        username=settings.operator_username,
        password=settings.operator_password,
    )
    created_again = ensure_operator(
        db_session,
        username=settings.operator_username,
        password=settings.operator_password,
    )
    assert created_again is False
    assert db_session.query(User).count() == 1


def test_bootstrap_creates_event_config(db_session):
    created = ensure_event_config(db_session)
    assert created is True
    row = db_session.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    assert row is not None
    assert row.name
    assert row.app_height_px == 720
    assert row.queue_visible_count == 8


def test_bootstrap_event_config_is_idempotent(db_session):
    ensure_event_config(db_session)
    created_again = ensure_event_config(db_session)
    assert created_again is False
    assert db_session.query(EventConfig).count() == 1
