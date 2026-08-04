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
