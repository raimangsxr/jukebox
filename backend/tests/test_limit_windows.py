"""Fixed-window participant vote and search limits (022)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Participant, ParticipantSearch, QueueEntryStatus, Vote
from app.services.limit_window_service import window_duration
from app.services.search_rate_limiter import can_search, record_search, search_limit_state
from app.services.vote_service import cast_vote, vote_limit_state, votes_remaining


def _vote(client, entry_id: str):
    return client.post("/api/votes", json={"queue_entry_id": entry_id})


def _search(client, query: str = "valid query"):
    return client.get("/api/youtube/search", params={"q": query})


def test_first_vote_at_full_quota_sets_reset_at(
    dev_participant_client, queued_entry, db_session
):
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"][
        "id"
    ]
    before = dev_participant_client.get("/api/participant/state").json()
    assert before["votes_quota_reset_at"] is None
    assert before["votes_remaining"] == 2

    assert _vote(dev_participant_client, queued_entry.id).status_code == 201

    state = dev_participant_client.get("/api/participant/state").json()
    assert state["votes_remaining"] == 1
    assert state["votes_quota_reset_at"] is not None

    participant = db_session.get(Participant, participant_id)
    assert participant.votes_quota_reset_at is not None


def test_second_vote_keeps_same_reset_at(
    dev_participant_client, queued_entry, second_queued_entry
):
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    first_state = dev_participant_client.get("/api/participant/state").json()
    first_reset = first_state["votes_quota_reset_at"]
    assert first_reset is not None

    assert _vote(dev_participant_client, second_queued_entry.id).status_code == 201
    second_state = dev_participant_client.get("/api/participant/state").json()
    assert second_state["votes_quota_reset_at"] == first_reset


def test_expired_vote_window_restores_full_quota(
    dev_participant_client, queued_entry, second_queued_entry, db_session
):
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"][
        "id"
    ]
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    assert _vote(dev_participant_client, second_queued_entry.id).status_code == 201

    participant = db_session.get(Participant, participant_id)
    participant.votes_quota_reset_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    state = dev_participant_client.get("/api/participant/state").json()
    assert state["votes_remaining"] == 2
    assert state["votes_quota_reset_at"] is None


def test_invalid_vote_does_not_start_window(
    dev_participant_client, playing_entry, db_session
):
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"][
        "id"
    ]
    response = _vote(dev_participant_client, playing_entry.id)
    assert response.status_code == 409

    participant = db_session.get(Participant, participant_id)
    assert participant.votes_quota_reset_at is None


def test_search_records_row_and_sets_reset_at(
    dev_participant_client, youtube_api_keys, monkeypatch, db_session
):
    from tests.conftest import make_youtube_search_item, make_youtube_search_response
    from tests.test_youtube_search import _FakeResponse, _mock_youtube_fetch

    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"][
        "id"
    ]

    def handler(url, timeout=0):
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    _mock_youtube_fetch(monkeypatch, handler)
    before = dev_participant_client.get("/api/participant/state").json()
    assert before["searches_quota_reset_at"] is None
    assert before["searches_remaining"] == 10

    assert _search(dev_participant_client).status_code == 200

    state = dev_participant_client.get("/api/participant/state").json()
    assert state["searches_remaining"] == 9
    assert state["searches_quota_reset_at"] is not None
    assert (
        db_session.query(ParticipantSearch)
        .filter(ParticipantSearch.participant_id == participant_id)
        .count()
        == 1
    )


def test_invalid_search_query_does_not_record(
    dev_participant_client, youtube_api_keys, db_session
):
    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"][
        "id"
    ]
    response = _search(dev_participant_client, "a")
    assert response.status_code == 422

    participant = db_session.get(Participant, participant_id)
    assert participant.searches_quota_reset_at is None
    assert (
        db_session.query(ParticipantSearch)
        .filter(ParticipantSearch.participant_id == participant_id)
        .count()
        == 0
    )


def test_url_submit_does_not_touch_search_window(
    dev_participant_client, monkeypatch, sample_video_id, db_session
):
    from tests.test_youtube_search import _mock_metadata, _submit

    participant_id = dev_participant_client.get("/api/participant/me").json()["participant"][
        "id"
    ]
    _mock_metadata(monkeypatch)
    response = _submit(dev_participant_client, sample_video_id)
    assert response.status_code == 201

    participant = db_session.get(Participant, participant_id)
    assert participant.searches_quota_reset_at is None
    assert (
        db_session.query(ParticipantSearch)
        .filter(ParticipantSearch.participant_id == participant_id)
        .count()
        == 0
    )


def test_state_returns_stable_reset_at_across_calls(
    dev_participant_client, queued_entry
):
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    first = dev_participant_client.get("/api/participant/state").json()
    second = dev_participant_client.get("/api/participant/state").json()
    assert first["votes_quota_reset_at"] == second["votes_quota_reset_at"]


def test_vote_limit_exceeded_preserves_reset_at(
    dev_participant_client, queued_entry, second_queued_entry
):
    assert _vote(dev_participant_client, queued_entry.id).status_code == 201
    assert _vote(dev_participant_client, second_queued_entry.id).status_code == 201
    before = dev_participant_client.get("/api/participant/state").json()
    reset_at = before["votes_quota_reset_at"]
    assert reset_at is not None

    response = _vote(dev_participant_client, queued_entry.id)
    assert response.status_code == 409
    after = dev_participant_client.get("/api/participant/state").json()
    assert after["votes_quota_reset_at"] == reset_at
    assert after["votes_remaining"] == 0


def test_search_limit_exceeded_preserves_reset_at(
    dev_participant_client, youtube_api_keys, monkeypatch
):
    from tests.conftest import make_youtube_search_item, make_youtube_search_response
    from tests.test_youtube_search import _FakeResponse, _mock_youtube_fetch

    def handler(url, timeout=0):
        return _FakeResponse(
            make_youtube_search_response([make_youtube_search_item("aaaaaaaaaaa")])
        )

    _mock_youtube_fetch(monkeypatch, handler)
    for _ in range(10):
        assert _search(dev_participant_client).status_code == 200
    before = dev_participant_client.get("/api/participant/state").json()
    reset_at = before["searches_quota_reset_at"]
    assert reset_at is not None

    response = _search(dev_participant_client, "one too many")
    assert response.status_code == 429
    after = dev_participant_client.get("/api/participant/state").json()
    assert after["searches_quota_reset_at"] == reset_at
    assert after["searches_remaining"] == 0


def test_window_duration_matches_settings():
    assert window_duration() == timedelta(minutes=10)


def test_vote_limit_state_unit(db_session: Session):
    participant = Participant(id=str(uuid4()), display_name="P")
    db_session.add(participant)
    db_session.commit()

    remaining, reset_at = vote_limit_state(db_session, participant.id)
    assert remaining == get_settings().max_votes_10minutes_per_participant
    assert reset_at is None


def test_search_limit_helpers(db_session: Session):
    participant = Participant(id=str(uuid4()), display_name="S")
    db_session.add(participant)
    db_session.commit()

    assert can_search(db_session, participant.id) is True
    record_search(db_session, participant.id)
    db_session.commit()
    remaining, reset_at = search_limit_state(db_session, participant.id)
    assert remaining == get_settings().max_searchs_10minutes_per_participant - 1
    assert reset_at is not None
