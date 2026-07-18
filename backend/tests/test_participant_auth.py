"""Participant session and dev-auth tests."""

from app.config import get_settings


def test_dev_auth_disabled_by_default(client):
    get_settings.cache_clear()
    response = client.post("/api/participant/dev-auth", json={"display_name": "X"})
    assert response.status_code == 404


def test_dev_auth_sets_cookie(client, monkeypatch):
    monkeypatch.setenv("JUKEBOX_ALLOW_DEV_PARTICIPANT_AUTH", "true")
    get_settings.cache_clear()
    response = client.post(
        "/api/participant/dev-auth",
        json={"display_name": "Ana"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["participant"]["display_name"] == "Ana"
    assert "jukebox_participant_session" in response.cookies


def test_me_requires_participant_session(client):
    response = client.get("/api/participant/me")
    assert response.status_code == 401


def test_me_returns_participant(dev_participant_client):
    response = dev_participant_client.get("/api/participant/me")
    assert response.status_code == 200
    assert response.json()["participant"]["display_name"] == "Voter"


def test_invalid_participant_cookie(client):
    client.cookies.set("jukebox_participant_session", "not-a-valid-token")
    response = client.get("/api/participant/me")
    assert response.status_code == 401
