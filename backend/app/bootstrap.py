import logging

from sqlalchemy.orm import Session

from .models import (
    EVENT_CONFIG_DEFAULT_APP_HEIGHT_PX,
    EVENT_CONFIG_DEFAULT_NAME,
    EVENT_CONFIG_DEFAULT_QUEUE_VISIBLE_COUNT,
    EVENT_CONFIG_DEFAULT_SUBTITLE,
    EVENT_CONFIG_DEFAULT_THEME,
    EVENT_CONFIG_SINGLETON_ID,
    EventConfig,
    User,
)
from .security import hash_password


logger = logging.getLogger(__name__)


def ensure_operator(db: Session, username: str, password: str) -> bool:
    """Idempotently create the operator user."""
    if not username or not password:
        raise ValueError(
            "JUKEBOX_OPERATOR_USERNAME and JUKEBOX_OPERATOR_PASSWORD must be set"
        )
    if len(password) < 12:
        raise ValueError(
            "JUKEBOX_OPERATOR_PASSWORD must be at least 12 characters"
        )

    existing = db.query(User).filter(User.username == username).one_or_none()
    if existing is not None:
        logger.info("Operator user %r already exists", username)
        return False

    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Created operator user %r (id=%s)", user.username, user.id)
    return True


def ensure_event_config(db: Session) -> bool:
    """Idempotently create the singleton event config row."""
    existing = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    if existing is not None:
        logger.info("Event config row already exists")
        return False

    row = EventConfig(
        id=EVENT_CONFIG_SINGLETON_ID,
        name=EVENT_CONFIG_DEFAULT_NAME,
        subtitle=EVENT_CONFIG_DEFAULT_SUBTITLE,
        app_height_px=EVENT_CONFIG_DEFAULT_APP_HEIGHT_PX,
        theme=EVENT_CONFIG_DEFAULT_THEME,
        queue_visible_count=EVENT_CONFIG_DEFAULT_QUEUE_VISIBLE_COUNT,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Seeded event config row (id=%s)", row.id)
    return True
