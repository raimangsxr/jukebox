from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


EVENT_CONFIG_SINGLETON_ID = 1
EVENT_CONFIG_DEFAULT_NAME = "Jukebox AMRN"
EVENT_CONFIG_DEFAULT_SUBTITLE = "Elige la música del evento"
EVENT_CONFIG_DEFAULT_APP_HEIGHT_PX = 720
EVENT_CONFIG_DEFAULT_THEME = "dark"
EVENT_CONFIG_DEFAULT_QUEUE_VISIBLE_COUNT = 8


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EventConfig(Base):
    __tablename__ = "event_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(200), nullable=False)
    app_height_px: Mapped[int] = mapped_column(Integer, nullable=False, default=720)
    theme: Mapped[str] = mapped_column(String(8), nullable=False, default="dark")
    queue_visible_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=8
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
