"""Operator dev-submit uses the same strict metadata validation as
participant submit (010, FR-013)."""

import pytest
from fastapi import HTTPException

from app.services import queue_service


def test_dev_submit_rejects_invalid_metadata(db_session, monkeypatch):
    def _fail(video_id):
        raise ValueError("metadata unavailable")

    monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _fail)
    monkeypatch.setattr(queue_service, "fetch_youtube_duration_sec", lambda *a, **k: None)

    with pytest.raises(HTTPException) as exc_info:
        queue_service.create_pending_entry(db_session, "dQw4w9WgXcQ")
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid youtube reference"


def test_dev_submit_accepts_valid_metadata(client, db_session, monkeypatch):
    # `client` bootstraps the event_config/runtime singletons on db_session,
    # which create_pending_entry -> bump_revision requires.
    monkeypatch.setattr(
        queue_service,
        "fetch_youtube_metadata_strict",
        lambda video_id: ("A Song", "https://i.ytimg.com/x.jpg"),
    )
    monkeypatch.setattr(queue_service, "fetch_youtube_duration_sec", lambda *a, **k: None)

    entry = queue_service.create_pending_entry(db_session, "dQw4w9WgXcQ")
    assert entry.title == "A Song"
    assert entry.youtube_video_id == "dQw4w9WgXcQ"
