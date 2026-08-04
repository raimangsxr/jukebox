from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    EVENT_CONFIG_SINGLETON_ID,
    MAX_QUEUED_ENTRIES,
    EventConfig,
    FillerReserveEntry,
    Participant,
    QueueEntry,
    QueueEntryPriority,
    QueueEntrySource,
    QueueEntryStatus,
    QueueMode,
)
from ..schemas import HistoryListResponse, HistoryQueueEntryRead, PendingQueueEntryRead, QueueEntryRead, StateResponse
from .notification_service import emit_song_approved, emit_song_up_next
from .queue_ordering import queued_order_columns
from .state_service import build_state_response, bump_revision, get_now_playing, get_or_create_runtime
from .youtube_meta import (
    fetch_youtube_duration_sec,
    fetch_youtube_metadata_strict,
    parse_youtube_video_id,
)

ACTIVE_DUPLICATE_STATUSES = (
    QueueEntryStatus.pending_review,
    QueueEntryStatus.queued,
    QueueEntryStatus.playing,
)

TERMINAL_STATUSES = (QueueEntryStatus.played, QueueEntryStatus.rejected)


def get_queue_mode(db: Session) -> QueueMode:
    config = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    if config is None:
        return QueueMode.moderated
    return QueueMode(config.queue_mode)


def _entry_read(entry: QueueEntry) -> QueueEntryRead:
    return QueueEntryRead.model_validate(entry)


def _count_queued(db: Session) -> int:
    return (
        db.execute(
            select(func.count())
            .select_from(QueueEntry)
            .where(QueueEntry.status == QueueEntryStatus.queued)
        ).scalar_one()
    )


def _has_active_duplicate(
    db: Session, youtube_video_id: str, exclude_id: str | None = None
) -> bool:
    stmt = select(QueueEntry.id).where(
        QueueEntry.youtube_video_id == youtube_video_id,
        QueueEntry.status.in_(ACTIVE_DUPLICATE_STATUSES),
    )
    if exclude_id:
        stmt = stmt.where(QueueEntry.id != exclude_id)
    return db.execute(stmt).first() is not None


def _has_video_conflict(db: Session, youtube_video_id: str, exclude_id: str | None = None) -> bool:
    if _has_active_duplicate(db, youtube_video_id, exclude_id=exclude_id):
        return True
    reserve = db.execute(
        select(FillerReserveEntry.id).where(
            FillerReserveEntry.youtube_video_id == youtube_video_id
        )
    ).first()
    return reserve is not None


def _resolve_youtube_entry_fields(
    db: Session,
    youtube_url_or_id: str,
    search_query: str | None = None,
) -> tuple[str, str, str | None, int | None, str]:
    video_id = parse_youtube_video_id(youtube_url_or_id)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid youtube reference",
        )
    try:
        title, thumbnail = fetch_youtube_metadata_strict(video_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid youtube reference",
        ) from None
    if search_query and search_query.strip():
        original_query = f"search:{search_query.strip()}"
    else:
        original_query = youtube_url_or_id.strip()
    return (
        video_id,
        title,
        thumbnail,
        fetch_youtube_duration_sec(video_id, db),
        original_query,
    )


def _next_position(db: Session) -> int:
    current_max = db.execute(
        select(func.max(QueueEntry.position)).where(
            QueueEntry.status == QueueEntryStatus.queued
        )
    ).scalar_one()
    return (current_max or 0) + 1


def _top_queued(db: Session) -> QueueEntry | None:
    return db.execute(
        select(QueueEntry)
        .where(QueueEntry.status == QueueEntryStatus.queued)
        .order_by(*queued_order_columns())
        .limit(1)
    ).scalar_one_or_none()


def _recompute_positions(db: Session) -> None:
    entries = db.execute(
        select(QueueEntry)
        .where(QueueEntry.status == QueueEntryStatus.queued)
        .order_by(*queued_order_columns())
    ).scalars().all()
    for index, entry in enumerate(entries, start=1):
        entry.position = index
    db.commit()


def _participant_display_names(db: Session, participant_ids: set[str]) -> dict[str, str]:
    if not participant_ids:
        return {}
    participants = db.execute(
        select(Participant).where(Participant.id.in_(participant_ids))
    ).scalars().all()
    return {participant.id: participant.display_name for participant in participants}


def list_pending(db: Session) -> list[QueueEntry]:
    return list(
        db.execute(
            select(QueueEntry)
            .where(QueueEntry.status == QueueEntryStatus.pending_review)
            .order_by(QueueEntry.created_at.asc())
        ).scalars().all()
    )


