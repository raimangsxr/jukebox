"""SSE stream tests."""

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
    )

    event_types = [event_type for event_type, _ in events if event_type]
    assert "state" in event_types
    assert "notification" in event_types
    state_events = [payload for et, payload in events if et == "state"]
    assert state_events
    assert state_events[-1]["queue"]

