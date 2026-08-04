from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import QueueEntry, QueueEntryStatus
from app.services.state_service import get_or_create_runtime


def _entry(
    db_session: Session,
    *,
    video_id: str,
    status: QueueEntryStatus,
    vote_count: int = 0,
    title: str = "Song",
    participant_id: str | None = None,
    position: int | None = None,
) -> QueueEntry:
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        status=status,
        original_query=video_id,
        vote_count=vote_count,
        position=position,
        submitted_by_participant_id=participant_id,
        source="participant",
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_get_active_queue_empty(authed_client: TestClient):
    response = authed_client.get("/api/queue/active")
    assert response.status_code == 200
    data = response.json()
    assert data["now_playing"] is None
    assert data["queued"] == []


def test_get_active_queue_order_and_fields(
    authed_client: TestClient,
    db_session: Session,
    playing_entry: QueueEntry,
    queued_entry: QueueEntry,
    participant,
):
    queued_entry.submitted_by_participant_id = participant.id
    playing_entry.submitted_by_participant_id = participant.id
    db_session.commit()

    response = authed_client.get("/api/queue/active")
    assert response.status_code == 200
    data = response.json()
    assert data["now_playing"]["id"] == playing_entry.id
    assert data["now_playing"]["source"] == "participant"
    assert data["now_playing"]["submitted_by_display_name"] == participant.display_name
    assert len(data["queued"]) == 1
    assert data["queued"][0]["id"] == queued_entry.id


def test_get_active_queue_requires_operator(client: TestClient, dev_participant_client: TestClient):
    assert client.get("/api/queue/active").status_code == 401
    assert dev_participant_client.get("/api/queue/active").status_code == 401


def test_clear_active_queue_permanent_delete(
    authed_client: TestClient,
    db_session: Session,
    playing_entry: QueueEntry,
    queued_entry: QueueEntry,
    pending_entry: QueueEntry,
    participant,
):
    playing_entry.submitted_by_participant_id = participant.id
    db_session.commit()
    playing_id = playing_entry.id
    queued_id = queued_entry.id

    response = authed_client.delete("/api/queue/active")
    assert response.status_code == 200
    assert response.json()["now_playing"] is None
    assert db_session.get(QueueEntry, playing_id) is None
    assert db_session.get(QueueEntry, queued_id) is None
    assert db_session.get(QueueEntry, pending_entry.id) is not None


def test_clear_active_queue_participant_submissions_empty(
    authed_client: TestClient,
    dev_participant_client: TestClient,
    db_session: Session,
    participant,
):
    entry = _entry(
        db_session,
        video_id="abc12345678",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        position=1,
    )
    entry_id = entry.id
    authed_client.delete("/api/queue/active")
    subs = dev_participant_client.get("/api/participant/submissions")
    assert subs.status_code == 200
    ids = [row["id"] for row in subs.json()["entries"]]
    assert entry_id not in ids


def test_clear_active_queue_participant_401(dev_participant_client: TestClient):
    assert dev_participant_client.delete("/api/queue/active").status_code == 401


def test_force_play_promotes_and_marks_interrupted_played(
    authed_client: TestClient,
    db_session: Session,
    playing_entry: QueueEntry,
    second_queued_entry: QueueEntry,
):
    third = _entry(
        db_session,
        video_id="thirdvid001",
        status=QueueEntryStatus.queued,
        vote_count=0,
        position=2,
    )
    response = authed_client.post(f"/api/queue/{third.id}/play-now")
    assert response.status_code == 200
    assert response.json()["now_playing"]["id"] == third.id
    interrupted = db_session.get(QueueEntry, playing_entry.id)
    assert interrupted is not None
    assert interrupted.status == QueueEntryStatus.played


def test_force_play_noop_when_already_playing(
    authed_client: TestClient,
    playing_entry: QueueEntry,
):
    response = authed_client.post(f"/api/queue/{playing_entry.id}/play-now")
    assert response.status_code == 200
    assert response.json()["now_playing"]["id"] == playing_entry.id


