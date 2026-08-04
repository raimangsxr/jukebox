from datetime import datetime, timezone
from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    EVENT_CONFIG_SINGLETON_ID,
    MAX_FILLER_RESERVE_ENTRIES,
    EventConfig,
    FillerReserveEntry,
    QueueEntry,
    QueueEntryPriority,
    QueueEntrySource,
    QueueEntryStatus,
)
from ..schemas import (
    FillerReserveBatchLineError,
    FillerReserveBatchValidation,
    FillerReserveEntryRead,
)
from .queue_service import (
    ACTIVE_DUPLICATE_STATUSES,
    _enqueue_entry,
    _has_active_duplicate,
    _has_video_conflict,
    _resolve_youtube_entry_fields,
)
from .state_service import bump_revision
from .youtube_meta import (
    fetch_youtube_videos_details_batch,
    parse_youtube_video_id,
    resolve_playlist_or_video_ids,
)

CSV_BOM = "\ufeff"
WATCH_URL_TEMPLATE = "https://www.youtube.com/watch?v={video_id}"


@dataclass
class ParsedImportLine:
    line_number: int
    raw: str


@dataclass
class PendingImportEntry:
    line_number: int
    video_id: str
    original_query: str


@dataclass
class ResolvedImportEntry:
    youtube_video_id: str
    title: str
    thumbnail_url: str | None
    duration_sec: int | None
    original_query: str


@dataclass
class BatchLineInput:
    line_number: int
    raw: str
    video_id: str | None = None


@dataclass
class BatchValidationResult:
    validation: FillerReserveBatchValidation
    to_append: list[ResolvedImportEntry]


@dataclass
class ImportValidationResult:
    validation: FillerReserveBatchValidation
    to_append: list[ResolvedImportEntry]


def list_reserve(db: Session) -> list[FillerReserveEntry]:
    return list(
        db.execute(
            select(FillerReserveEntry).order_by(FillerReserveEntry.position.asc())
        ).scalars().all()
    )


def list_reserve_reads(db: Session) -> list[FillerReserveEntryRead]:
    return [FillerReserveEntryRead.model_validate(e) for e in list_reserve(db)]


def _next_reserve_position(db: Session) -> int:
    current_max = db.execute(select(func.max(FillerReserveEntry.position))).scalar_one()
    return (current_max or 0) + 1


def _count_reserve(db: Session) -> int:
    return db.execute(select(func.count()).select_from(FillerReserveEntry)).scalar_one()


def add_to_reserve(
    db: Session,
    youtube_url_or_id: str,
    search_query: str | None = None,
) -> FillerReserveEntry:
    if _count_reserve(db) >= MAX_FILLER_RESERVE_ENTRIES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="filler reserve is full",
        )
    video_id, title, thumbnail, duration_sec, original_query = _resolve_youtube_entry_fields(
        db, youtube_url_or_id, search_query
    )
    if _has_video_conflict(db, video_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="video already in queue",
        )
    entry = FillerReserveEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=thumbnail,
        duration_sec=duration_sec,
        original_query=original_query,
        position=_next_reserve_position(db),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_from_reserve(db: Session, entry_id: str) -> None:
    entry = db.get(FillerReserveEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="filler reserve entry not found",
        )
    db.delete(entry)
    db.commit()
    _renumber_reserve_positions(db)


def reorder_reserve(db: Session, ordered_ids: list[str]) -> list[FillerReserveEntryRead]:
    entries = list_reserve(db)
    if len(ordered_ids) != len(entries):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ordered_ids must include all reserve entries",
        )
    by_id = {e.id: e for e in entries}
    if set(ordered_ids) != set(by_id.keys()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ordered_ids must match reserve entries",
        )
    for index, entry_id in enumerate(ordered_ids, start=1):
        by_id[entry_id].position = index
    db.commit()
    return list_reserve_reads(db)


def _renumber_reserve_positions(db: Session) -> None:
    entries = list_reserve(db)
    for index, entry in enumerate(entries, start=1):
        entry.position = index
    db.commit()


