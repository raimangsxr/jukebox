"""Queue history and requeue API tests."""

from datetime import datetime, timezone
from uuid import uuid4

from app.models import (
    FillerReserveEntry,
    QueueEntry,
    QueueEntryPriority,
    QueueEntrySource,
    QueueEntryStatus,
)
from app.services.state_service import get_or_create_runtime


def _mock_metadata(monkeypatch, *, title="History Song"):
    from app.services import queue_service

    def _ok(video_id: str):
        return title, f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _ok)
    monkeypatch.setattr(queue_service, "fetch_youtube_duration_sec", lambda *_a, **_k: 180)


def _terminal_entry(
    db_session,
    *,
    video_id: str,
    status: QueueEntryStatus,
    participant_id: str | None = None,
    source: str = QueueEntrySource.participant.value,
    priority: str = QueueEntryPriority.normal.value,
) -> QueueEntry:
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title="Terminal Song",
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        status=status,
        original_query=video_id,
        vote_count=0,
        submitted_by_participant_id=participant_id,
        finished_at=datetime.now(timezone.utc),
        source=source,
        priority=priority,
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_history_requires_operator(client):
    assert client.get("/api/queue/history").status_code == 401


def test_history_requires_operator_not_participant(dev_participant_client):
    assert dev_participant_client.get("/api/queue/history").status_code == 401


def test_requeue_requires_operator(client, db_session):
    entry = _terminal_entry(
        db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played
    )
    assert client.post(f"/api/queue/history/{entry.id}/requeue").status_code == 401


def test_requeue_participant_forbidden(dev_participant_client, db_session):
    entry = _terminal_entry(
        db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played
    )
    assert (
        dev_participant_client.post(f"/api/queue/history/{entry.id}/requeue").status_code
        == 401
    )


def test_history_list_pagination_and_filter(authed_client, db_session, participant):
    played = _terminal_entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.played,
        participant_id=participant.id,
    )
    _terminal_entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.rejected,
    )

    all_response = authed_client.get("/api/queue/history")
    assert all_response.status_code == 200
    data = all_response.json()
    assert data["total"] == 2
    assert len(data["entries"]) == 2
    returned_ids = {entry["id"] for entry in data["entries"]}
    assert played.id in returned_ids
    played_row = next(entry for entry in data["entries"] if entry["id"] == played.id)
    assert played_row["submitted_by_display_name"] == participant.display_name
    assert played_row["source"] == QueueEntrySource.participant.value

    played_only = authed_client.get("/api/queue/history", params={"status": "played"})
    assert played_only.status_code == 200
    assert played_only.json()["total"] == 1
    assert played_only.json()["entries"][0]["status"] == "played"

    rejected_only = authed_client.get(
        "/api/queue/history", params={"status": "rejected", "page_size": 1}
    )
    assert rejected_only.status_code == 200
    assert rejected_only.json()["total"] == 1
    assert rejected_only.json()["page_size"] == 1


def test_requeue_from_played(authed_client, db_session, participant):
    entry = _terminal_entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.played,
        participant_id=participant.id,
    )
    before = get_or_create_runtime(db_session).revision
    response = authed_client.post(f"/api/queue/history/{entry.id}/requeue")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] in ("queued", "playing")
    assert data["priority"] == QueueEntryPriority.normal.value
    assert data["id"] != entry.id
    db_session.expire_all()
    new_entry = db_session.get(QueueEntry, data["id"])
    assert new_entry.source == QueueEntrySource.operator_requeue.value
    assert get_or_create_runtime(db_session).revision > before


def test_requeue_from_rejected_operator_song_gets_low_priority(authed_client, db_session):
    entry = _terminal_entry(
        db_session,
        video_id="9bZkp7q19f0",
        status=QueueEntryStatus.rejected,
        source=QueueEntrySource.operator_direct.value,
        priority=QueueEntryPriority.low.value,
    )
    response = authed_client.post(f"/api/queue/history/{entry.id}/requeue")
    assert response.status_code == 201
    assert response.json()["priority"] == QueueEntryPriority.low.value