def test_force_play_participant_401(dev_participant_client: TestClient, queued_entry: QueueEntry):
    assert (
        dev_participant_client.post(f"/api/queue/{queued_entry.id}/play-now").status_code == 401
    )


def test_set_vote_count_reorders_queued(
    authed_client: TestClient,
    db_session: Session,
    playing_entry: QueueEntry,
    queued_entry: QueueEntry,
    second_queued_entry: QueueEntry,
):
    queued_entry.vote_count = 1
    second_queued_entry.vote_count = 0
    db_session.commit()

    response = authed_client.patch(
        f"/api/queue/{second_queued_entry.id}/vote-count",
        json={"vote_count": 5},
    )
    assert response.status_code == 200
    active = authed_client.get("/api/queue/active").json()
    assert active["queued"][0]["id"] == second_queued_entry.id
    playing = db_session.get(QueueEntry, playing_entry.id)
    assert playing is not None
    assert playing.status == QueueEntryStatus.playing


def test_set_vote_count_negative_422(authed_client: TestClient, queued_entry: QueueEntry):
    response = authed_client.patch(
        f"/api/queue/{queued_entry.id}/vote-count",
        json={"vote_count": -1},
    )
    assert response.status_code == 422


def test_set_vote_count_participant_401(dev_participant_client: TestClient, queued_entry: QueueEntry):
    assert (
        dev_participant_client.patch(
            f"/api/queue/{queued_entry.id}/vote-count",
            json={"vote_count": 2},
        ).status_code
        == 401
    )


def test_delete_active_entry_hard_delete(
    authed_client: TestClient,
    db_session: Session,
    queued_entry: QueueEntry,
    participant,
):
    queued_entry.submitted_by_participant_id = participant.id
    db_session.commit()
    response = authed_client.delete(f"/api/queue/active/{queued_entry.id}")
    assert response.status_code == 200
    assert db_session.get(QueueEntry, queued_entry.id) is None


def test_delete_playing_promotes_next(
    authed_client: TestClient,
    db_session: Session,
    playing_entry: QueueEntry,
    second_queued_entry: QueueEntry,
):
    response = authed_client.delete(f"/api/queue/active/{playing_entry.id}")
    assert response.status_code == 200
    assert response.json()["now_playing"]["id"] == second_queued_entry.id
    assert db_session.get(QueueEntry, playing_entry.id) is None


def test_delete_active_not_in_history(
    authed_client: TestClient,
    queued_entry: QueueEntry,
):
    authed_client.delete(f"/api/queue/active/{queued_entry.id}")
    history = authed_client.get("/api/queue/history")
    assert history.status_code == 200
    ids = [e["id"] for e in history.json()["entries"]]
    assert queued_entry.id not in ids


def test_delete_active_participant_submissions(
    authed_client: TestClient,
    dev_participant_client: TestClient,
    db_session: Session,
    participant,
):
    entry = _entry(
        db_session,
        video_id="delpart0001",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        position=1,
    )
    authed_client.delete(f"/api/queue/active/{entry.id}")
    subs = dev_participant_client.get("/api/participant/submissions")
    assert entry.id not in [row["id"] for row in subs.json()["entries"]]


def test_delete_active_participant_401(dev_participant_client: TestClient, queued_entry: QueueEntry):
    response = dev_participant_client.delete(f"/api/queue/active/{queued_entry.id}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/queue/active"),
        ("DELETE", "/api/queue/active"),
        ("DELETE", "/api/queue/active/{id}"),
        ("POST", "/api/queue/{id}/play-now"),
        ("PATCH", "/api/queue/{id}/vote-count"),
    ],
)
def test_active_queue_routes_operator_only(
    dev_participant_client: TestClient,
    queued_entry: QueueEntry,
    method: str,
    path: str,
):
    url = path.replace("{id}", queued_entry.id)
    if method == "GET":
        response = dev_participant_client.get(url)
    elif method == "DELETE":
        response = dev_participant_client.delete(url)
    elif method == "POST":
        response = dev_participant_client.post(url)
    else:
        response = dev_participant_client.patch(url, json={"vote_count": 1})
    assert response.status_code == 401
