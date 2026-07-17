from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.models import ApiToken


def test_login_success(client: TestClient, operator_credentials):
    response = client.post("/api/auth/login", json=operator_credentials)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == operator_credentials["username"]
    assert "jukebox_session" in response.cookies


def test_login_wrong_password(client: TestClient, operator_credentials):
    response = client.post(
        "/api/auth/login",
        json={"username": operator_credentials["username"], "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


def test_login_unknown_user(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "irrelevant"},
    )
    assert response.status_code == 401


def test_login_missing_field(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "op"})
    assert response.status_code == 422


def test_logout_clears_cookie(client: TestClient, operator_credentials):
    login = client.post("/api/auth/login", json=operator_credentials)
    assert login.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200

    response = client.post("/api/auth/logout")
    assert response.status_code == 204

    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 401


def test_me_without_session_returns_401(client: TestClient):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_session_returns_user(client: TestClient, operator_credentials):
    client.post("/api/auth/login", json=operator_credentials)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == operator_credentials["username"]


def test_token_exchange_success(
    client: TestClient,
    authed_client: TestClient,
    operator_credentials,
    embed_token,
):
    plaintext = embed_token["plaintext"]
    token_id = embed_token["id"]

    response = client.post("/api/auth/token", json={"token": plaintext})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == operator_credentials["username"]
    assert "jukebox_session" in response.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200

    listed = authed_client.get("/api/tokens")
    assert listed.status_code == 200
    rows = {t["id"]: t for t in listed.json()["tokens"]}
    assert token_id in rows
    assert rows[token_id]["last_used_at"] is not None


def test_token_exchange_unknown_token_returns_401(client: TestClient):
    response = client.post(
        "/api/auth/token",
        json={"token": "this-token-does-not-exist-abcdef123456"},
    )
    assert response.status_code == 401


def test_token_exchange_revoked_token_returns_401(
    client: TestClient,
    db_session,
    embed_token,
):
    row = db_session.get(ApiToken, embed_token["id"])
    row.revoked_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.post("/api/auth/token", json={"token": embed_token["plaintext"]})
    assert response.status_code == 401


def test_token_validation_error(client: TestClient):
    response = client.post("/api/auth/token", json={"token": "short"})
    assert response.status_code == 422