def test_requeue_moderated_mode_skips_pending(authed_client, db_session):
    entry = _terminal_entry(
        db_session, video_id="kJQP7kiw5Fk", status=QueueEntryStatus.played
    )
    response = authed_client.post(f"/api/queue/history/{entry.id}/requeue")
    assert response.status_code == 201
    assert response.json()["status"] in ("queued", "playing")


def test_requeue_duplicate_active_blocked(authed_client, db_session, queued_entry):
    entry = _terminal_entry(
        db_session,
        video_id=queued_entry.youtube_video_id,
        status=QueueEntryStatus.played,
    )
    response = authed_client.post(f"/api/queue/history/{entry.id}/requeue")
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_requeue_duplicate_in_reserve_blocked(authed_client, db_session):
    video_id = "dQw4w9WgXcQ"
    entry = _terminal_entry(
        db_session, video_id=video_id, status=QueueEntryStatus.played
    )
    reserve = FillerReserveEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title="Reserve dup",
        original_query=video_id,
        position=1,
    )
    db_session.add(reserve)
    db_session.commit()

    response = authed_client.post(f"/api/queue/history/{entry.id}/requeue")
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_clear_history_requires_operator(client, db_session):
    _terminal_entry(db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played)
    assert client.delete("/api/queue/history").status_code == 401


def test_clear_history_forbidden_for_participant(dev_participant_client, db_session):
    _terminal_entry(db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played)
    assert dev_participant_client.delete("/api/queue/history").status_code == 401


def test_clear_history_operator_success(authed_client, db_session, queued_entry, playing_entry):
    played = _terminal_entry(
        db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played
    )
    rejected = _terminal_entry(
        db_session, video_id="jNQXAC9IVRw", status=QueueEntryStatus.rejected
    )
    pending = QueueEntry(
        id=str(uuid4()),
        youtube_video_id="9bZkp7q19f0",
        title="Pending",
        status=QueueEntryStatus.pending_review,
        original_query="9bZkp7q19f0",
        vote_count=0,
    )
    db_session.add(pending)
    db_session.commit()

    played_id = played.id
    rejected_id = rejected.id

    response = authed_client.delete("/api/queue/history")
    assert response.status_code == 204

    db_session.expire_all()
    assert db_session.get(QueueEntry, played_id) is None
    assert db_session.get(QueueEntry, rejected_id) is None
    assert db_session.get(QueueEntry, queued_entry.id) is not None
    assert db_session.get(QueueEntry, playing_entry.id) is not None
    assert db_session.get(QueueEntry, pending.id) is not None

    listed = authed_client.get("/api/queue/history")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0


def test_clear_history_idempotent(authed_client, db_session):
    _terminal_entry(db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played)
    assert authed_client.delete("/api/queue/history").status_code == 204
    assert authed_client.delete("/api/queue/history").status_code == 204


def test_clear_history_participant_submissions(
    authed_client, dev_participant_client, db_session
):
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    played = _terminal_entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.played,
        participant_id=participant_id,
    )
    queued = QueueEntry(
        id=str(uuid4()),
        youtube_video_id="jNQXAC9IVRw",
        title="Still active",
        status=QueueEntryStatus.queued,
        original_query="jNQXAC9IVRw",
        vote_count=0,
        submitted_by_participant_id=participant_id,
    )
    db_session.add(queued)
    db_session.commit()

    played_id = played.id
    queued_id = queued.id

    assert authed_client.delete("/api/queue/history").status_code == 204

    submissions = dev_participant_client.get("/api/participant/submissions")
    assert submissions.status_code == 200
    ids = {entry["id"] for entry in submissions.json()["entries"]}
    assert played_id not in ids
    assert queued_id in ids


def test_clear_history_with_active_filter_deletes_all_terminal(authed_client, db_session):
    _terminal_entry(
        db_session, video_id="dQw4w9WgXcQ", status=QueueEntryStatus.played
    )
    _terminal_entry(
        db_session, video_id="jNQXAC9IVRw", status=QueueEntryStatus.rejected
    )

    filtered = authed_client.get("/api/queue/history", params={"status": "played"})
    assert filtered.json()["total"] == 1

    assert authed_client.delete("/api/queue/history").status_code == 204

    assert authed_client.get("/api/queue/history").json()["total"] == 0
    assert (
        authed_client.get("/api/queue/history", params={"status": "rejected"}).json()["total"]
        == 0
    )