def _create_queue_entry_from_reserve(
    db: Session,
    reserve_entry: FillerReserveEntry,
    *,
    source: QueueEntrySource,
) -> QueueEntry:
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=reserve_entry.youtube_video_id,
        title=reserve_entry.title,
        thumbnail_url=reserve_entry.thumbnail_url,
        duration_sec=reserve_entry.duration_sec,
        status=QueueEntryStatus.pending_review,
        original_query=reserve_entry.original_query,
        vote_count=0,
        priority=QueueEntryPriority.low.value,
        source=source.value,
    )
    db.add(entry)
    db.flush()
    return entry


def transfer_to_queue(
    db: Session,
    reserve_ids: list[str],
    *,
    source: QueueEntrySource = QueueEntrySource.operator_filler,
) -> list[QueueEntry]:
    created: list[QueueEntry] = []
    for reserve_id in reserve_ids:
        reserve_entry = db.get(FillerReserveEntry, reserve_id)
        if reserve_entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="filler reserve entry not found",
            )
        entry = _create_queue_entry_from_reserve(db, reserve_entry, source=source)
        db.delete(reserve_entry)
        db.flush()
        try:
            _enqueue_entry(db, entry)
        except Exception:
            db.rollback()
            raise
        created.append(entry)
    _renumber_reserve_positions(db)
    bump_revision(db)
    return created


def inject_next_if_idle(db: Session) -> QueueEntry | None:
    config = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    if config is None or not config.filler_auto_inject_enabled:
        return None

    from .queue_service import _count_queued
    from .state_service import get_now_playing

    if get_now_playing(db) is not None:
        return None
    if _count_queued(db) > 0:
        return None

    reserve_entry = db.execute(
        select(FillerReserveEntry)
        .order_by(FillerReserveEntry.position.asc())
        .limit(1)
    ).scalar_one_or_none()
    if reserve_entry is None:
        return None

    entry = _create_queue_entry_from_reserve(
        db, reserve_entry, source=QueueEntrySource.auto_inject
    )
    db.delete(reserve_entry)
    db.flush()
    _renumber_reserve_positions(db)
    _enqueue_entry(db, entry)
    bump_revision(db)
    return entry


def export_reserve_csv(db: Session) -> bytes:
    lines = ["url"]
    for entry in list_reserve(db):
        lines.append(WATCH_URL_TEMPLATE.format(video_id=entry.youtube_video_id))
    body = "\n".join(lines)
    if lines:
        body += "\n"
    return (CSV_BOM + body).encode("utf-8")


def parse_import_file(content: bytes) -> list[ParsedImportLine]:
    text = content.decode("utf-8-sig")
    parsed: list[ParsedImportLine] = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if index == 1 and line.lower() == "url":
            continue
        parsed.append(ParsedImportLine(line_number=index, raw=line))
    return parsed


def _active_queue_video_ids(db: Session) -> set[str]:
    rows = db.execute(
        select(QueueEntry.youtube_video_id).where(
            QueueEntry.status.in_(ACTIVE_DUPLICATE_STATUSES)
        )
    ).scalars().all()
    return set(rows)


def clear_reserve(db: Session) -> None:
    for entry in list_reserve(db):
        db.delete(entry)
    db.commit()
    bump_revision(db)


def append_reserve_entries(
    db: Session, resolved: list[ResolvedImportEntry]
) -> list[FillerReserveEntryRead]:
    position = _next_reserve_position(db)
    for item in resolved:
        db.add(
            FillerReserveEntry(
                id=str(uuid4()),
                youtube_video_id=item.youtube_video_id,
                title=item.title,
                thumbnail_url=item.thumbnail_url,
                duration_sec=item.duration_sec,
                original_query=item.original_query,
                position=position,
            )
        )
        position += 1
    db.commit()
    bump_revision(db)
    return list_reserve_reads(db)


def _empty_batch_validation(
    *,
    errors: list[FillerReserveBatchLineError] | None = None,
) -> FillerReserveBatchValidation:
    return FillerReserveBatchValidation(
        add_count=0,
        skipped_in_reserve=0,
        skipped_in_queue=0,
        skipped_unresolvable=0,
        skipped_capacity=0,
        can_confirm=False,
        errors=errors or [],
    )


