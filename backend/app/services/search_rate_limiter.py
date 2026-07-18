from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

_WINDOW = timedelta(minutes=5)
_LIMIT = 10

_timestamps: dict[str, deque[datetime]] = defaultdict(deque)


def check_and_record(participant_id: str, now: datetime | None = None) -> bool:
    """Return True if search is allowed; record timestamp when allowed."""
    now = now or datetime.now(timezone.utc)
    window_start = now - _WINDOW
    bucket = _timestamps[participant_id]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= _LIMIT:
        return False
    bucket.append(now)
    return True


def reset_for_tests() -> None:
    _timestamps.clear()
