"""Event configuration read/update endpoint (010, FR-015..FR-017)."""

from app.models import (
    EVENT_CONFIG_DEFAULT_NAME,
    EVENT_CONFIG_SINGLETON_ID,
    EventConfig,
)


def _valid_payload(**overrides):
    payload = {
        "name": "Fiesta AMRN",
        "subtitle": "Vota tu canción",
        "app_height_px": 900,
        "theme": "dark",
        "queue_visible_count": 6,
    }
    payload.update(overrides)
    return payload


def test_get_returns_current_config(authed_client):
    response = authed_client.get("/api/event-config")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == EVENT_CONFIG_DEFAULT_NAME
    assert body["theme"] == "dark"
    assert "updated_at" in body


def test_put_persists_changes(authed_client, db_session):
    response = authed_client.put("/api/event-config", json=_valid_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Fiesta AMRN"
    assert body["subtitle"] == "Vota tu canción"
    assert body["app_height_px"] == 900
    assert body["queue_visible_count"] == 6

    config = db_session.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    assert config.name == "Fiesta AMRN"
    assert config.queue_visible_count == 6


def test_put_bumps_revision(authed_client):
    before = authed_client.get("/api/state").json()["revision"]
    authed_client.put("/api/event-config", json=_valid_payload(name="Nuevo"))
    after = authed_client.get("/api/state").json()
    assert after["revision"] > before
    assert after["event_config"]["name"] == "Nuevo"


def test_put_rejects_unsupported_theme(authed_client):
    response = authed_client.put("/api/event-config", json=_valid_payload(theme="neon"))
    assert response.status_code == 422


def test_put_rejects_out_of_range_values(authed_client):
    assert authed_client.put(
        "/api/event-config", json=_valid_payload(app_height_px=0)
    ).status_code == 422
    assert authed_client.put(
        "/api/event-config", json=_valid_payload(queue_visible_count=0)
    ).status_code == 422
    assert authed_client.put(
        "/api/event-config", json=_valid_payload(name="")
    ).status_code == 422


def test_put_rejects_participant(dev_participant_client):
    response = dev_participant_client.put("/api/event-config", json=_valid_payload())
    assert response.status_code == 401


def test_get_rejects_anonymous(client):
    assert client.get("/api/event-config").status_code == 401
