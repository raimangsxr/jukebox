from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ParticipantStateResponse, VoteCreateRequest, VoteResponse
from ..security import CurrentParticipant
from ..services.state_service import build_participant_state_response
from ..services.vote_service import cast_vote, votes_remaining


router = APIRouter(prefix="/api", tags=["votes"])


@router.post("/votes", response_model=VoteResponse, status_code=201)
def create_vote(
    body: VoteCreateRequest,
    participant: CurrentParticipant,
    db: Session = Depends(get_db),
) -> VoteResponse:
    vote = cast_vote(db, participant.id, body.queue_entry_id)
    state = build_participant_state_response(db, participant.id)
    return VoteResponse(
        id=vote.id,
        votes_remaining=votes_remaining(db, participant.id),
        state=state,
    )
