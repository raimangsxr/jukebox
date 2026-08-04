from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas import (
    DevSubmitRequest,
    HistoryListResponse,
    OperatorQueueSubmitRequest,
    PendingListResponse,
    ActiveQueueListResponse,
    QueueEntryRead,
    RejectBody,
    StateResponse,
    SubmitRequest,
    VoteCountUpdateRequest,
)
from ..security import CurrentParticipant, CurrentUser
from ..services import queue_service


router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("/history", response_model=HistoryListResponse)
def get_queue_history(
    _user: CurrentUser,
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> HistoryListResponse:
    return queue_service.list_history(
        db, status_filter=status, page=page, page_size=page_size
    )


@router.delete("/history", status_code=204)
def clear_queue_history(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    queue_service.clear_history(db)


@router.get("/active", response_model=ActiveQueueListResponse)
def get_active_queue(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> ActiveQueueListResponse:
    return queue_service.list_active_queue(db)


@router.delete("/active", response_model=StateResponse)
def clear_active_queue(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> StateResponse:
    return queue_service.clear_active_queue(db)


@router.delete("/active/{entry_id}", response_model=StateResponse)
def delete_active_queue_entry(
    entry_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> StateResponse:
    return queue_service.delete_active_entry(db, entry_id)


@router.post("/history/{entry_id}/requeue", response_model=QueueEntryRead, status_code=201)
def requeue_history_entry(
    entry_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    entry = queue_service.requeue_from_history(db, entry_id)
    return QueueEntryRead.model_validate(entry)


@router.post("/operator-submit", response_model=QueueEntryRead, status_code=201)
def operator_submit_to_queue(
    body: OperatorQueueSubmitRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    entry = queue_service.create_operator_queued_entry(
        db, body.youtube_url_or_id, body.search_query
    )
    return QueueEntryRead.model_validate(entry)


@router.get("/pending", response_model=PendingListResponse)
def get_pending(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> PendingListResponse:
    entries = queue_service.list_pending_for_moderation(db)
    return PendingListResponse(entries=entries)


@router.post("/{entry_id}/approve", response_model=QueueEntryRead)
def approve_entry(
    entry_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    entry = queue_service.approve_entry(db, entry_id)
    return QueueEntryRead.model_validate(entry)


@router.post("/{entry_id}/reject", response_model=QueueEntryRead)
def reject_entry(
    entry_id: str,
    body: RejectBody,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    entry = queue_service.reject_entry(db, entry_id, body.reason)
    return QueueEntryRead.model_validate(entry)


@router.post("/skip", response_model=StateResponse)
def skip_queue(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> StateResponse:
    return queue_service.skip_or_advance(db)


@router.post("/{entry_id}/play-now", response_model=StateResponse)
def play_queue_entry_now(
    entry_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> StateResponse:
    return queue_service.force_play_entry(db, entry_id)


@router.patch("/{entry_id}/vote-count", response_model=StateResponse)
def update_queue_entry_vote_count(
    entry_id: str,
    body: VoteCountUpdateRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> StateResponse:
    return queue_service.set_entry_vote_count(db, entry_id, body.vote_count)


@router.post("/dev-submit", response_model=QueueEntryRead, status_code=201)
def dev_submit(
    body: DevSubmitRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    settings = get_settings()
    if not settings.allow_dev_queue_submit:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    entry = queue_service.create_pending_entry(db, body.youtube_url_or_id)
    return QueueEntryRead.model_validate(entry)


@router.post("/submit", response_model=QueueEntryRead, status_code=201)
def participant_submit(
    body: SubmitRequest,
    participant: CurrentParticipant,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    entry = queue_service.submit_as_participant(
        db, participant.id, body.youtube_url_or_id, body.search_query
    )
    return QueueEntryRead.model_validate(entry)
