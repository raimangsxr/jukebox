from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

_WINDOW = timedelta(minutes=5)
_LIMIT = 10
# Periodically drop buckets for participants who have gone idle so memory stays
# bounded to recently-active participants (010-hardening-and-polish, FR-010).
_SWEEP_EVERY = 256

_timestamps: dict[str, deque[datetime]] = defaultdict(deque)
_calls_since_sweep = 0


def _sweep(now: datetime) -> None:
    window_start = now - _WINDOW
    stale = [
        participant_id
        for participant_id, bucket in _timestamps.items()
        if not bucket or bucket[-1] < window_start
    ]
    for participant_id in stale:
        del _timestamps[participant_id]


def _maybe_sweep(now: datetime) -> None:
    global _calls_since_sweep
    _calls_since_sweep += 1
    if _calls_since_sweep >= _SWEEP_EVERY:
        _calls_since_sweep = 0
        _sweep(now)


def check_and_record(participant_id: str, now: datetime | None = None) -> bool:
    """Return True if search is allowed; record timestamp when allowed."""
    now = now or datetime.now(timezone.utc)
    _maybe_sweep(now)
    window_start = now - _WINDOW
    bucket = _timestamps[participant_id]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= _LIMIT:
        return False
    bucket.append(now)
    return True


def reset_for_tests() -> None:
    global _calls_since_sweep
    _timestamps.clear()
    _calls_since_sweep = 0
