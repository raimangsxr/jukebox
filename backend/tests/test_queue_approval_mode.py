"""Queue approval mode (moderated vs free) tests."""

from uuid import uuid4

from app.models import (
    EVENT_CONFIG_SINGLETON_ID,
    EventConfig,
    QueueEntry,
    QueueEntryStatus,
    QueueMode,
)

from .conftest import _make_queue_entry
from .test_participant_submit import _mock_metadata, _submit


def _set_queue_mode(db_session, mode: QueueMode) -> None:
    config = db_session.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    config.queue_mode = mode.value
    db_session.commit()


def test_default_mode_is_moderated(authed_client):
    response = authed_client.get("/api/event-config")
    assert response.status_code == 200
    assert response.json()["queue_mode"] == "moderated"


def test_moderated_submit_pending_not_in_queue(
    dev_participant_client, monkeypatch, sample_video_id, authed_client
):
    _mock_metadata(monkeypatch)
    response = _submit(
        dev_participant_client, f"https://www.youtube.com/watch?v={sample_video_id}"
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"

    state = dev_participant_client.get("/api/state").json()
    queue_ids = [item["id"] for item in state["queue"]]
    assert response.json()["id"] not in queue_ids

    pending = authed_client.get("/api/queue/pending").json()["entries"]
    assert any(entry["id"] == response.json()["id"] for entry in pending)


def test_moderated_pending_cap(dev_participant_client, monkeypatch, db_session):
    _set_queue_mode(db_session, QueueMode.moderated)
    _mock_metadata(monkeypatch)
    assert _submit(dev_participant_client, "aaaaaaaaaaa").status_code == 201
    assert _submit(dev_participant_client, "bbbbbbbbbbb").status_code == 201
    response = _submit(dev_participant_client, "ccccccccccc")
    assert response.status_code == 429
    assert response.json()["detail"] == "pending submission limit reached"


def test_free_submit_goes_directly_to_queue(
    dev_participant_client, monkeypatch, sample_video_id, authed_client, db_session
):
    _set_queue_mode(db_session, QueueMode.free)
    _mock_metadata(monkeypatch)
    response = _submit(
        dev_participant_client, f"https://www.youtube.com/watch?v={sample_video_id}"
    )
    assert response.status_code == 201
    assert response.json()["status"] == "playing"

    pending = authed_client.get("/api/queue/pending").json()["entries"]
    assert not any(entry["id"] == response.json()["id"] for entry in pending)

    state = dev_participant_client.get("/api/state").json()
    assert state["now_playing"]["id"] == response.json()["id"]
    queue_ids = [item["id"] for item in state["queue"]]
    assert response.json()["id"] not in queue_ids


def test_free_queued_cap(dev_participant_client, monkeypatch, db_session):
    _set_queue_mode(db_session, QueueMode.free)
    _mock_metadata(monkeypatch)
    assert _submit(dev_participant_client, "aaaaaaaaaaa").status_code == 201
    assert _submit(dev_participant_client, "bbbbbbbbbbb").status_code == 201
    assert _submit(dev_participant_client, "ccccccccccc").status_code == 201
    response = _submit(dev_participant_client, "ddddddddddd")
    assert response.status_code == 429
    assert response.json()["detail"] == "pending submission limit reached"


def test_free_duplicate_video_rejected(dev_participant_client, monkeypatch, db_session):
    _set_queue_mode(db_session, QueueMode.free)
    _mock_metadata(monkeypatch)
    assert _submit(dev_participant_client, "dQw4w9WgXcQ").status_code == 201
    response = _submit(dev_participant_client, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_legacy_pending_reject_after_switch_to_free(
    authed_client, dev_participant_client, monkeypatch, db_session, participant
):
    _mock_metadata(monkeypatch)
    submit = _submit(dev_participant_client, "aaaaaaaaaaa")
    assert submit.status_code == 201
    pending_id = submit.json()["id"]

    _set_queue_mode(db_session, QueueMode.free)
    response = authed_client.post(
        f"/api/queue/{pending_id}/reject",
        json={"reason": "no encaja"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    state = dev_participant_client.get("/api/state").json()
    assert pending_id not in [item["id"] for item in state["queue"]]


def test_mode_switch_preserves_queue_positions(
    authed_client, dev_participant_client, monkeypatch, db_session, participant
):
    _set_queue_mode(db_session, QueueMode.free)
    _mock_metadata(monkeypatch)
    first = _submit(dev_participant_client, "aaaaaaaaaaa").json()["id"]
    second = _submit(dev_participant_client, "bbbbbbbbbbb").json()["id"]

    before = dev_participant_client.get("/api/state").json()
    assert before["now_playing"]["id"] == first
    assert [item["id"] for item in before["queue"]] == [second]

    _set_queue_mode(db_session, QueueMode.moderated)
    authed_client.put("/api/event-config/queue-mode", json={"queue_mode": "free"})
    after = dev_participant_client.get("/api/state").json()
    assert after["now_playing"]["id"] == first
    assert [item["id"] for item in after["queue"]] == [second]


def test_moderated_resumes_after_switch_back(
    dev_participant_client, monkeypatch, db_session, authed_client
):
    _set_queue_mode(db_session, QueueMode.free)
    _mock_metadata(monkeypatch)
    assert _submit(dev_participant_client, "aaaaaaaaaaa").json()["status"] == "playing"

    authed_client.put("/api/event-config/queue-mode", json={"queue_mode": "moderated"})
    response = _submit(dev_participant_client, "bbbbbbbbbbb")
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"


def test_free_submit_after_operator_mode_put(
    authed_client, dev_participant_client, monkeypatch, db_session
):
    _mock_metadata(monkeypatch)
    authed_client.put("/api/event-config/queue-mode", json={"queue_mode": "free"})
    response = _submit(dev_participant_client, "ccccccccccc")
    assert response.status_code == 201
    assert response.json()["status"] == "playing"
