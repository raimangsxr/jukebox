from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..config import get_settings

_PACIFIC = ZoneInfo("America/Los_Angeles")


class YoutubeApiKeyPool:
    def __init__(self) -> None:
        self._next_index = 0
        self._exhausted_until: dict[str, datetime] = {}

    def _keys(self) -> list[str]:
        raw = get_settings().youtube_api_keys
        return [key.strip() for key in raw.split(",") if key.strip()]

    def _is_available(self, key: str, now: datetime) -> bool:
        until = self._exhausted_until.get(key)
        return until is None or now >= until

    def _is_db_exhausted(self, db: Session | None, key: str) -> bool:
        if db is None:
            return False
        from .youtube_api_key_usage_service import is_key_exhausted_in_db

        return is_key_exhausted_in_db(db, key)

    def has_available_key(
        self,
        now: datetime | None = None,
        db: Session | None = None,
    ) -> bool:
        now = now or datetime.now(_PACIFIC)
        return any(
            self._is_available(key, now) and not self._is_db_exhausted(db, key)
            for key in self._keys()
        )

    def acquire_key(
        self,
        now: datetime | None = None,
        db: Session | None = None,
    ) -> str | None:
        keys = self._keys()
        if not keys:
            return None
        now = now or datetime.now(_PACIFIC)
        for _ in range(len(keys)):
            key = keys[self._next_index % len(keys)]
            self._next_index = (self._next_index + 1) % len(keys)
            if self._is_available(key, now) and not self._is_db_exhausted(db, key):
                return key
        return None

    def mark_exhausted(self, key: str, now: datetime | None = None) -> None:
        now = now or datetime.now(_PACIFIC)
        next_day = (now + timedelta(days=1)).date()
        self._exhausted_until[key] = datetime.combine(
            next_day, datetime.min.time(), tzinfo=_PACIFIC
        )

    def reset_for_tests(self) -> None:
        self._next_index = 0
        self._exhausted_until.clear()


_pool = YoutubeApiKeyPool()


def get_youtube_api_key_pool() -> YoutubeApiKeyPool:
    return _pool
