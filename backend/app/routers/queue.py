from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas import (
    DevSubmitRequest,
    PendingListResponse,
    QueueEntryRead,
    RejectBody,
    StateResponse,
    SubmitRequest,
)
from ..security import CurrentParticipant, CurrentUser
from ..services import queue_service


router = APIRouter(prefix="/api/queue", tags=["queue"])


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
