from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Participant, ParticipantSearch
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


def _limit() -> int:
    return get_settings().max_searchs_10minutes_per_participant


def _count_searches_in_active_window(
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
        .select_from(ParticipantSearch)
        .where(
            ParticipantSearch.participant_id == participant_id,
            ParticipantSearch.created_at >= start,
            ParticipantSearch.created_at <= compare_now,
        )
    ).scalar_one()


def search_limit_state(
    db: Session,
    participant_id: str,
    *,
    now: datetime | None = None,
) -> tuple[int, datetime | None]:
    now = now or utc_now()
    participant = db.get(Participant, participant_id)
    if participant is None:
        return _limit(), None

    expired = expire_reset_at(now, participant.searches_quota_reset_at)
    if expired != participant.searches_quota_reset_at:
        participant.searches_quota_reset_at = expired
        db.flush()

    reset_at = participant.searches_quota_reset_at
    max_searches = _limit()
    used = (
        _count_searches_in_active_window(db, participant_id, reset_at, now=now)
        if reset_at is not None
        else 0
    )
    return remaining_quota(max_searches, used), reset_at


def can_search(
    db: Session,
    participant_id: str,
    *,
    now: datetime | None = None,
) -> bool:
    remaining, _ = search_limit_state(db, participant_id, now=now)
    return remaining > 0


def record_search(
    db: Session,
    participant_id: str,
    *,
    now: datetime | None = None,
) -> None:
    now = now or utc_now()
    participant = db.get(Participant, participant_id)
    if participant is None:
        return

    remaining, _ = search_limit_state(db, participant_id, now=now)
    if should_start_window(remaining, _limit()):
        participant.searches_quota_reset_at = new_reset_at(now)

    db.add(
        ParticipantSearch(
            id=str(uuid4()),
            participant_id=participant_id,
            created_at=now,
        )
    )
    db.flush()


def reset_for_tests() -> None:
    """No-op: search limits are DB-backed (022). Kept for test fixture compatibility."""
