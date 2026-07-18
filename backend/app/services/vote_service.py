from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import QueueEntry, QueueEntryStatus, Vote
from .queue_service import _recompute_positions
from .state_service import build_participant_state_response, bump_revision

MAX_VOTES_PER_WINDOW = 2
WINDOW = timedelta(minutes=5)


def count_votes_in_window(
    db: Session,
    participant_id: str,
    *,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(timezone.utc)
    cutoff = now - WINDOW
    return db.execute(
        select(func.count())
        .select_from(Vote)
        .where(
            Vote.participant_id == participant_id,
            Vote.created_at >= cutoff,
        )
    ).scalar_one()


def votes_remaining(db: Session, participant_id: str) -> int:
    return max(0, MAX_VOTES_PER_WINDOW - count_votes_in_window(db, participant_id))


def cast_vote(db: Session, participant_id: str, queue_entry_id: str) -> Vote:
    entry = db.get(QueueEntry, queue_entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="queue entry not found",
        )
    if entry.status != QueueEntryStatus.queued:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="entry not votable",
        )
    if count_votes_in_window(db, participant_id) >= MAX_VOTES_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="vote limit exceeded",
        )

    vote = Vote(
        id=str(uuid4()),
        queue_entry_id=queue_entry_id,
        participant_id=participant_id,
    )
    db.add(vote)
    entry.vote_count += 1
    db.commit()
    _recompute_positions(db)
    bump_revision(db)
    db.refresh(vote)
    return vote
