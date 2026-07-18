from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Participant
from ..schemas import (
    ParticipantDevAuthRequest,
    ParticipantMeResponse,
    ParticipantRead,
    ParticipantStateResponse,
    QueueEntryRead,
    SubmissionListResponse,
)
from ..security import CurrentParticipant
from ..services import queue_service
from ..services.participant_session import set_participant_cookie
from ..services.state_service import build_participant_state_response


router = APIRouter(prefix="/api/participant", tags=["participant"])


@router.get("/me", response_model=ParticipantMeResponse)
def participant_me(
    participant: CurrentParticipant,
) -> ParticipantMeResponse:
    return ParticipantMeResponse(participant=ParticipantRead.model_validate(participant))


@router.get("/state", response_model=ParticipantStateResponse)
def participant_state(
    participant: CurrentParticipant,
    db: Session = Depends(get_db),
) -> ParticipantStateResponse:
    return build_participant_state_response(db, participant.id)


@router.get("/submissions", response_model=SubmissionListResponse)
def participant_submissions(
    participant: CurrentParticipant,
    db: Session = Depends(get_db),
) -> SubmissionListResponse:
    entries = queue_service.list_participant_submissions(db, participant.id)
    return SubmissionListResponse(
        entries=[QueueEntryRead.model_validate(entry) for entry in entries]
    )


@router.post("/dev-auth", response_model=ParticipantMeResponse)
def participant_dev_auth(
    response: Response,
    body: ParticipantDevAuthRequest | None = None,
    db: Session = Depends(get_db),
) -> ParticipantMeResponse:
    settings = get_settings()
    if not settings.allow_dev_participant_auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    display_name = body.display_name if body else "Participante"
    participant = Participant(
        id=str(uuid4()),
        display_name=display_name,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    set_participant_cookie(response, participant.id)
    return ParticipantMeResponse(participant=ParticipantRead.model_validate(participant))
