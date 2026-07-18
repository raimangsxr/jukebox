"""Participant submissions list API tests."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import QueueEntry, QueueEntryStatus


def _make_submission(
    db_session,
    participant_id: str,
    *,
    video_id: str,
    status: QueueEntryStatus,
    created_at: datetime | None = None,
):
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=f"Song {video_id}",
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        status=status,
        original_query=video_id,
        vote_count=0,
        submitted_by_participant_id=participant_id,
        rejection_reason="No encaja" if status == QueueEntryStatus.rejected else None,
    )
    if created_at is not None:
        entry.created_at = created_at
    db_session.add(entry)
    db_session.commit()
    return entry


def test_submissions_requires_auth(client):
    response = client.get("/api/participant/submissions")
    assert response.status_code == 401


def test_submissions_only_own_entries(
    dev_participant_client, db_session, participant
):
    own_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    _make_submission(db_session, own_id, video_id="aaaaaaaaaaa", status=QueueEntryStatus.pending_review)
    _make_submission(db_session, participant.id, video_id="bbbbbbbbbbb", status=QueueEntryStatus.pending_review)

    response = dev_participant_client.get("/api/participant/submissions")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["youtube_video_id"] == "aaaaaaaaaaa"


def test_submissions_order_and_status_fields(dev_participant_client, db_session):
    own_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    now = datetime.now(timezone.utc)
    _make_submission(
        db_session,
        own_id,
        video_id="aaaaaaaaaaa",
        status=QueueEntryStatus.queued,
        created_at=now - timedelta(minutes=5),
    )
    _make_submission(
        db_session,
        own_id,
        video_id="bbbbbbbbbbb",
        status=QueueEntryStatus.rejected,
        created_at=now,
    )

    response = dev_participant_client.get("/api/participant/submissions")
    entries = response.json()["entries"]
    assert len(entries) == 2
    assert entries[0]["youtube_video_id"] == "bbbbbbbbbbb"
    assert entries[1]["youtube_video_id"] == "aaaaaaaaaaa"
    rejected = next(e for e in entries if e["status"] == "rejected")
    assert rejected["rejection_reason"] == "No encaja"
