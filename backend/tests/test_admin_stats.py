"""Admin statistics API tests."""

from datetime import datetime, timezone
from uuid import uuid4

from app.models import Participant, QueueEntry, QueueEntryStatus, Vote


def _stats(authed_client):
    return authed_client.get("/api/admin/stats")


def _participant(
    db_session,
    *,
    display_name: str = "Test Participant",
    email: str | None = None,
) -> Participant:
    row = Participant(
        id=str(uuid4()),
        display_name=display_name,
        email=email,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _entry(
    db_session,
    *,
    video_id: str,
    status: QueueEntryStatus,
    participant_id: str | None = None,
    title: str = "Song",
    vote_count: int = 0,
) -> QueueEntry:
    entry = QueueEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=title,
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        status=status,
        original_query=video_id,
        vote_count=vote_count,
        submitted_by_participant_id=participant_id,
        finished_at=(
            datetime.now(timezone.utc)
            if status in (QueueEntryStatus.played, QueueEntryStatus.rejected)
            else None
        ),
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def _vote(db_session, *, participant_id: str, queue_entry_id: str) -> Vote:
    row = Vote(
        id=str(uuid4()),
        participant_id=participant_id,
        queue_entry_id=queue_entry_id,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def test_stats_requires_operator(client):
    assert _stats(client).status_code == 401


def test_stats_participant_forbidden(dev_participant_client):
    assert _stats(dev_participant_client).status_code == 401


def test_stats_empty_db(authed_client):
    data = _stats(authed_client).json()
    assert data["participants_active_count"] == 0
    assert data["total_submissions"] == 0
    assert data["total_votes_cast"] == 0
    assert data["distinct_voted_songs_count"] == 0
    assert data["queue_counts"] == {
        "pending_review": 0,
        "queued": 0,
        "playing": 0,
        "played": 0,
        "rejected": 0,
    }
    assert data["top_submitters"] == []
    assert data["top_voters"] == []
    assert data["top_songs"] == []


def test_summary_active_participants_union(authed_client, db_session):
    submitter = _participant(db_session, display_name="Submitter")
    voter_only = _participant(db_session, display_name="Voter Only")
    inactive = _participant(db_session, display_name="Inactive")
    queued = _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.queued,
        participant_id=submitter.id,
    )
    _entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.rejected,
        participant_id=submitter.id,
    )
    _vote(db_session, participant_id=voter_only.id, queue_entry_id=queued.id)

    data = _stats(authed_client).json()
    assert data["participants_active_count"] == 2
    assert data["total_submissions"] == 2
    assert data["total_votes_cast"] == 1
    assert inactive.id not in {
        row["participant_id"] for row in data["top_submitters"] + data["top_voters"]
    }


def test_summary_distinct_voted_songs(authed_client, db_session, participant):
    _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        vote_count=2,
        title="A",
    )
    _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.played,
        participant_id=participant.id,
        vote_count=1,
        title="B",
    )
    _entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        vote_count=0,
        title="No votes",
    )

    data = _stats(authed_client).json()
    assert data["distinct_voted_songs_count"] == 1


def test_top_submitters_all_statuses_and_operator_excluded(authed_client, db_session):
    alice = _participant(db_session, display_name="Alice")
    bob = _participant(db_session, display_name="Bob")
    for status in QueueEntryStatus:
        _entry(
            db_session,
            video_id=f"{status.value[:8]}1",
            status=status,
            participant_id=alice.id if status != QueueEntryStatus.queued else bob.id,
        )
    _entry(
        db_session,
        video_id="operator01",
        status=QueueEntryStatus.queued,
        participant_id=None,
    )
    _entry(
        db_session,
        video_id="bobextra1",
        status=QueueEntryStatus.pending_review,
        participant_id=bob.id,
    )

    data = _stats(authed_client).json()
    submitters = {row["display_name"]: row["count"] for row in data["top_submitters"]}
    assert submitters["Bob"] == 2
    assert submitters["Alice"] == 4
    assert len(data["top_submitters"]) == 2


