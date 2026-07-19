from datetime import date, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


EVENT_CONFIG_SINGLETON_ID = 1
JUKEBOX_RUNTIME_SINGLETON_ID = 1
EVENT_CONFIG_DEFAULT_NAME = "Jukebox AMRN"
EVENT_CONFIG_DEFAULT_SUBTITLE = "Elige la música del evento"
EVENT_CONFIG_DEFAULT_APP_HEIGHT_PX = 720
EVENT_CONFIG_DEFAULT_THEME = "dark"
EVENT_CONFIG_DEFAULT_QUEUE_VISIBLE_COUNT = 8
MAX_QUEUED_ENTRIES = 100


class QueueEntryStatus(str, Enum):
    pending_review = "pending_review"
    rejected = "rejected"
    queued = "queued"
    playing = "playing"
    played = "played"


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


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    youtube_video_id: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_by_participant_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    vote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[QueueEntryStatus] = mapped_column(
        SAEnum(
            QueueEntryStatus,
            name="queue_entry_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    original_query: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class JukeboxRuntime(Base):
    __tablename__ = "jukebox_runtime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    now_playing_entry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("queue_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    google_sub: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    queue_entry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("queue_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class YoutubeApiKeyDailyUsage(Base):
    __tablename__ = "youtube_api_key_daily_usage"
    __table_args__ = (
        UniqueConstraint(
            "key_hash",
            "quota_day",
            name="uq_youtube_api_key_daily_usage_key_day",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    quota_day: Mapped[date] = mapped_column(Date, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
