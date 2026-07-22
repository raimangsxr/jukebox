"""Pacific quota-day reset evaluated on read (010, FR-011)."""

from datetime import datetime, timedelta

from app.services import youtube_api_key_usage_service as svc


def test_usage_resets_on_read_after_day_rolls(client, db_session, youtube_api_keys):
    svc.record_attempt(db_session, "key-one")
    today = svc.build_usage_list(db_session)
    assert today.keys[0].used_count == 1

    tomorrow = datetime.now(svc._PACIFIC) + timedelta(days=1)
    rolled = svc.build_usage_list(db_session, now=tomorrow)
    # New Pacific quota day → fresh zeroed rows, no intervening traffic needed.
    assert rolled.quota_day == svc.pacific_quota_day(tomorrow).isoformat()
    assert all(item.used_count == 0 for item in rolled.keys)
    assert all(item.remaining_count == svc.DAILY_LIMIT for item in rolled.keys)
