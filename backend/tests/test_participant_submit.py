"""Participant song submit API tests."""

from uuid import uuid4

from app.models import QueueEntry, QueueEntryStatus
from app.services.state_service import get_or_create_runtime


def _submit(client, url: str):
    return client.post("/api/queue/submit", json={"youtube_url_or_id": url})


def _mock_metadata(monkeypatch, *, title="Test Song", fail=False):
    from app.services import queue_service

    if fail:

        def _fail(video_id: str):
            raise ValueError("metadata unavailable")

        monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _fail)
    else:

        def _ok(video_id: str):
            return title, f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _ok)


def _make_entry(
    db_session,
    *,
    video_id: str,
    status: QueueEntryStatus,
    participant_id: str | None = None,
) -> QueueEntry:
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title="Existing",
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        status=status,
        original_query=video_id,
        vote_count=0,
        submitted_by_participant_id=participant_id,
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_submit_success(dev_participant_client, monkeypatch, sample_video_id):
    _mock_metadata(monkeypatch)
    response = _submit(
        dev_participant_client, f"https://www.youtube.com/watch?v={sample_video_id}"
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending_review"
    assert data["youtube_video_id"] == sample_video_id


def test_submit_sets_participant_id(
    dev_participant_client, monkeypatch, sample_video_id, db_session
):
    _mock_metadata(monkeypatch)
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    response = _submit(dev_participant_client, sample_video_id)
    assert response.status_code == 201
    entry = db_session.get(QueueEntry, response.json()["id"])
    assert entry.submitted_by_participant_id == participant_id


def test_submit_bumps_revision(dev_participant_client, monkeypatch, sample_video_id, db_session):
    _mock_metadata(monkeypatch)
    before = get_or_create_runtime(db_session).revision
    assert _submit(dev_participant_client, sample_video_id).status_code == 201
    db_session.expire_all()
    after = get_or_create_runtime(db_session).revision
    assert after == before + 1


def test_submit_pending_limit(dev_participant_client, monkeypatch):
    _mock_metadata(monkeypatch)
    assert _submit(dev_participant_client, "aaaaaaaaaaa").status_code == 201
    assert _submit(dev_participant_client, "bbbbbbbbbbb").status_code == 201
    response = _submit(dev_participant_client, "ccccccccccc")
    assert response.status_code == 429
    assert response.json()["detail"] == "pending submission limit reached"


def test_submit_active_own_limit(dev_participant_client, monkeypatch, db_session):
    _mock_metadata(monkeypatch)
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    _make_entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.queued,
        participant_id=participant_id,
    )
    response = _submit(dev_participant_client, "ddddddddddd")
    assert response.status_code == 429
    assert response.json()["detail"] == "active song limit reached"


def test_submit_duplicate(dev_participant_client, monkeypatch, pending_entry, sample_video_id):
    _mock_metadata(monkeypatch)
    response = _submit(dev_participant_client, sample_video_id)
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_submit_invalid_youtube(dev_participant_client):
    response = _submit(dev_participant_client, "not-a-url")
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid youtube reference"


def test_submit_metadata_failure(dev_participant_client, monkeypatch):
    _mock_metadata(monkeypatch, fail=True)
    response = _submit(dev_participant_client, "dQw4w9WgXcQ")
    assert response.status_code == 422
    assert response.json()["detail"] == "invalid youtube reference"


def test_submit_requires_auth(client, monkeypatch, sample_video_id):
    _mock_metadata(monkeypatch)
    response = _submit(client, sample_video_id)
    assert response.status_code == 401


def test_resubmit_after_played(dev_participant_client, monkeypatch, db_session):
    _mock_metadata(monkeypatch)
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    video_id = "dQw4w9WgXcQ"
    _make_entry(
        db_session,
        video_id=video_id,
        status=QueueEntryStatus.played,
        participant_id=participant_id,
    )
    response = _submit(dev_participant_client, video_id)
    assert response.status_code == 201


def test_resubmit_after_reject(dev_participant_client, monkeypatch, db_session):
    _mock_metadata(monkeypatch)
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    _make_entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.rejected,
        participant_id=participant_id,
    )
    response = _submit(dev_participant_client, "jNQXAC9IVRw")
    assert response.status_code == 201