"""Filler reserve, operator submit, and auto-inject tests."""

from uuid import uuid4

from app.models import (
    EVENT_CONFIG_SINGLETON_ID,
    EventConfig,
    FillerReserveEntry,
    MAX_FILLER_RESERVE_ENTRIES,
    MAX_QUEUED_ENTRIES,
    QueueEntry,
    QueueEntryPriority,
    QueueEntrySource,
    QueueEntryStatus,
)
from app.services.state_service import get_or_create_runtime


def _mock_batch_metadata(monkeypatch):
    def _batch(video_ids, db=None):
        return {
            video_id: (
                f"Title {video_id}",
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                200,
            )
            for video_id in video_ids
        }

    monkeypatch.setattr(
        "app.services.filler_reserve_service.fetch_youtube_videos_details_batch",
        _batch,
    )


def _mock_metadata(monkeypatch, *, title="Filler Song"):
    from app.services import queue_service

    def _ok(video_id: str):
        return title, f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    monkeypatch.setattr(queue_service, "fetch_youtube_metadata_strict", _ok)
    monkeypatch.setattr(queue_service, "fetch_youtube_duration_sec", lambda *_a, **_k: 200)


def _add_reserve(db_session, video_id: str, position: int) -> FillerReserveEntry:
    entry = FillerReserveEntry(
        id=str(uuid4()),
        youtube_video_id=video_id,
        title=f"Reserve {video_id}",
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        original_query=video_id,
        position=position,
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_reserve_routes_require_operator(client):
    assert client.get("/api/filler-reserve").status_code == 401
    assert (
        client.post("/api/filler-reserve", json={"youtube_url_or_id": "dQw4w9WgXcQ"}).status_code
        == 401
    )


def test_reserve_routes_forbid_participant(dev_participant_client):
    assert dev_participant_client.get("/api/filler-reserve").status_code == 401
    assert (
        dev_participant_client.post(
            "/api/filler-reserve", json={"youtube_url_or_id": "dQw4w9WgXcQ"}
        ).status_code
        == 401
    )


def test_add_list_delete_reserve(authed_client, monkeypatch, sample_video_id):
    _mock_metadata(monkeypatch)
    add = authed_client.post(
        "/api/filler-reserve",
        json={"youtube_url_or_id": sample_video_id},
    )
    assert add.status_code == 201
    entry_id = add.json()["id"]

    listing = authed_client.get("/api/filler-reserve")
    assert listing.status_code == 200
    assert len(listing.json()["entries"]) == 1
    assert listing.json()["entries"][0]["youtube_video_id"] == sample_video_id

    delete = authed_client.delete(f"/api/filler-reserve/{entry_id}")
    assert delete.status_code == 204
    assert authed_client.get("/api/filler-reserve").json()["entries"] == []


def test_reserve_duplicate_blocked(authed_client, monkeypatch, queued_entry):
    _mock_metadata(monkeypatch)
    response = authed_client.post(
        "/api/filler-reserve",
        json={"youtube_url_or_id": queued_entry.youtube_video_id},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "video already in queue"


def test_reserve_max_entries(authed_client, monkeypatch, db_session):
    _mock_metadata(monkeypatch)
    for index in range(MAX_FILLER_RESERVE_ENTRIES):
        _add_reserve(db_session, f"{index:011d}"[:11], index + 1)

    response = authed_client.post(
        "/api/filler-reserve",
        json={"youtube_url_or_id": "dQw4w9WgXcQ"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "filler reserve is full"


def test_reserve_reorder(authed_client, db_session):
    first = _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    second = _add_reserve(db_session, "jNQXAC9IVRw", 2)

    response = authed_client.put(
        "/api/filler-reserve/reorder",
        json={"ordered_ids": [second.id, first.id]},
    )
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert entries[0]["id"] == second.id
    assert entries[0]["position"] == 1


def test_enqueue_consumes_reserve(authed_client, db_session, monkeypatch):
    _mock_metadata(monkeypatch)
    reserve = _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    before = get_or_create_runtime(db_session).revision

    response = authed_client.post(f"/api/filler-reserve/{reserve.id}/enqueue")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] in ("queued", "playing")
    assert data["priority"] == QueueEntryPriority.low.value

    db_session.expire_all()
    queued = db_session.get(QueueEntry, data["id"])
    assert queued.source == QueueEntrySource.operator_filler.value
    assert db_session.get(FillerReserveEntry, reserve.id) is None
    assert get_or_create_runtime(db_session).revision > before


def test_enqueue_batch(authed_client, db_session, monkeypatch):
    _mock_metadata(monkeypatch)
    first = _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    second = _add_reserve(db_session, "jNQXAC9IVRw", 2)

    response = authed_client.post(
        "/api/filler-reserve/enqueue-batch",
        json={"ids": [first.id, second.id]},
    )
    assert response.status_code == 201
    assert len(response.json()) == 2
    assert authed_client.get("/api/filler-reserve").json()["entries"] == []


def test_operator_submit(authed_client, monkeypatch, sample_video_id, db_session):
    _mock_metadata(monkeypatch)
    before = get_or_create_runtime(db_session).revision
    response = authed_client.post(
        "/api/queue/operator-submit",
        json={"youtube_url_or_id": sample_video_id},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] in ("queued", "playing")
    assert data["priority"] == QueueEntryPriority.low.value
    db_session.expire_all()
    entry = db_session.get(QueueEntry, data["id"])
    assert entry.source == QueueEntrySource.operator_direct.value
    assert get_or_create_runtime(db_session).revision > before


def test_operator_submit_forbidden_for_participant(dev_participant_client, monkeypatch, sample_video_id):
    _mock_metadata(monkeypatch)
    response = dev_participant_client.post(
        "/api/queue/operator-submit",
        json={"youtube_url_or_id": sample_video_id},
    )
    assert response.status_code == 401


def test_enqueue_queue_full(authed_client, db_session, monkeypatch):
    _mock_metadata(monkeypatch)
    reserve = _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    for index in range(MAX_QUEUED_ENTRIES):
        video_id = f"{index:011d}"
        db_session.add(
            QueueEntry(
                id=str(uuid4()),
                youtube_video_id=video_id,
                title=f"Queued {index}",
                status=QueueEntryStatus.queued,
                original_query=video_id,
                position=index + 1,
            )
        )
    db_session.commit()

    response = authed_client.post(f"/api/filler-reserve/{reserve.id}/enqueue")
    assert response.status_code == 409
    assert response.json()["detail"] == "queue is full"


def test_auto_inject_on_idle_skip(authed_client, db_session, playing_entry, monkeypatch):
    _mock_metadata(monkeypatch)
    _add_reserve(db_session, "kJQP7kiw5Fk", 1)
    before = get_or_create_runtime(db_session).revision

    response = authed_client.post("/api/queue/skip")
    assert response.status_code == 200
    data = response.json()
    assert data["now_playing"]["youtube_video_id"] == "kJQP7kiw5Fk"
    db_session.expire_all()
    entry = db_session.get(QueueEntry, data["now_playing"]["id"])
    assert entry.source == QueueEntrySource.auto_inject.value
    assert get_or_create_runtime(db_session).revision > before


def test_auto_inject_disabled(authed_client, db_session, playing_entry, monkeypatch):
    _mock_metadata(monkeypatch)
    config = db_session.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    config.filler_auto_inject_enabled = False
    db_session.commit()
    _add_reserve(db_session, "kJQP7kiw5Fk", 1)

    response = authed_client.post("/api/queue/skip")
    assert response.status_code == 200
    assert response.json()["now_playing"] is None


def test_auto_inject_empty_reserve_noop(authed_client, playing_entry):
    response = authed_client.post("/api/queue/skip")
    assert response.status_code == 200
    assert response.json()["now_playing"] is None


def test_source_audit_all_creation_paths(
    authed_client,
    dev_participant_client,
    db_session,
    monkeypatch,
    sample_video_id,
    participant,
):
    from datetime import datetime, timezone

    _mock_metadata(monkeypatch)

    participant_entry = dev_participant_client.post(
        "/api/queue/submit",
        json={"youtube_url_or_id": sample_video_id},
    )
    assert participant_entry.status_code == 201
    assert (
        db_session.get(QueueEntry, participant_entry.json()["id"]).source
        == QueueEntrySource.participant.value
    )

    direct = authed_client.post(
        "/api/queue/operator-submit",
        json={"youtube_url_or_id": "jNQXAC9IVRw"},
    )
    assert direct.status_code == 201
    assert (
        db_session.get(QueueEntry, direct.json()["id"]).source
        == QueueEntrySource.operator_direct.value
    )

    reserve = _add_reserve(db_session, "9bZkp7q19f0", 1)
    filler = authed_client.post(f"/api/filler-reserve/{reserve.id}/enqueue")
    assert filler.status_code == 201
    assert (
        db_session.get(QueueEntry, filler.json()["id"]).source
        == QueueEntrySource.operator_filler.value
    )

    played = QueueEntry(
        id=str(uuid4()),
        youtube_video_id="kJQP7kiw5Fk",
        title="Played",
        status=QueueEntryStatus.played,
        original_query="kJQP7kiw5Fk",
        finished_at=datetime.now(timezone.utc),
        submitted_by_participant_id=participant.id,
    )
    db_session.add(played)
    db_session.commit()

    requeue = authed_client.post(f"/api/queue/history/{played.id}/requeue")
    assert requeue.status_code == 201
    assert (
        db_session.get(QueueEntry, requeue.json()["id"]).source
        == QueueEntrySource.operator_requeue.value
    )

    config = db_session.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    config.filler_auto_inject_enabled = True
    db_session.commit()

    for entry in db_session.query(QueueEntry).all():
        entry.status = QueueEntryStatus.played
        entry.position = None
    runtime = get_or_create_runtime(db_session)
    runtime.now_playing_entry_id = None
    db_session.commit()

    playing = QueueEntry(
        id=str(uuid4()),
        youtube_video_id="aaaaaaaaaaa",
        title="Playing",
        status=QueueEntryStatus.playing,
        original_query="aaaaaaaaaaa",
    )
    db_session.add(playing)
    runtime.now_playing_entry_id = playing.id
    db_session.commit()

    _add_reserve(db_session, "M7lc1UVf-VE", 1)
    skip = authed_client.post("/api/queue/skip")
    assert skip.status_code == 200
    now_playing = skip.json()["now_playing"]
    assert now_playing is not None
    assert (
        db_session.get(QueueEntry, now_playing["id"]).source
        == QueueEntrySource.auto_inject.value
    )


def _csv_bytes(*lines: str) -> bytes:
    return "\n".join(lines).encode("utf-8")


def test_export_requires_operator(client):
    assert client.get("/api/filler-reserve/export").status_code == 401


def test_export_forbidden_for_participant(dev_participant_client):
    assert dev_participant_client.get("/api/filler-reserve/export").status_code == 401


def test_export_csv_order_and_format(authed_client, db_session):
    _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    _add_reserve(db_session, "jNQXAC9IVRw", 2)

    response = authed_client.get("/api/filler-reserve/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "filler-reserve-" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.csv"')

    raw = response.content
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    lines = text.strip().split("\n")
    assert lines[0] == "url"
    assert lines[1] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert lines[2] == "https://www.youtube.com/watch?v=jNQXAC9IVRw"


def test_export_empty_reserve_header_only(authed_client):
    response = authed_client.get("/api/filler-reserve/export")
    assert response.status_code == 200
    text = response.content.decode("utf-8-sig").strip()
    assert text == "url"


def test_import_validate_requires_operator(client):
    payload = {"file": ("reserve.csv", _csv_bytes("url", "dQw4w9WgXcQ"), "text/csv")}
    assert client.post("/api/filler-reserve/import/validate", files=payload).status_code == 401
    assert client.post("/api/filler-reserve/import", files=payload).status_code == 401


def test_import_forbidden_for_participant(dev_participant_client):
    payload = {"file": ("reserve.csv", _csv_bytes("url", "dQw4w9WgXcQ"), "text/csv")}
    assert dev_participant_client.post("/api/filler-reserve/import/validate", files=payload).status_code == 401
    assert dev_participant_client.post("/api/filler-reserve/import", files=payload).status_code == 401


def test_import_validate_happy_path(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ", "jNQXAC9IVRw"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["add_count"] == 2
    assert data["can_confirm"] is True
    assert data["errors"] == []


def test_import_validate_duplicate_in_file(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["can_confirm"] is False
    assert len(data["errors"]) == 1
    assert data["errors"][0]["detail"] == "duplicate in file"
    assert data["errors"][0]["line"] == 3


def test_import_validate_queue_conflict_skipped(authed_client, queued_entry, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", queued_entry.youtube_video_id, "dQw4w9WgXcQ"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    data = response.json()
    assert data["can_confirm"] is True
    assert data["add_count"] == 1
    assert data["skipped_in_queue"] == 1


def test_import_validate_skips_current_reserve(authed_client, db_session, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ", "jNQXAC9IVRw"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["skipped_in_reserve"] == 1
    assert data["add_count"] == 1
    assert data["can_confirm"] is True


def test_import_validate_invalid_url(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "not-a-url"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    data = response.json()
    assert data["can_confirm"] is False
    assert data["errors"][0]["detail"] == "invalid youtube reference"


def test_import_validate_capacity_partial(authed_client, db_session, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    for index in range(MAX_FILLER_RESERVE_ENTRIES - 1):
        _add_reserve(db_session, f"{index:011d}"[:11], index + 1)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ", "jNQXAC9IVRw", "M7lc1UVf-VE"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    data = response.json()
    assert data["add_count"] == 1
    assert data["skipped_capacity"] == 2
    assert data["can_confirm"] is True


def test_import_validate_empty_file_rejected(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    payload = {"file": ("reserve.csv", _csv_bytes("url"), "text/csv")}
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    data = response.json()
    assert data["add_count"] == 0
    assert data["can_confirm"] is False


def test_import_validate_unresolvable_skipped(authed_client, monkeypatch):
    def _batch(video_ids, db=None):
        return {
            video_ids[0]: ("Title", "https://example.com/thumb.jpg", 200)
        } if video_ids else {}

    monkeypatch.setattr(
        "app.services.filler_reserve_service.fetch_youtube_videos_details_batch",
        _batch,
    )
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ", "jNQXAC9IVRw"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    data = response.json()
    assert data["add_count"] == 1
    assert data["skipped_unresolvable"] == 1
    assert data["can_confirm"] is True


def test_import_commit_rejects_invalid(authed_client, monkeypatch, db_session):
    _mock_batch_metadata(monkeypatch)
    _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "not-a-url"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import", files=payload)
    assert response.status_code == 422
    assert "errors" in response.json()["detail"]
    listing = authed_client.get("/api/filler-reserve")
    assert len(listing.json()["entries"]) == 1


def test_import_commit_appends_reserve(authed_client, monkeypatch, db_session):
    _mock_batch_metadata(monkeypatch)
    _add_reserve(db_session, "aaaaaaaaaaa", 1)
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ", "jNQXAC9IVRw"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import", files=payload)
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert [entry["youtube_video_id"] for entry in entries] == [
        "aaaaaaaaaaa",
        "dQw4w9WgXcQ",
        "jNQXAC9IVRw",
    ]
    listing = authed_client.get("/api/filler-reserve")
    assert [entry["youtube_video_id"] for entry in listing.json()["entries"]] == [
        "aaaaaaaaaaa",
        "dQw4w9WgXcQ",
        "jNQXAC9IVRw",
    ]


def test_import_empty_file_does_not_clear(authed_client, monkeypatch, db_session):
    _mock_batch_metadata(monkeypatch)
    _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    payload = {"file": ("reserve.csv", _csv_bytes("url"), "text/csv")}
    response = authed_client.post("/api/filler-reserve/import", files=payload)
    assert response.status_code == 422
    assert len(authed_client.get("/api/filler-reserve").json()["entries"]) == 1


def test_clear_reserve(authed_client, db_session):
    _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    _add_reserve(db_session, "jNQXAC9IVRw", 2)
    response = authed_client.delete("/api/filler-reserve")
    assert response.status_code == 204
    assert authed_client.get("/api/filler-reserve").json()["entries"] == []


def test_clear_reserve_forbidden_for_participant(dev_participant_client, db_session):
    _add_reserve(db_session, "dQw4w9WgXcQ", 1)
    assert dev_participant_client.delete("/api/filler-reserve").status_code == 401


def test_playlist_validate_requires_operator(client):
    body = {"youtube_playlist_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    assert client.post("/api/filler-reserve/playlist/validate", json=body).status_code == 401


def test_playlist_validate_single_video(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    response = authed_client.post(
        "/api/filler-reserve/playlist/validate",
        json={"youtube_playlist_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["add_count"] == 1
    assert data["can_confirm"] is True


def test_playlist_commit_appends(authed_client, monkeypatch, db_session):
    _mock_batch_metadata(monkeypatch)
    _add_reserve(db_session, "aaaaaaaaaaa", 1)

    def _resolve(_url, db=None):
        return [
            (1, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            (2, "jNQXAC9IVRw", "https://www.youtube.com/watch?v=jNQXAC9IVRw"),
        ]

    monkeypatch.setattr(
        "app.services.filler_reserve_service.resolve_playlist_or_video_ids",
        _resolve,
    )
    response = authed_client.post(
        "/api/filler-reserve/playlist",
        json={"youtube_playlist_url": "https://www.youtube.com/playlist?list=PLtest"},
    )
    assert response.status_code == 200
    ids = [entry["youtube_video_id"] for entry in response.json()["entries"]]
    assert ids == ["aaaaaaaaaaa", "dQw4w9WgXcQ", "jNQXAC9IVRw"]


def test_playlist_unavailable(authed_client, monkeypatch):
    def _fail(_url, db=None):
        raise ValueError("playlist unavailable")

    monkeypatch.setattr(
        "app.services.filler_reserve_service.resolve_playlist_or_video_ids",
        _fail,
    )
    response = authed_client.post(
        "/api/filler-reserve/playlist/validate",
        json={"youtube_playlist_url": "https://example.com/not-youtube"},
    )
    data = response.json()
    assert data["can_confirm"] is False
    assert data["errors"][0]["detail"] == "playlist unavailable"


def test_playlist_too_large(authed_client, monkeypatch):
    def _resolve(_url, db=None):
        raise ValueError("playlist too large")

    monkeypatch.setattr(
        "app.services.filler_reserve_service.resolve_playlist_or_video_ids",
        _resolve,
    )
    response = authed_client.post(
        "/api/filler-reserve/playlist/validate",
        json={"youtube_playlist_url": "https://www.youtube.com/playlist?list=PLbig"},
    )
    assert response.json()["errors"][0]["detail"] == "playlist too large"


def test_playlist_duplicate_in_batch(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)

    def _resolve(_url, db=None):
        return [
            (1, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            (2, "dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        ]

    monkeypatch.setattr(
        "app.services.filler_reserve_service.resolve_playlist_or_video_ids",
        _resolve,
    )
    response = authed_client.post(
        "/api/filler-reserve/playlist/validate",
        json={"youtube_playlist_url": "https://www.youtube.com/playlist?list=PLdup"},
    )
    data = response.json()
    assert data["can_confirm"] is False
    assert data["errors"][0]["detail"] == "duplicate in batch"


def test_import_round_trip_export_append(authed_client, db_session, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    _add_reserve(db_session, "aaaaaaaaaaa", 1)
    _add_reserve(db_session, "dQw4w9WgXcQ", 2)
    _add_reserve(db_session, "jNQXAC9IVRw", 3)

    export = authed_client.get("/api/filler-reserve/export")
    assert export.status_code == 200

    clear = authed_client.delete("/api/filler-reserve")
    assert clear.status_code == 204

    import_response = authed_client.post(
        "/api/filler-reserve/import",
        files={"file": ("reserve.csv", export.content, "text/csv")},
    )
    assert import_response.status_code == 200
    entries = import_response.json()["entries"]
    assert len(entries) == 3
    assert entries[0]["youtube_video_id"] == "aaaaaaaaaaa"


def test_batch_validation_response_fields(authed_client, monkeypatch):
    _mock_batch_metadata(monkeypatch)
    payload = {"file": ("reserve.csv", _csv_bytes("url", "dQw4w9WgXcQ"), "text/csv")}
    data = authed_client.post(
        "/api/filler-reserve/import/validate", files=payload
    ).json()
    for field in (
        "add_count",
        "skipped_in_reserve",
        "skipped_in_queue",
        "skipped_unresolvable",
        "skipped_capacity",
        "can_confirm",
        "errors",
    ):
        assert field in data


def test_import_validate_calls_youtube_api(authed_client, monkeypatch):
    called = {"value": False}

    def _batch(video_ids, db=None):
        called["value"] = True
        return {
            video_id: ("Title", "https://example.com/thumb.jpg", 200)
            for video_id in video_ids
        }

    monkeypatch.setattr(
        "app.services.filler_reserve_service.fetch_youtube_videos_details_batch",
        _batch,
    )
    payload = {
        "file": (
            "reserve.csv",
            _csv_bytes("url", "dQw4w9WgXcQ"),
            "text/csv",
        )
    }
    response = authed_client.post("/api/filler-reserve/import/validate", files=payload)
    assert response.status_code == 200
    assert called["value"] is True
