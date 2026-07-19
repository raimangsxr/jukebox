"""YouTube API key usage tracking tests."""

import io
import json
import urllib.error
from datetime import timedelta

from app.config import get_settings
from app.services.youtube_api_key_usage_service import (
    DAILY_LIMIT,
    build_usage_list,
    key_hash,
    mark_google_exhausted,
    pacific_quota_day,
    record_attempt,
    reset_for_tests,
)
from tests.conftest import collect_sse_events_after, make_youtube_search_item, make_youtube_search_response


def _usage(client):
    return client.get("/api/youtube/api-keys/usage")


def test_usage_requires_operator_auth(client, youtube_api_keys):
    assert _usage(client).status_code == 401


def test_usage_requires_operator_not_participant(
    dev_participant_client, youtube_api_keys
):
    assert _usage(dev_participant_client).status_code == 401


def test_usage_empty_when_no_keys(authed_client, monkeypatch):
    monkeypatch.setenv("JUKEBOX_YOUTUBE_API_KEYS", "")
    get_settings.cache_clear()
    response = _usage(authed_client)
    assert response.status_code == 200
    data = response.json()
    assert data["keys"] == []
    assert data["daily_limit"] == 100
    assert data["next_reset_at"]


def test_usage_lists_masked_keys(authed_client, youtube_api_keys):
    response = _usage(authed_client)
    assert response.status_code == 200
    data = response.json()
    assert len(data["keys"]) == 2
    first = data["keys"][0]
    assert first["label"] == "Clave 1"
    assert first["masked_suffix"] == "…-one"
    assert first["used_count"] == 0
    assert first["remaining_count"] == 100
    assert first["daily_limit"] == 100
    assert first["exhausted"] is False
  # ensure full key never returned
    assert "key-one" not in json.dumps(data)


def test_record_attempt_increments(db_session, youtube_api_keys):
    reset_for_tests()
    record_attempt(db_session, "key-one")
    data = build_usage_list(db_session).model_dump()
    assert data["keys"][0]["used_count"] == 1
    assert data["keys"][0]["remaining_count"] == 99


def test_record_attempt_still_counts_on_failed_fetch(
    db_session, dev_participant_client, youtube_api_keys, monkeypatch
):
    import app.services.youtube_search_service as mod

    def handler(url, timeout=0):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(mod.urllib.request, "urlopen", handler)
    response = dev_participant_client.get("/api/youtube/search", params={"q": "network test"})
    assert response.status_code == 503
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 1


def test_record_attempt_caps_at_daily_limit(db_session, youtube_api_keys):
    reset_for_tests()
    for _ in range(DAILY_LIMIT):
        record_attempt(db_session, "key-one")
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 100
    assert usage.keys[0].remaining_count == 0
    assert usage.keys[0].exhausted is True


def test_persistence_across_new_session(db_session, db_engine, youtube_api_keys):
    reset_for_tests()
    record_attempt(db_session, "key-one")
    TestingSession = __import__("sqlalchemy.orm", fromlist=["sessionmaker"]).sessionmaker
    session_factory = TestingSession(bind=db_engine, autoflush=False, autocommit=False)
    fresh = session_factory()
    try:
        usage = build_usage_list(fresh)
        assert usage.keys[0].used_count == 1
    finally:
        fresh.close()


def test_sse_api_key_usage_on_increment(authed_client, db_session, youtube_api_keys):
    reset_for_tests()

    events = collect_sse_events_after(
        lambda: record_attempt(db_session, "key-one"),
        event_type="api_key_usage",
    )
    assert len(events) == 1
    _, payload = events[0]
    assert payload is not None
    assert payload["keys"][0]["used_count"] == 1


def test_search_increments_usage(
    dev_participant_client, db_session, youtube_api_keys, monkeypatch
):
    reset_for_tests()

    def handler(url, timeout=0):
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    import app.services.youtube_search_service as mod

    monkeypatch.setattr(mod.urllib.request, "urlopen", handler)
    response = dev_participant_client.get("/api/youtube/search", params={"q": "test query"})
    assert response.status_code == 200
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 1


def test_search_rate_limit_does_not_increment(
    dev_participant_client, db_session, youtube_api_keys, monkeypatch
):
    reset_for_tests()

    def handler(url, timeout=0):
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    import app.services.youtube_search_service as mod

    monkeypatch.setattr(mod.urllib.request, "urlopen", handler)
    for _ in range(10):
        assert dev_participant_client.get("/api/youtube/search", params={"q": "ok query"}).status_code == 200
    assert (
        dev_participant_client.get("/api/youtube/search", params={"q": "too many"}).status_code
        == 429
    )
    usage = build_usage_list(db_session)
    total = sum(item.used_count for item in usage.keys)
    assert total == 10


def test_invalid_query_does_not_increment(dev_participant_client, db_session, youtube_api_keys):
    reset_for_tests()
    response = dev_participant_client.get("/api/youtube/search", params={"q": "a"})
    assert response.status_code == 422
    usage = build_usage_list(db_session)
    assert all(item.used_count == 0 for item in usage.keys)


def test_metadata_fetch_increments_usage(
    db_session, youtube_api_keys, monkeypatch, sample_video_id
):
    reset_for_tests()
    from app.services.youtube_meta import fetch_youtube_duration_sec

    def handler(url, timeout=0):
        return _FakeResponse(
            {
                "items": [
                    {"contentDetails": {"duration": "PT3M30S"}},
                ]
            }
        )

    import app.services.youtube_meta as mod

    monkeypatch.setattr(mod.urllib.request, "urlopen", handler)
    duration = fetch_youtube_duration_sec(sample_video_id, db_session)
    assert duration == 210
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 1


def test_mark_google_exhausted_sets_100(db_session, youtube_api_keys):
    reset_for_tests()
    record_attempt(db_session, "key-one")
    mark_google_exhausted(db_session, "key-one")
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 100
    assert usage.keys[0].remaining_count == 0
    assert usage.keys[0].exhausted is True


def test_failover_increments_both_keys(
    dev_participant_client, db_session, youtube_api_keys, monkeypatch
):
    reset_for_tests()

    def handler(url, timeout=0):
        url_str = str(url)
        if "key-one" in url_str:
            raise urllib.error.HTTPError(
                url_str,
                403,
                "quota",
                hdrs=None,
                fp=io.BytesIO(
                    json.dumps(
                        {"error": {"errors": [{"reason": "quotaExceeded"}]}}
                    ).encode()
                ),
            )
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    import app.services.youtube_search_service as mod

    monkeypatch.setattr(mod.urllib.request, "urlopen", handler)
    response = dev_participant_client.get("/api/youtube/search", params={"q": "failover"})
    assert response.status_code == 200
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 100
    assert usage.keys[0].exhausted is True
    assert usage.keys[1].used_count == 1


def test_quota_day_roll_resets_counts(db_session, youtube_api_keys):
    reset_for_tests()
    from app.models import YoutubeApiKeyDailyUsage

    yesterday = pacific_quota_day() - timedelta(days=1)
    db_session.add(
        YoutubeApiKeyDailyUsage(
            key_hash=key_hash("key-one"),
            quota_day=yesterday,
            used_count=50,
            exhausted=True,
        )
    )
    db_session.commit()
    usage = build_usage_list(db_session)
    assert usage.keys[0].used_count == 0
    assert usage.keys[0].remaining_count == 100


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False