def list_pending_for_moderation(db: Session) -> list[PendingQueueEntryRead]:
    entries = list_pending(db)
    if not entries:
        return []

    participant_ids = {
        entry.submitted_by_participant_id
        for entry in entries
        if entry.submitted_by_participant_id
    }
    names_by_id = _participant_display_names(db, participant_ids)

    return [
        PendingQueueEntryRead(
            **QueueEntryRead.model_validate(entry).model_dump(),
            submitted_by_display_name=(
                names_by_id.get(entry.submitted_by_participant_id)
                if entry.submitted_by_participant_id
                else None
            ),
        )
        for entry in entries
    ]


def list_history(
    db: Session,
    *,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> HistoryListResponse:
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)

    filters = [QueueEntry.status.in_(TERMINAL_STATUSES)]
    if status_filter == QueueEntryStatus.played.value:
        filters = [QueueEntry.status == QueueEntryStatus.played]
    elif status_filter == QueueEntryStatus.rejected.value:
        filters = [QueueEntry.status == QueueEntryStatus.rejected]

    total = db.execute(
        select(func.count()).select_from(QueueEntry).where(*filters)
    ).scalar_one()
    entries = list(
        db.execute(
            select(QueueEntry)
            .where(*filters)
            .order_by(QueueEntry.finished_at.desc(), QueueEntry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
    )

    participant_ids = {
        entry.submitted_by_participant_id
        for entry in entries
        if entry.submitted_by_participant_id
    }
    names_by_id = _participant_display_names(db, participant_ids)

    return HistoryListResponse(
        entries=[
            HistoryQueueEntryRead(
                **QueueEntryRead.model_validate(entry).model_dump(),
                finished_at=entry.finished_at or entry.created_at,
                submitted_by_display_name=(
                    names_by_id.get(entry.submitted_by_participant_id)
                    if entry.submitted_by_participant_id
                    else None
                ),
                source=entry.source,
            )
            for entry in entries
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def requeue_from_history(db: Session, entry_id: str) -> QueueEntry:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="queue entry not found"
        )
    if entry.status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invalid status transition",
        )
    if _has_video_conflict(db, entry.youtube_video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )

    priority = (
        QueueEntryPriority.normal.value
        if entry.submitted_by_participant_id
        else QueueEntryPriority.low.value
    )
    new_entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=entry.youtube_video_id,
        title=entry.title,
        thumbnail_url=entry.thumbnail_url,
        duration_sec=entry.duration_sec,
        status=QueueEntryStatus.pending_review,
        original_query=entry.original_query,
        vote_count=0,
        submitted_by_participant_id=entry.submitted_by_participant_id,
        priority=priority,
        source=QueueEntrySource.operator_requeue.value,
    )
    db.add(new_entry)
    db.flush()
    _enqueue_entry(db, new_entry)
    bump_revision(db)
    return new_entry


def create_operator_queued_entry(
    db: Session,
    youtube_url_or_id: str,
    search_query: str | None = None,
) -> QueueEntry:
    video_id, title, thumbnail, duration_sec, original_query = _resolve_youtube_entry_fields(
        db, youtube_url_or_id, search_query
    )
    if _has_video_conflict(db, video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=thumbnail,
        duration_sec=duration_sec,
        status=QueueEntryStatus.pending_review,
        original_query=original_query,
        vote_count=0,
        priority=QueueEntryPriority.low.value,
        source=QueueEntrySource.operator_direct.value,
    )
    db.add(entry)
    db.flush()
    _enqueue_entry(db, entry)
    bump_revision(db)
    return entry


def create_pending_entry(db: Session, youtube_url_or_id: str) -> QueueEntry:
    video_id, title, thumbnail, duration_sec, original_query = _resolve_youtube_entry_fields(
        db, youtube_url_or_id, None
    )
    if _has_video_conflict(db, video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=thumbnail,
        duration_sec=duration_sec,
        status=QueueEntryStatus.pending_review,
        original_query=original_query,
        vote_count=0,
        priority=QueueEntryPriority.normal.value,
        source=QueueEntrySource.participant.value,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    bump_revision(db)
    return entry


def _count_participant_pending(db: Session, participant_id: str) -> int:
    return (
        db.execute(
            select(func.count())
            .select_from(QueueEntry)
            .where(
                QueueEntry.submitted_by_participant_id == participant_id,
                QueueEntry.status == QueueEntryStatus.pending_review,
            )
        ).scalar_one()
    )


def _count_participant_queued(db: Session, participant_id: str) -> int:
    return (
        db.execute(
            select(func.count())
            .select_from(QueueEntry)
            .where(
                QueueEntry.submitted_by_participant_id == participant_id,
                QueueEntry.status == QueueEntryStatus.queued,
            )
        ).scalar_one()
    )


def _enqueue_entry(db: Session, entry: QueueEntry) -> QueueEntry:
    if _count_queued(db) >= MAX_QUEUED_ENTRIES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="queue is full",
        )
    if _has_active_duplicate(db, entry.youtube_video_id, exclude_id=entry.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )

    entry.status = QueueEntryStatus.queued
    entry.approved_at = datetime.now(timezone.utc)
    entry.position = _next_position(db)
    db.commit()
    db.refresh(entry)
    _recompute_positions(db)
    emit_song_approved(entry)
    _maybe_auto_start_playback(db)
    return entry


def _maybe_auto_start_playback(db: Session) -> None:
    if get_now_playing(db) is not None:
        return
    next_entry = _top_queued(db)
    if next_entry is None:
        from .filler_reserve_service import inject_next_if_idle

        inject_next_if_idle(db)
        next_entry = _top_queued(db)
    if next_entry is None:
        return
    runtime = get_or_create_runtime(db)
    emit_song_up_next(next_entry)
    next_entry.status = QueueEntryStatus.playing
    next_entry.position = None
    runtime.now_playing_entry_id = next_entry.id
    db.commit()
    _recompute_positions(db)


def submit_as_participant(
    db: Session,
    participant_id: str,
    youtube_url_or_id: str,
    search_query: str | None = None,
) -> QueueEntry:
    video_id, title, thumbnail, duration_sec, original_query = _resolve_youtube_entry_fields(
        db, youtube_url_or_id, search_query
    )

    mode = get_queue_mode(db)
    max_submissions = get_settings().max_pending_submissions_per_participant

    if mode == QueueMode.moderated:
        pending_count = _count_participant_pending(db, participant_id)
        if pending_count >= max_submissions:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="pending submission limit reached",
            )
    else:
        queued_count = _count_participant_queued(db, participant_id)
        if queued_count >= max_submissions:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="pending submission limit reached",
            )

    if _has_video_conflict(db, video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )

    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=thumbnail,
        duration_sec=duration_sec,
        status=QueueEntryStatus.pending_review,
        original_query=original_query,
        vote_count=0,
        submitted_by_participant_id=participant_id,
        priority=QueueEntryPriority.normal.value,
        source=QueueEntrySource.participant.value,
    )
    db.add(entry)
    db.flush()

    if mode == QueueMode.moderated:
        if _count_participant_pending(db, participant_id) > max_submissions:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="pending submission limit reached",
            )
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(entry)
        bump_revision(db)
        return entry

    if _count_participant_queued(db, participant_id) >= max_submissions:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="pending submission limit reached",
        )
    try:
        _enqueue_entry(db, entry)
    except Exception:
        db.rollback()
        raise
    bump_revision(db)
    return entry