def validate_batch(
    db: Session,
    lines: list[BatchLineInput],
    *,
    duplicate_detail: str = "duplicate in file",
) -> BatchValidationResult:
    errors: list[FillerReserveBatchLineError] = []
    seen_video_ids: set[str] = set()
    candidates: list[tuple[int, str, str]] = []

    for line in lines:
        video_id = line.video_id if line.video_id is not None else parse_youtube_video_id(line.raw)
        if not video_id:
            errors.append(
                FillerReserveBatchLineError(
                    line=line.line_number,
                    detail="invalid youtube reference",
                )
            )
            continue
        if video_id in seen_video_ids:
            errors.append(
                FillerReserveBatchLineError(
                    line=line.line_number,
                    detail=duplicate_detail,
                )
            )
            continue
        seen_video_ids.add(video_id)
        candidates.append((line.line_number, line.raw, video_id))

    if errors:
        return BatchValidationResult(
            validation=_empty_batch_validation(errors=errors),
            to_append=[],
        )

    if not candidates:
        return BatchValidationResult(
            validation=_empty_batch_validation(),
            to_append=[],
        )

    reserve_ids = {entry.youtube_video_id for entry in list_reserve(db)}
    queue_ids = _active_queue_video_ids(db)
    slots_left = max(0, MAX_FILLER_RESERVE_ENTRIES - _count_reserve(db))

    details = fetch_youtube_videos_details_batch(
        [video_id for _, _, video_id in candidates], db
    )

    skipped_in_reserve = 0
    skipped_in_queue = 0
    skipped_unresolvable = 0
    skipped_capacity = 0
    to_append: list[ResolvedImportEntry] = []

    for line_number, raw, video_id in candidates:
        if video_id in reserve_ids:
            skipped_in_reserve += 1
            continue
        if video_id in queue_ids:
            skipped_in_queue += 1
            continue
        item = details.get(video_id)
        if item is None:
            skipped_unresolvable += 1
            continue
        if len(to_append) >= slots_left:
            skipped_capacity += 1
            continue
        title, thumbnail, duration_sec = item
        to_append.append(
            ResolvedImportEntry(
                youtube_video_id=video_id,
                title=title,
                thumbnail_url=thumbnail,
                duration_sec=duration_sec,
                original_query=raw,
            )
        )

    add_count = len(to_append)
    validation = FillerReserveBatchValidation(
        add_count=add_count,
        skipped_in_reserve=skipped_in_reserve,
        skipped_in_queue=skipped_in_queue,
        skipped_unresolvable=skipped_unresolvable,
        skipped_capacity=skipped_capacity,
        can_confirm=add_count > 0,
        errors=[],
    )
    return BatchValidationResult(validation=validation, to_append=to_append)


def _playlist_blocking_result(detail: str) -> BatchValidationResult:
    return BatchValidationResult(
        validation=_empty_batch_validation(
            errors=[FillerReserveBatchLineError(line=1, detail=detail)]
        ),
        to_append=[],
    )


def validate_playlist_url(db: Session, url: str) -> BatchValidationResult:
    try:
        resolved = resolve_playlist_or_video_ids(url, db)
    except ValueError as exc:
        return _playlist_blocking_result(str(exc))

    lines = [
        BatchLineInput(line_number=index, raw=raw, video_id=video_id)
        for index, video_id, raw in resolved
    ]
    return validate_batch(db, lines, duplicate_detail="duplicate in batch")


def commit_playlist_url(
    db: Session, url: str
) -> tuple[list[FillerReserveEntryRead] | None, FillerReserveBatchValidation]:
    result = validate_playlist_url(db, url)
    if not result.validation.can_confirm:
        return None, result.validation
    return append_reserve_entries(db, result.to_append), result.validation


def validate_import_file(db: Session, content: bytes) -> ImportValidationResult:
    parsed = parse_import_file(content)
    lines = [
        BatchLineInput(line_number=line.line_number, raw=line.raw)
        for line in parsed
    ]
    batch = validate_batch(db, lines, duplicate_detail="duplicate in file")
    return ImportValidationResult(validation=batch.validation, to_append=batch.to_append)


def commit_import_file(
    db: Session, content: bytes
) -> tuple[list[FillerReserveEntryRead] | None, FillerReserveBatchValidation]:
    result = validate_import_file(db, content)
    if not result.validation.can_confirm:
        return None, result.validation
    return append_reserve_entries(db, result.to_append), result.validation
