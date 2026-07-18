"""Google OAuth participant login tests."""

from fastapi import HTTPException

from app.models import Participant
from app.services import google_oauth_service


def test_login_redirects_to_google(client, google_oauth_settings):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-client-id" in location
    assert "state=" in location


def test_oauth_config_disabled_by_default(client):
    response = client.get("/api/auth/google/config")
    assert response.status_code == 200
    assert response.json() == {"enabled": False}


def test_oauth_config_enabled(client, google_oauth_settings):
    response = client.get("/api/auth/google/config")
    assert response.status_code == 200
    assert response.json() == {"enabled": True}


def test_login_redirects_when_oauth_not_configured(client):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 302
    assert "oauth_error=not_configured" in response.headers["location"]


def test_callback_upserts_participant_and_sets_cookie(
    google_oauth_client, db_session, google_profile
):
    state = google_oauth_service.create_oauth_state()
    response = google_oauth_client.get(
        f"/api/auth/google/callback?code=auth-code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith(
        "http://localhost:4200/participar"
    )
    assert "oauth=ok" in response.headers["location"]
    assert "jukebox_participant_session" in response.cookies

    participant = (
        db_session.query(Participant)
        .filter(Participant.google_sub == google_profile["sub"])
        .one()
    )
    assert participant.display_name == google_profile["name"]
    assert participant.email == google_profile["email"]

    me = google_oauth_client.get("/api/participant/me")
    assert me.status_code == 200
    assert me.json()["participant"]["display_name"] == google_profile["name"]


def test_callback_reuses_existing_google_sub(
    google_oauth_client, db_session, google_participant, google_profile
):
    state = google_oauth_service.create_oauth_state()
    response = google_oauth_client.get(
        f"/api/auth/google/callback?code=auth-code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 302

    count = (
        db_session.query(Participant)
        .filter(Participant.google_sub == google_profile["sub"])
        .count()
    )
    assert count == 1

    me = google_oauth_client.get("/api/participant/me")
    assert me.json()["participant"]["id"] == google_participant.id


def test_callback_invalid_state(google_oauth_client):
    response = google_oauth_client.get(
        "/api/auth/google/callback?code=auth-code&state=bad-state",
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert "oauth_error=invalid_state" in location
    assert google_oauth_client.get("/api/participant/me").status_code == 401


def test_callback_denied(google_oauth_client):
    response = google_oauth_client.get(
        "/api/auth/google/callback?error=access_denied",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "oauth_error=denied" in response.headers["location"]


def test_callback_exchange_failed(google_oauth_client, monkeypatch):
    state = google_oauth_service.create_oauth_state()

    def _fail(code: str) -> dict:
        raise HTTPException(status_code=502, detail="exchange_failed")

    monkeypatch.setattr(google_oauth_service, "exchange_code_for_tokens", _fail)
    response = google_oauth_client.get(
        f"/api/auth/google/callback?code=auth-code&state={state}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "oauth_error=exchange_failed" in response.headers["location"]
