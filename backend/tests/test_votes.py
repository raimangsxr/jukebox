"""Participant vote API tests."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.config import get_settings
from app.models import Participant, QueueEntryStatus, Vote


def _vote(client, entry_id: str):
    return client.post("/api/votes", json={"queue_entry_id": entry_id})


def test_cast_vote_success(dev_participant_client, queued_entry):
    before = dev_participant_client.get("/api/participant/state").json()
    assert before["votes_remaining"] == 2
    initial_count = before["queue"][0]["vote_count"]

    response = _vote(dev_participant_client, queued_entry.id)
    assert response.status_code == 201
    data = response.json()
    assert data["votes_remaining"] == 1
    assert data["state"]["queue"][0]["vote_count"] == initial_count + 1


def test_same_entry_double_vote(dev_participant_client, queued_entry):
    before = dev_participant_client.get("/api/participant/state").json()
    initial_count = before["queue"][0]["vote_count"]
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    response = _vote(dev_participant_client, queued_entry.id)
    assert response.status_code == 201
    assert response.json()["votes_remaining"] == 0
    state = dev_participant_client.get("/api/participant/state").json()
    assert state["queue"][0]["vote_count"] == initial_count + 2


def test_vote_limit_exceeded(dev_participant_client, queued_entry, second_queued_entry):
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    assert _vote(dev_participant_client, second_queued_entry.id).status_code == 201
    response = _vote(dev_participant_client, queued_entry.id)
    assert response.status_code == 409
    assert response.json()["detail"] == "vote limit exceeded"


def test_invalid_target_playing(dev_participant_client, playing_entry):
    response = _vote(dev_participant_client, playing_entry.id)
    assert response.status_code == 409
    assert response.json()["detail"] == "entry not votable"


def test_invalid_target_pending(dev_participant_client, pending_entry):
    response = _vote(dev_participant_client, pending_entry.id)
    assert response.status_code == 409
    assert response.json()["detail"] == "entry not votable"


def test_stale_target_after_promoted_to_playing(
    dev_participant_client, queued_entry, db_session
):
    entry_id = queued_entry.id
    queued_entry.status = QueueEntryStatus.playing
    db_session.commit()
    response = _vote(dev_participant_client, entry_id)
    assert response.status_code == 409
    assert response.json()["detail"] == "entry not votable"


def test_vote_entry_not_found(dev_participant_client):
    response = _vote(dev_participant_client, str(uuid4()))
    assert response.status_code == 404


def test_reorder_by_vote_count(
    dev_participant_client, queued_entry, second_queued_entry, db_session
):
    queued_entry.vote_count = 1
    second_queued_entry.vote_count = 3
    db_session.commit()

    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    response = _vote(dev_participant_client, queued_entry.id)
    assert response.status_code == 201
    state = response.json()["state"]
    assert state["queue"][0]["id"] == queued_entry.id


def test_concurrent_participants_vote_consistent_counts(
    client, db_session, queued_entry, monkeypatch
):
    monkeypatch.setenv("JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH", "true")
    get_settings.cache_clear()

    initial_count = queued_entry.vote_count
    for name in ("A", "B"):
        auth = client.post("/api/participant/dev-auth", json={"display_name": name})
        assert auth.status_code == 200
        vote = client.post("/api/votes", json={"queue_entry_id": queued_entry.id})
        assert vote.status_code == 201

    db_session.refresh(queued_entry)
    assert queued_entry.vote_count == initial_count + 2


def test_participant_cannot_moderate(dev_participant_client):
    response = dev_participant_client.post("/api/queue/skip")
    assert response.status_code == 401


def test_operator_cannot_vote_without_participant_session(authed_client, queued_entry):
    response = authed_client.post(
        "/api/votes",
        json={"queue_entry_id": queued_entry.id},
    )
    assert response.status_code == 401


def test_window_expiry_allows_vote_after_rollover(
    dev_participant_client, queued_entry, second_queued_entry, db_session
):
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"]["id"]
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    assert _vote(dev_participant_client, second_queued_entry.id).status_code == 201

    old_time = datetime.now(timezone.utc) - timedelta(minutes=6)
    for vote in db_session.query(Vote).filter(Vote.participant_id == participant_id).all():
        vote.created_at = old_time
    db_session.commit()

    state = dev_participant_client.get("/api/participant/state").json()
    assert state["votes_remaining"] == 2

    response = _vote(dev_participant_client, queued_entry.id)
    assert response.status_code == 201


def test_google_participant_vote_regression(
    google_oauth_client, db_session, queued_entry, google_profile
):
    from app.models import Participant
    from app.services import google_oauth_service

    state = google_oauth_service.create_oauth_state()
    callback = google_oauth_client.get(
        f"/api/auth/google/callback?code=auth-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code == 302

    before = google_oauth_client.get("/api/participant/state").json()
    assert before["votes_remaining"] == 2
    response = _vote(google_oauth_client, queued_entry.id)
    assert response.status_code == 201
    assert response.json()["votes_remaining"] == 1

    me = google_oauth_client.get("/api/participant/me").json()["participant"]
    row = db_session.get(Participant, me["id"])
    assert row.google_sub == google_profile["sub"]
