"""Search rate-limiter DB-backed limits (022)."""

from datetime import datetime, timezone
from uuid import uuid4

from app.models import Participant
from app.services import search_rate_limiter as rl


def test_limit_enforced_within_window(db_session):
    participant = Participant(id=str(uuid4()), display_name="p1")
    db_session.add(participant)
    db_session.commit()

    now = datetime(2021, 6, 1, 12, 0, tzinfo=timezone.utc)
    limit = rl._limit()
    for _ in range(limit):
        assert rl.can_search(db_session, participant.id, now=now) is True
        rl.record_search(db_session, participant.id, now=now)
        db_session.commit()
    assert rl.can_search(db_session, participant.id, now=now) is False


def test_reset_for_tests_is_noop():
    rl.reset_for_tests()
