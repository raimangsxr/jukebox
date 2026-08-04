"""Fixed-window quota helpers for participant vote and search limits.

Window starts on first consumption at full quota; ``reset_at`` is set once and
cleared when ``now >= reset_at`` (full quota restored).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def window_duration() -> timedelta:
    # Same 10-minute deployment window as JUKEBOX_MAX_* limit env vars (016/022).
    return timedelta(minutes=10)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def expire_reset_at(now: datetime, reset_at: datetime | None) -> datetime | None:
    if reset_at is None:
        return None
    if ensure_utc(now) >= ensure_utc(reset_at):
        return None
    return reset_at


def window_start(reset_at: datetime) -> datetime:
    return reset_at - window_duration()


def remaining_quota(max_quota: int, used: int) -> int:
    return max(0, max_quota - used)


def should_start_window(remaining_before: int, max_quota: int) -> bool:
    """True when the participant still has full quota before this consumption."""
    return remaining_before >= max_quota


def new_reset_at(now: datetime) -> datetime:
    return now + window_duration()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sql_utc(dt: datetime) -> datetime:
    """UTC instant as naive datetime for cross-DB timestamp comparisons."""
    return ensure_utc(dt).replace(tzinfo=None)
