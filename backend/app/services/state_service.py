from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    EVENT_CONFIG_SINGLETON_ID,
    JUKEBOX_RUNTIME_SINGLETON_ID,
    EventConfig,
    JukeboxRuntime,
    QueueEntry,
    QueueEntryStatus,
)
from ..schemas import EventConfigSummary, ParticipantStateResponse, QueueEntryRead, StateResponse
from .sse_hub import broadcast_state


def get_or_create_runtime(db: Session) -> JukeboxRuntime:
    runtime = db.get(JukeboxRuntime, JUKEBOX_RUNTIME_SINGLETON_ID)
    if runtime is None:
        runtime = JukeboxRuntime(id=JUKEBOX_RUNTIME_SINGLETON_ID, revision=0)
        db.add(runtime)
        db.commit()
        db.refresh(runtime)
    return runtime


def bump_revision(db: Session) -> JukeboxRuntime:
    runtime = get_or_create_runtime(db)
    runtime.revision += 1
    runtime.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(runtime)
    state = build_state_response(db)
    broadcast_state(state)
    return runtime


def _entry_to_read(entry: QueueEntry) -> QueueEntryRead:
    return QueueEntryRead.model_validate(entry)


def get_now_playing(db: Session) -> QueueEntry | None:
    runtime = get_or_create_runtime(db)
    if not runtime.now_playing_entry_id:
        return None
    entry = db.get(QueueEntry, runtime.now_playing_entry_id)
    if entry is None or entry.status != QueueEntryStatus.playing:
        return None
    return entry


def get_queue_strip(db: Session) -> list[QueueEntry]:
    config = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    limit = config.queue_visible_count if config else 8
    stmt = (
        select(QueueEntry)
        .where(QueueEntry.status == QueueEntryStatus.queued)
        .order_by(QueueEntry.vote_count.desc(), QueueEntry.created_at.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_all_queued(db: Session) -> list[QueueEntry]:
    stmt = (
        select(QueueEntry)
        .where(QueueEntry.status == QueueEntryStatus.queued)
        .order_by(QueueEntry.vote_count.desc(), QueueEntry.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def build_participant_state_response(
    db: Session, participant_id: str
) -> ParticipantStateResponse:
    from .vote_service import votes_remaining as _votes_remaining

    runtime = get_or_create_runtime(db)
    config = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    if config is None:
        raise RuntimeError("event_config singleton missing")

    now_playing = get_now_playing(db)
    queue = get_all_queued(db)

    return ParticipantStateResponse(
        revision=runtime.revision,
        now_playing=_entry_to_read(now_playing) if now_playing else None,
        queue=[_entry_to_read(e) for e in queue],
        votes_remaining=_votes_remaining(db, participant_id),
        max_pending_submissions=get_settings().max_pending_submissions_per_participant,
        event_config=EventConfigSummary(
            name=config.name,
            subtitle=config.subtitle,
            app_height_px=config.app_height_px,
            theme=config.theme,
            queue_visible_count=config.queue_visible_count,
        ),
    )


def build_state_response(db: Session) -> StateResponse:
    runtime = get_or_create_runtime(db)
    config = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    if config is None:
        raise RuntimeError("event_config singleton missing")

    now_playing = get_now_playing(db)
    queue = get_queue_strip(db)

    return StateResponse(
        revision=runtime.revision,
        now_playing=_entry_to_read(now_playing) if now_playing else None,
        queue=[_entry_to_read(e) for e in queue],
        event_config=EventConfigSummary(
            name=config.name,
            subtitle=config.subtitle,
            app_height_px=config.app_height_px,
            theme=config.theme,
            queue_visible_count=config.queue_visible_count,
        ),
    )
