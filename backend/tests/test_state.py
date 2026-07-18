"""State snapshot API tests."""

from app.models import QueueEntryStatus


def test_state_requires_auth(client):
    response = client.get("/api/state")
    assert response.status_code == 401


def test_state_returns_snapshot(authed_client, playing_entry, queued_entry):
    response = authed_client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert data["revision"] >= 0
    assert data["now_playing"]["id"] == playing_entry.id
    assert data["now_playing"]["youtube_video_id"] == playing_entry.youtube_video_id
    assert len(data["queue"]) == 1
    assert data["queue"][0]["id"] == queued_entry.id
    assert data["queue"][0]["vote_count"] == 3
    assert data["event_config"]["queue_visible_count"] == 8


def test_state_queue_visible_count_cap(authed_client, db_session):
    from uuid import uuid4

    from app.models import QueueEntry

    for index in range(10):
        entry = QueueEntry(
            id=str(uuid4()),
            youtube_video_id=f"id{index:07d}"[:11],
            title=f"Song {index}",
            status=QueueEntryStatus.queued,
            original_query=f"id{index}",
            vote_count=index,
            position=index + 1,
        )
        db_session.add(entry)
    db_session.commit()

    response = authed_client.get("/api/state")
    assert response.status_code == 200
    assert len(response.json()["queue"]) == 8
