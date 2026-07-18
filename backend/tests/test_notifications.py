"""SSE notification tests."""

from uuid import uuid4

from app.models import QueueEntryStatus
from app.services.state_service import get_or_create_runtime

from .conftest import _make_queue_entry, collect_sse_events_after


def test_song_approved_on_approve(authed_client, db_session, participant):
    pending = _make_queue_entry(
        db_session,
        video_id="approvedVid1",
        status=QueueEntryStatus.pending_review,
        title="Approved Song",
        submitted_by_participant_id=participant.id,
    )

    events = collect_sse_events_after(
        lambda: authed_client.post(f"/api/queue/{pending.id}/approve"),
        event_type="notification",
    )

    assert len(events) == 1
    _, payload = events[0]
    assert payload is not None
    assert payload["type"] == "song.approved"
    assert payload["queue_entry_id"] == pending.id
    assert payload["participant_id"] == participant.id
    assert payload["title"] == "Approved Song"


def test_song_approved_skipped_without_owner(authed_client, pending_entry):
    events = collect_sse_events_after(
        lambda: authed_client.post(f"/api/queue/{pending_entry.id}/approve"),
        event_type="notification",
    )
    assert events == []


def test_song_approved_not_emitted_on_reject(authed_client, db_session, participant):
    pending = _make_queue_entry(
        db_session,
        video_id="rejectVid1",
        status=QueueEntryStatus.pending_review,
        submitted_by_participant_id=participant.id,
    )

    events = collect_sse_events_after(
        lambda: authed_client.post(
            f"/api/queue/{pending.id}/reject",
            json={"reason": "no"},
        ),
        event_type="notification",
    )
    assert events == []


def test_song_up_next_on_skip(authed_client, db_session, participant):
    playing = _make_queue_entry(
        db_session,
        video_id="playingVid1",
        status=QueueEntryStatus.playing,
        title="Current",
    )
    runtime = get_or_create_runtime(db_session)
    runtime.now_playing_entry_id = playing.id
    db_session.commit()

    next_song = _make_queue_entry(
        db_session,
        video_id="nextVid1",
        status=QueueEntryStatus.queued,
        vote_count=5,
        title="Next Song",
        submitted_by_participant_id=participant.id,
    )

    events = collect_sse_events_after(
        lambda: authed_client.post("/api/queue/skip"),
        event_type="notification",
    )

    assert len(events) == 1
    _, payload = events[0]
    assert payload is not None
    assert payload["type"] == "song.up_next"
    assert payload["queue_entry_id"] == next_song.id
    assert payload["participant_id"] == participant.id


def test_song_up_next_on_idle_start(authed_client, db_session, participant):
    queued = _make_queue_entry(
        db_session,
        video_id="idleStart1",
        status=QueueEntryStatus.queued,
        title="Idle Start",
        submitted_by_participant_id=participant.id,
    )

    events = collect_sse_events_after(
        lambda: authed_client.post("/api/queue/skip"),
        event_type="notification",
    )

    assert len(events) == 1
    _, payload = events[0]
    assert payload is not None
    assert payload["type"] == "song.up_next"
    assert payload["queue_entry_id"] == queued.id


def test_song_up_next_skipped_without_owner(authed_client, playing_entry, queued_entry):
    events = collect_sse_events_after(
        lambda: authed_client.post("/api/queue/skip"),
        event_type="notification",
    )
    assert events == []


def test_song_up_next_not_emitted_on_vote_reorder(
    dev_participant_client, queued_entry, second_queued_entry, db_session
):
    queued_entry.vote_count = 1
    second_queued_entry.vote_count = 3
    db_session.commit()

    events = collect_sse_events_after(
        lambda: dev_participant_client.post(
            "/api/votes",
            json={"queue_entry_id": queued_entry.id},
        ),
        event_type="notification",
    )
    assert events == []


def test_song_up_next_not_emitted_when_only_playing(
    authed_client, db_session, participant
):
    playing = _make_queue_entry(
        db_session,
        video_id="onlyPlaying1",
        status=QueueEntryStatus.playing,
        title="Only Playing",
        submitted_by_participant_id=participant.id,
    )
    runtime = get_or_create_runtime(db_session)
    runtime.now_playing_entry_id = playing.id
    db_session.commit()

    events = collect_sse_events_after(
        lambda: authed_client.post("/api/queue/skip"),
        event_type="notification",
    )
    assert events == []


def test_notification_payload_uses_owner_participant_id(
    authed_client, db_session, participant
):
    other_participant_id = str(uuid4())
    pending = _make_queue_entry(
        db_session,
        video_id="ownerPayload1",
        status=QueueEntryStatus.pending_review,
        submitted_by_participant_id=participant.id,
    )

    events = collect_sse_events_after(
        lambda: authed_client.post(f"/api/queue/{pending.id}/approve"),
        event_type="notification",
    )

    assert len(events) == 1
    _, payload = events[0]
    assert payload is not None
    assert payload["participant_id"] == participant.id
    assert payload["participant_id"] != other_participant_id
