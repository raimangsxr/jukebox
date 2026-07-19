from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import YoutubeApiKeyDailyUsage
from ..schemas import ApiKeyUsageItem, ApiKeyUsageListResponse
from .sse_hub import broadcast_api_key_usage

_PACIFIC = ZoneInfo("America/Los_Angeles")
DAILY_LIMIT = 100
_last_broadcast_quota_day: date | None = None


def pacific_quota_day(now: datetime | None = None) -> date:
    now = now or datetime.now(_PACIFIC)
    return now.date()


def next_pacific_midnight(now: datetime | None = None) -> datetime:
    now = now or datetime.now(_PACIFIC)
    next_day = (now + timedelta(days=1)).date()
    return datetime.combine(next_day, datetime.min.time(), tzinfo=_PACIFIC)


def key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def masked_suffix(api_key: str) -> str:
    suffix = api_key[-4:] if len(api_key) >= 4 else api_key
    return f"…{suffix}"


def configured_keys() -> list[str]:
    raw = get_settings().youtube_api_keys
    return [key.strip() for key in raw.split(",") if key.strip()]


def is_key_exhausted_in_db(
    db: Session,
    api_key: str,
    quota_day: date | None = None,
) -> bool:
    day = quota_day or pacific_quota_day()
    row = db.execute(
        select(YoutubeApiKeyDailyUsage).where(
            YoutubeApiKeyDailyUsage.key_hash == key_hash(api_key),
            YoutubeApiKeyDailyUsage.quota_day == day,
        )
    ).scalar_one_or_none()
    return row is not None and row.exhausted


def ensure_rows_for_configured_keys(db: Session, quota_day: date) -> None:
    for api_key in configured_keys():
        kh = key_hash(api_key)
        row = db.execute(
            select(YoutubeApiKeyDailyUsage).where(
                YoutubeApiKeyDailyUsage.key_hash == kh,
                YoutubeApiKeyDailyUsage.quota_day == quota_day,
            )
        ).scalar_one_or_none()
        if row is None:
            db.add(
                YoutubeApiKeyDailyUsage(
                    key_hash=kh,
                    quota_day=quota_day,
                    used_count=0,
                    exhausted=False,
                )
            )
    db.commit()


def roll_quota_day_if_needed(db: Session, now: datetime | None = None) -> bool:
    global _last_broadcast_quota_day
    current = pacific_quota_day(now)
    rolled = (
        _last_broadcast_quota_day is not None
        and _last_broadcast_quota_day != current
    )
    _last_broadcast_quota_day = current
    if rolled:
        ensure_rows_for_configured_keys(db, current)
        broadcast_api_key_usage(build_usage_list(db, skip_roll=True))
    return rolled


def build_usage_list(
    db: Session,
    *,
    skip_roll: bool = False,
    now: datetime | None = None,
) -> ApiKeyUsageListResponse:
    if not skip_roll:
        roll_quota_day_if_needed(db, now)
    quota_day = pacific_quota_day(now)
    ensure_rows_for_configured_keys(db, quota_day)
    items: list[ApiKeyUsageItem] = []
    for index, api_key in enumerate(configured_keys(), start=1):
        kh = key_hash(api_key)
        row = db.execute(
            select(YoutubeApiKeyDailyUsage).where(
                YoutubeApiKeyDailyUsage.key_hash == kh,
                YoutubeApiKeyDailyUsage.quota_day == quota_day,
            )
        ).scalar_one()
        used = min(row.used_count, DAILY_LIMIT)
        remaining = max(0, DAILY_LIMIT - used)
        items.append(
            ApiKeyUsageItem(
                index=index,
                label=f"Clave {index}",
                masked_suffix=masked_suffix(api_key),
                used_count=used,
                remaining_count=remaining,
                daily_limit=DAILY_LIMIT,
                exhausted=row.exhausted or used >= DAILY_LIMIT,
            )
        )
    return ApiKeyUsageListResponse(
        keys=items,
        daily_limit=DAILY_LIMIT,
        quota_day=quota_day.isoformat(),
        next_reset_at=next_pacific_midnight(now).isoformat(),
    )


def _get_row_for_update(
    db: Session,
    api_key: str,
    quota_day: date,
) -> YoutubeApiKeyDailyUsage:
    ensure_rows_for_configured_keys(db, quota_day)
    return db.execute(
        select(YoutubeApiKeyDailyUsage)
        .where(
            YoutubeApiKeyDailyUsage.key_hash == key_hash(api_key),
            YoutubeApiKeyDailyUsage.quota_day == quota_day,
        )
        .with_for_update()
    ).scalar_one()


def record_attempt(db: Session, api_key: str) -> ApiKeyUsageListResponse:
    quota_day = pacific_quota_day()
    row = _get_row_for_update(db, api_key, quota_day)
    if row.used_count < DAILY_LIMIT:
        row.used_count += 1
    if row.used_count >= DAILY_LIMIT:
        row.used_count = DAILY_LIMIT
        row.exhausted = True
    row.updated_at = datetime.now(_PACIFIC)
    db.commit()
    response = build_usage_list(db, skip_roll=True)
    broadcast_api_key_usage(response)
    return response


def mark_google_exhausted(db: Session, api_key: str) -> ApiKeyUsageListResponse:
    quota_day = pacific_quota_day()
    row = _get_row_for_update(db, api_key, quota_day)
    row.used_count = DAILY_LIMIT
    row.exhausted = True
    row.updated_at = datetime.now(_PACIFIC)
    db.commit()
    response = build_usage_list(db, skip_roll=True)
    broadcast_api_key_usage(response)
    return response


def reset_for_tests() -> None:
    global _last_broadcast_quota_day
    _last_broadcast_quota_day = None
