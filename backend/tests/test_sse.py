"""SSE stream tests."""

from app.schemas import NotificationEventRead
from app.services import sse_hub
from app.services.state_service import bump_revision

from .conftest import collect_sse_events_after


def test_sse_requires_auth(client):
    response = client.get("/api/events/stream")
    assert response.status_code == 401


def test_sse_endpoint_registered(authed_client):
    schema = authed_client.app.openapi()["paths"]
    assert "/api/events/stream" in schema
    assert "get" in schema["/api/events/stream"]


def test_sse_revision_on_approve(authed_client, pending_entry):
    before = authed_client.get("/api/state").json()["revision"]
    approve = authed_client.post(f"/api/queue/{pending_entry.id}/approve")
    assert approve.status_code == 200
    after = authed_client.get("/api/state").json()
    assert after["revision"] > before
    assert len(after["queue"]) == 1
    assert after["queue"][0]["status"] == "queued"


def test_sse_vote_count_broadcast(authed_client, queued_entry, db_session):
    queued_entry.vote_count = 42
    db_session.commit()
    before = authed_client.get("/api/state").json()["revision"]
    bump_revision(db_session)
    after = authed_client.get("/api/state").json()
    assert after["revision"] > before
    assert after["queue"][0]["vote_count"] == 42


def test_sse_revision_on_vote(dev_participant_client, queued_entry):
    before = dev_participant_client.get("/api/participant/state").json()["revision"]
    vote = dev_participant_client.post(
        "/api/votes",
        json={"queue_entry_id": queued_entry.id},
    )
    assert vote.status_code == 201
    after = dev_participant_client.get("/api/participant/state").json()
    assert after["revision"] > before


def test_sse_stream_includes_notification_without_blocking_state(
    authed_client, pending_entry, participant, db_session
):
    pending_entry.submitted_by_participant_id = participant.id
    db_session.commit()

    events = collect_sse_events_after(
        lambda: authed_client.post(f"/api/queue/{pending_entry.id}/approve"),
        timeout=2.5,
        audience=sse_hub.PARTICIPANT,
        participant_id=participant.id,
    )

    event_types = [event_type for event_type, _ in events if event_type]
    assert "state" in event_types
    assert "notification" in event_types
    state_events = [payload for et, payload in events if et == "state"]
    assert state_events
    assert state_events[-1]["queue"]


def test_state_broadcast_reaches_all_audiences(db_session):
    """`state` is public: both operator and participant subscribers receive it."""
    operator_q = sse_hub.subscribe(audience=sse_hub.OPERATOR)
    participant_q = sse_hub.subscribe(
        audience=sse_hub.PARTICIPANT, participant_id="p-1"
    )
    try:
        sse_hub.broadcast_state({"revision": 7, "queue": []})
        assert operator_q.get_nowait().startswith("event: state")
        assert participant_q.get_nowait().startswith("event: state")
    finally:
        sse_hub.unsubscribe(operator_q)
        sse_hub.unsubscribe(participant_q)


def test_api_key_usage_reaches_operators_only(db_session):
    """FR-001: participant streams never receive operator-only api_key_usage."""
    operator_q = sse_hub.subscribe(audience=sse_hub.OPERATOR)
    participant_q = sse_hub.subscribe(
        audience=sse_hub.PARTICIPANT, participant_id="p-1"
    )
    try:
        sse_hub.broadcast_api_key_usage({"keys": [], "daily_limit": 100})
        assert operator_q.qsize() == 1
        assert operator_q.get_nowait().startswith("event: api_key_usage")
        assert participant_q.qsize() == 0
    finally:
        sse_hub.unsubscribe(operator_q)
        sse_hub.unsubscribe(participant_q)


def test_notification_delivered_only_to_target_participant(db_session):
    """FR-002: a notification reaches only the target participant's stream."""
    target_q = sse_hub.subscribe(audience=sse_hub.PARTICIPANT, participant_id="p-1")
    other_q = sse_hub.subscribe(audience=sse_hub.PARTICIPANT, participant_id="p-2")
    operator_q = sse_hub.subscribe(audience=sse_hub.OPERATOR)
    try:
        sse_hub.deliver_notification(
            "p-1",
            NotificationEventRead(
                type="song.approved",
                queue_entry_id="q-1",
                participant_id="p-1",
                title="Mi canción",
            ),
        )
        assert target_q.qsize() == 1
        assert target_q.get_nowait().startswith("event: notification")
        assert other_q.qsize() == 0
        assert operator_q.qsize() == 0
    finally:
        sse_hub.unsubscribe(target_q)
        sse_hub.unsubscribe(other_q)
        sse_hub.unsubscribe(operator_q)

