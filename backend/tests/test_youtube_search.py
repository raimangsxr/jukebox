"""YouTube text search API tests."""

import io
import json
import urllib.error
from uuid import uuid4

from app.config import get_settings
from app.models import QueueEntry, QueueEntryStatus
from tests.conftest import make_youtube_search_item, make_youtube_search_response


def _search(client, query: str):
    return client.get("/api/youtube/search", params={"q": query})


def _submit(client, video_id: str, *, search_query: str | None = None):
    body: dict[str, str] = {"youtube_url_or_id": video_id}
    if search_query is not None:
        body["search_query"] = search_query
    return client.post("/api/queue/submit", json=body)


def _mock_metadata(monkeypatch, *, fail: bool = False):
    from app.services import queue_service

    if fail:

        def _fail(video_id: str):
            raise ValueError("metadata unavailable")

        monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _fail)
    else:

        def _ok(video_id: str):
            return "Test Song", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _ok)


def _mock_youtube_fetch(monkeypatch, handler):
    import app.services.youtube_search_service as mod

    monkeypatch.setattr(mod.urllib.request, "urlopen", handler)


def test_search_config_disabled(client, monkeypatch):
    monkeypatch.setenv("JUKEBOX_YOUTUBE_API_KEYS", "")
    get_settings.cache_clear()
    response = client.get("/api/youtube/search/config")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}


def test_search_config_enabled(client, youtube_api_keys):
    response = client.get("/api/youtube/search/config")
    assert response.status_code == 200
    assert response.json() == {"enabled": True}


def test_search_requires_auth(client, youtube_api_keys):
    response = _search(client, "test query")
    assert response.status_code == 401


def test_search_happy_path(dev_participant_client, youtube_api_keys, monkeypatch):
    items = [
        make_youtube_search_item("aaaaaaaaaaa", title="Song A", channel="Channel A"),
        make_youtube_search_item("bbbbbbbbbbb", title="Song B", channel="Channel B"),
    ]

    def handler(url, timeout=0):
        payload = make_youtube_search_response(items)
        return _FakeResponse(payload)

    _mock_youtube_fetch(monkeypatch, handler)
    response = _search(dev_participant_client, "bohemian rhapsody")
    assert response.status_code == 200
    data = response.json()["results"]
    assert len(data) == 2
    assert data[0]["title"] == "Song A"
    assert data[0]["channel_title"] == "Channel A"
    assert data[0]["thumbnail_url"].endswith("/default.jpg")


def test_search_caps_max_results(dev_participant_client, youtube_api_keys, monkeypatch):
    captured: dict[str, str] = {}

    def handler(url, timeout=0):
        captured["url"] = str(url)
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    _mock_youtube_fetch(monkeypatch, handler)
    monkeypatch.setenv("JUKEBOX_YOUTUBE_SEARCH_MAX_RESULTS", "10")
    get_settings.cache_clear()
    response = _search(dev_participant_client, "many results")
    assert response.status_code == 200
    assert "maxResults=10" in captured["url"]


def test_search_invalid_query_too_short(dev_participant_client, youtube_api_keys):
    response = _search(dev_participant_client, "a")
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid search query"


def test_search_invalid_query_whitespace_only(dev_participant_client, youtube_api_keys):
    response = _search(dev_participant_client, "   ")
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid search query"


def test_search_rate_limit(dev_participant_client, youtube_api_keys, monkeypatch):
    def handler(url, timeout=0):
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    _mock_youtube_fetch(monkeypatch, handler)
    for _ in range(10):
        assert _search(dev_participant_client, "query ok").status_code == 200
    response = _search(dev_participant_client, "one too many")
    assert response.status_code == 429
    assert response.json()["detail"] == "search rate limit exceeded"


def test_search_empty_results(dev_participant_client, youtube_api_keys, monkeypatch):
    def handler(url, timeout=0):
        return _FakeResponse({"items": []})

    _mock_youtube_fetch(monkeypatch, handler)
    response = _search(dev_participant_client, "nothing here")
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_network_error(dev_participant_client, youtube_api_keys, monkeypatch):
    def handler(url, timeout=0):
        raise urllib.error.URLError("network down")

    _mock_youtube_fetch(monkeypatch, handler)
    response = _search(dev_participant_client, "network test")
    assert response.status_code == 503
    assert response.json()["detail"] == "youtube search unavailable"


def test_search_quota_failover(dev_participant_client, youtube_api_keys, monkeypatch):
    calls: list[str] = []

    def handler(url, timeout=0):
        url_str = str(url)
        if "key=key-one" in url_str:
            calls.append("key-one")
            raise urllib.error.HTTPError(
                url_str,
                403,
                "quota",
                hdrs=None,
                fp=io.BytesIO(
                    json.dumps(
                        {
                            "error": {
                                "errors": [{"reason": "quotaExceeded"}],
                            }
                        }
                    ).encode()
                ),
            )
        calls.append("key-two")
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("ccccccccccc")])
        )

    _mock_youtube_fetch(monkeypatch, handler)
    response = _search(dev_participant_client, "failover test")
    assert response.status_code == 200
    assert "key-one" in calls
    assert "key-two" in calls


def test_search_all_keys_exhausted(dev_participant_client, youtube_api_keys, monkeypatch):
    def handler(url, timeout=0):
        url_str = str(url)
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

    _mock_youtube_fetch(monkeypatch, handler)
    response = _search(dev_participant_client, "all exhausted")
    assert response.status_code == 503
    assert response.json()["detail"] == "youtube search unavailable"


def test_submit_from_search_success(
    dev_participant_client, youtube_api_keys, monkeypatch, sample_video_id, db_session
):
    _mock_metadata(monkeypatch)
    response = _submit(
        dev_participant_client,
        sample_video_id,
        search_query="never gonna give you up",
    )
    assert response.status_code == 201
    entry = db_session.get(QueueEntry, response.json()["id"])
    assert entry.original_query == "search:never gonna give you up"


def test_submit_from_search_pending_limit(dev_participant_client, monkeypatch):
    _mock_metadata(monkeypatch)
    assert _submit(dev_participant_client, "aaaaaaaaaaa", search_query="one").status_code == 201
    assert _submit(dev_participant_client, "bbbbbbbbbbb", search_query="two").status_code == 201
    response = _submit(dev_participant_client, "ccccccccccc", search_query="three")
    assert response.status_code == 429
    assert response.json()["detail"] == "pending submission limit reached"


def test_submit_from_search_active_own_limit(
    dev_participant_client, monkeypatch, db_session
):
    _mock_metadata(monkeypatch)
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id="jNQXAC9IVRw",
        title="Active",
        thumbnail_url="https://example.com/t.jpg",
        status=QueueEntryStatus.queued,
        original_query="search:existing",
        vote_count=0,
        submitted_by_participant_id=participant_id,
    )
    db_session.add(entry)
    db_session.commit()
    response = _submit(dev_participant_client, "ddddddddddd", search_query="new song")
    assert response.status_code == 429
    assert response.json()["detail"] == "active song limit reached"


def test_submit_from_search_duplicate(
    dev_participant_client, monkeypatch, pending_entry, sample_video_id
):
    _mock_metadata(monkeypatch)
    response = _submit(
        dev_participant_client,
        sample_video_id,
        search_query="duplicate",
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_submit_from_search_metadata_failure(dev_participant_client, monkeypatch):
    _mock_metadata(monkeypatch, fail=True)
    response = _submit(dev_participant_client, "eeeeeeeeeee", search_query="bad meta")
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid youtube reference"


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False
