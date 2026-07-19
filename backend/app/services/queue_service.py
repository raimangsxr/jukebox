from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (
    MAX_QUEUED_ENTRIES,
    Participant,
    QueueEntry,
    QueueEntryStatus,
)
from ..schemas import PendingQueueEntryRead, QueueEntryRead, StateResponse
from .notification_service import emit_song_approved, emit_song_up_next
from .state_service import build_state_response, bump_revision, get_now_playing, get_or_create_runtime
from .youtube_meta import (
    fetch_youtube_duration_sec,
    fetch_youtube_metadata,
    fetch_youtube_metadata_strict,
    parse_youtube_video_id,
)

ACTIVE_DUPLICATE_STATUSES = (
    QueueEntryStatus.pending_review,
    QueueEntryStatus.queued,
    QueueEntryStatus.playing,
)


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


def _has_active_duplicate(db: Session, youtube_video_id: str, exclude_id: str | None = None) -> bool:
    stmt = select(QueueEntry.id).where(
        QueueEntry.youtube_video_id == youtube_video_id,
        QueueEntry.status.in_(ACTIVE_DUPLICATE_STATUSES),
    )
    if exclude_id:
        stmt = stmt.where(QueueEntry.id != exclude_id)
    return db.execute(stmt).first() is not None


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
        .order_by(QueueEntry.vote_count.desc(), QueueEntry.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()


def _recompute_positions(db: Session) -> None:
    entries = db.execute(
        select(QueueEntry)
        .where(QueueEntry.status == QueueEntryStatus.queued)
        .order_by(QueueEntry.vote_count.desc(), QueueEntry.created_at.asc())
    ).scalars().all()
    for index, entry in enumerate(entries, start=1):
        entry.position = index
    db.commit()


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
    names_by_id: dict[str, str] = {}
    if participant_ids:
        participants = db.execute(
            select(Participant).where(Participant.id.in_(participant_ids))
        ).scalars().all()
        names_by_id = {participant.id: participant.display_name for participant in participants}

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


def create_pending_entry(db: Session, youtube_url_or_id: str) -> QueueEntry:
    video_id = parse_youtube_video_id(youtube_url_or_id)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid youtube reference",
        )
    if _has_active_duplicate(db, video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )
    title, thumbnail = fetch_youtube_metadata(video_id)
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=thumbnail,
        duration_sec=fetch_youtube_duration_sec(video_id, db),
        status=QueueEntryStatus.pending_review,
        original_query=youtube_url_or_id.strip(),
        vote_count=0,
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


def submit_as_participant(
    db: Session,
    participant_id: str,
    youtube_url_or_id: str,
    search_query: str | None = None,
) -> QueueEntry:
    video_id = parse_youtube_video_id(youtube_url_or_id)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid youtube reference",
        )

    pending_count = _count_participant_pending(db, participant_id)
    max_pending = get_settings().max_pending_submissions_per_participant
    if pending_count >= max_pending:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="pending submission limit reached",
        )

    if _has_active_duplicate(db, video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
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

    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=thumbnail,
        duration_sec=fetch_youtube_duration_sec(video_id, db),
        status=QueueEntryStatus.pending_review,
        original_query=original_query,
        vote_count=0,
        submitted_by_participant_id=participant_id,
    )
    db.add(entry)
    db.flush()
    if _count_participant_pending(db, participant_id) > max_pending:
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
    bump_revision(db)
    emit_song_approved(entry)
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
    db.commit()
    db.refresh(entry)
    bump_revision(db)
    return entry


def skip_or_advance(db: Session) -> StateResponse:
    runtime = get_or_create_runtime(db)
    current = get_now_playing(db)
    if current is not None:
        current.status = QueueEntryStatus.played
        current.position = None
        runtime.now_playing_entry_id = None
        db.commit()

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
