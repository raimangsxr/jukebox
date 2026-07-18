"""Queue moderation API tests."""

from uuid import uuid4

from app.config import get_settings
from app.models import MAX_QUEUED_ENTRIES, QueueEntry, QueueEntryStatus


def test_pending_requires_auth(client):
    assert client.get("/api/queue/pending").status_code == 401


def test_pending_list(authed_client, pending_entry):
    response = authed_client.get("/api/queue/pending")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["id"] == pending_entry.id
    assert entries[0]["duration_sec"] is None
    assert entries[0]["submitted_by_display_name"] is None


def test_pending_list_includes_submitter_and_duration(
    authed_client, db_session, sample_video_id, participant
):
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=sample_video_id,
        title="Participant Song",
        thumbnail_url=f"https://i.ytimg.com/vi/{sample_video_id}/hqdefault.jpg",
        duration_sec=213,
        status=QueueEntryStatus.pending_review,
        original_query=sample_video_id,
        submitted_by_participant_id=participant.id,
    )
    db_session.add(entry)
    db_session.commit()

    response = authed_client.get("/api/queue/pending")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["duration_sec"] == 213
    assert entries[0]["submitted_by_display_name"] == participant.display_name


def test_approve_pending(authed_client, pending_entry):
    response = authed_client.post(f"/api/queue/{pending_entry.id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_reject_pending(authed_client, pending_entry):
    response = authed_client.post(
        f"/api/queue/{pending_entry.id}/reject",
        json={"reason": "No encaja con el evento"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_idle_start_via_skip(authed_client, queued_entry):
    response = authed_client.post("/api/queue/skip")
    assert response.status_code == 200
    data = response.json()
    assert data["now_playing"]["id"] == queued_entry.id


def test_skip_advances_playing(authed_client, playing_entry, queued_entry):
    response = authed_client.post("/api/queue/skip")
    assert response.status_code == 200
    data = response.json()
    assert data["now_playing"]["id"] == queued_entry.id


def test_nothing_to_advance(authed_client):
    response = authed_client.post("/api/queue/skip")
    assert response.status_code == 409
    assert response.json()["detail"] == "nothing to advance"


def test_duplicate_active_blocked(authed_client, db_session, queued_entry):
    dup = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=queued_entry.youtube_video_id,
        title="Dup",
        status=QueueEntryStatus.pending_review,
        original_query=queued_entry.youtube_video_id,
    )
    db_session.add(dup)
    db_session.commit()

    response = authed_client.post(f"/api/queue/{dup.id}/approve")
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_queue_full_blocks_approve(authed_client, pending_entry, db_session):
    for index in range(MAX_QUEUED_ENTRIES):
        video_id = f"{index:011d}"
        entry = QueueEntry(
            id=str(uuid4()),
            youtube_video_id=video_id,
            title=f"Queued {index}",
            status=QueueEntryStatus.queued,
            original_query=video_id,
            position=index + 1,
        )
        db_session.add(entry)
    db_session.commit()

    response = authed_client.post(f"/api/queue/{pending_entry.id}/approve")
    assert response.status_code == 409
    assert response.json()["detail"] == "queue is full"


def test_dev_submit_gated(authed_client, monkeypatch):
    monkeypatch.setenv("JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT", "false")
    get_settings.cache_clear()
    response = authed_client.post(
        "/api/queue/dev-submit",
        json={"youtube_url_or_id": "dQw4w9WgXcQ"},
    )
    assert response.status_code == 404
    get_settings.cache_clear()


def test_dev_submit_enabled(authed_client, monkeypatch):
    monkeypatch.setenv("JUKEBOX_ALLOW_DEV_QUEUE_SUBMIT", "true")
    get_settings.cache_clear()
    response = authed_client.post(
        "/api/queue/dev-submit",
        json={"youtube_url_or_id": "dQw4w9WgXcQ"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"
    get_settings.cache_clear()
