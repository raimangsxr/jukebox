from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Participant, QueueEntry, QueueEntryStatus, Vote
from .limit_window_service import (
    ensure_utc,
    expire_reset_at,
    new_reset_at,
    remaining_quota,
    should_start_window,
    sql_utc,
    utc_now,
    window_start,
)
from .queue_service import _recompute_positions
from .state_service import bump_revision


def _max_votes_per_window() -> int:
    return get_settings().max_votes_10minutes_per_participant


def _count_votes_in_active_window(
    db: Session,
    participant_id: str,
    reset_at: datetime,
    *,
    now: datetime,
) -> int:
    start = sql_utc(window_start(ensure_utc(reset_at)))
    compare_now = sql_utc(now)
    return db.execute(
        select(func.count())
        .select_from(Vote)
        .where(
            Vote.participant_id == participant_id,
            Vote.created_at >= start,
            Vote.created_at <= compare_now,
        )
    ).scalar_one()


def vote_limit_state(
    db: Session,
    participant_id: str,
    *,
    now: datetime | None = None,
) -> tuple[int, datetime | None]:
    now = now or utc_now()
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="participant not found",
        )

    expired = expire_reset_at(now, participant.votes_quota_reset_at)
    if expired != participant.votes_quota_reset_at:
        participant.votes_quota_reset_at = expired
        db.flush()

    reset_at = participant.votes_quota_reset_at
    max_votes = _max_votes_per_window()
    used = (
        _count_votes_in_active_window(db, participant_id, reset_at, now=now)
        if reset_at is not None
        else 0
    )
    return remaining_quota(max_votes, used), reset_at


def votes_remaining(db: Session, participant_id: str) -> int:
    remaining, _ = vote_limit_state(db, participant_id)
    return remaining


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

    now = utc_now()
    remaining, _ = vote_limit_state(db, participant_id, now=now)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="vote limit exceeded",
        )

    participant = db.get(Participant, participant_id)
    assert participant is not None
    if should_start_window(remaining, _max_votes_per_window()):
        participant.votes_quota_reset_at = new_reset_at(now)

    vote = Vote(
        id=str(uuid4()),
        queue_entry_id=queue_entry_id,
        participant_id=participant_id,
        created_at=now,
    )
    db.add(vote)
    entry.vote_count += 1
    db.commit()
    _recompute_positions(db)
    bump_revision(db)
    db.refresh(vote)
    return vote