def test_top_submitters_email_fallback(authed_client, db_session):
    participant = _participant(db_session, display_name="   ", email="carlos@example.com")
    _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
    )

    data = _stats(authed_client).json()
    assert data["top_submitters"][0]["display_name"] == "carlos"


def test_top_submitters_tie_break_alphabetical(authed_client, db_session):
    for name in ["Zoe", "Amy", "Mia", "Leo", "Eve", "Ian", "Uma", "Bob", "Cal", "Dan", "Fin"]:
        participant = _participant(db_session, display_name=name)
        _entry(
            db_session,
            video_id=f"vid{name[:3]}",
            status=QueueEntryStatus.queued,
            participant_id=participant.id,
        )

    data = _stats(authed_client).json()
    assert len(data["top_submitters"]) == 10
    names = [row["display_name"] for row in data["top_submitters"]]
    assert names == sorted(names)


def test_top_voters_ranking(authed_client, db_session, queued_entry):
    alice = _participant(db_session, display_name="Alice")
    bob = _participant(db_session, display_name="Bob")
    second = _entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.queued,
    )
    for _ in range(3):
        _vote(db_session, participant_id=alice.id, queue_entry_id=queued_entry.id)
    for _ in range(2):
        _vote(db_session, participant_id=bob.id, queue_entry_id=second.id)

    data = _stats(authed_client).json()
    voters = data["top_voters"]
    assert voters[0]["display_name"] == "Alice"
    assert voters[0]["count"] == 3
    assert voters[1]["display_name"] == "Bob"
    assert voters[1]["count"] == 2


def test_top_songs_aggregate_and_exclude_zero(authed_client, db_session, participant):
    _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        vote_count=2,
        title="Zebra Song",
    )
    _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.played,
        participant_id=participant.id,
        vote_count=3,
        title="Alpha Song",
    )
    _entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        vote_count=0,
        title="Ignored",
    )
    _entry(
        db_session,
        video_id="9bZkp7q19f0",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        vote_count=1,
        title="Beta Song",
    )

    data = _stats(authed_client).json()
    songs = data["top_songs"]
    assert len(songs) == 2
    assert songs[0]["youtube_video_id"] == "dQw4w9WgXcQ"
    assert songs[0]["vote_count"] == 5
    assert songs[1]["youtube_video_id"] == "9bZkp7q19f0"


def test_queue_counts_by_status(authed_client, db_session, participant):
    for status in QueueEntryStatus:
        _entry(
            db_session,
            video_id=f"{status.value[:8]}x",
            status=status,
            participant_id=participant.id,
        )

    counts = _stats(authed_client).json()["queue_counts"]
    assert counts["pending_review"] == 1
    assert counts["queued"] == 1
    assert counts["playing"] == 1
    assert counts["played"] == 1
    assert counts["rejected"] == 1


def test_stats_after_clear_history(authed_client, db_session, participant):
    _entry(
        db_session,
        video_id="dQw4w9WgXcQ",
        status=QueueEntryStatus.played,
        participant_id=participant.id,
        vote_count=4,
        title="Played",
    )
    _entry(
        db_session,
        video_id="jNQXAC9IVRw",
        status=QueueEntryStatus.rejected,
        participant_id=participant.id,
        title="Rejected",
    )
    _entry(
        db_session,
        video_id="9bZkp7q19f0",
        status=QueueEntryStatus.queued,
        participant_id=participant.id,
        vote_count=2,
        title="Queued",
    )

    before = _stats(authed_client).json()
    assert before["queue_counts"]["played"] == 1
    assert before["queue_counts"]["rejected"] == 1
    assert before["total_submissions"] == 3

    assert authed_client.delete("/api/queue/history").status_code == 204

    after = _stats(authed_client).json()
    assert after["queue_counts"]["played"] == 0
    assert after["queue_counts"]["rejected"] == 0
    assert after["queue_counts"]["queued"] == 1
    assert after["total_submissions"] == 1
    assert after["top_submitters"][0]["count"] == 1
    assert after["top_songs"][0]["vote_count"] == 2