def list_participant_submissions(db: Session, participant_id: str) -> list[QueueEntry]:
    return list(
        db.execute(
            select(QueueEntry)
            .where(QueueEntry.submitted_by_participant_id == participant_id)
            .order_by(QueueEntry.created_at.desc(), QueueEntry.id.desc())
        ).scalars().all()
    )


def approve_entry(db: Session, entry_id: str) -> QueueEntry:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="queue entry not found")
    if entry.status != QueueEntryStatus.pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invalid status transition",
        )
    if not entry.priority:
        entry.priority = QueueEntryPriority.normal.value
    if not entry.source:
        entry.source = QueueEntrySource.participant.value
    entry = _enqueue_entry(db, entry)
    bump_revision(db)
    return entry


def reject_entry(db: Session, entry_id: str, reason: str | None) -> QueueEntry:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="queue entry not found")
    if entry.status != QueueEntryStatus.pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="invalid status transition",
        )
    entry.status = QueueEntryStatus.rejected
    entry.rejection_reason = reason[:200] if reason else None
    entry.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    bump_revision(db)
    return entry


def skip_or_advance(db: Session) -> StateResponse:
    from .filler_reserve_service import inject_next_if_idle

    runtime = get_or_create_runtime(db)
    current = get_now_playing(db)
    if current is not None:
        current.status = QueueEntryStatus.played
        current.position = None
        current.finished_at = datetime.now(timezone.utc)
        runtime.now_playing_entry_id = None
        db.commit()

        next_entry = _top_queued(db)
        if next_entry is None:
            inject_next_if_idle(db)
            next_entry = _top_queued(db)
        if next_entry is not None:
            emit_song_up_next(next_entry)
            next_entry.status = QueueEntryStatus.playing
            next_entry.position = None
            runtime.now_playing_entry_id = next_entry.id
            db.commit()
        _recompute_positions(db)
        bump_revision(db)
        return build_state_response(db)

    next_entry = _top_queued(db)
    if next_entry is None:
        inject_next_if_idle(db)
        next_entry = _top_queued(db)
    if next_entry is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="nothing to advance",
        )

    emit_song_up_next(next_entry)
    next_entry.status = QueueEntryStatus.playing
    next_entry.position = None
    runtime.now_playing_entry_id = next_entry.id
    db.commit()
    _recompute_positions(db)
    bump_revision(db)
    return build_state_response(db)
