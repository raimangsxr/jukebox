from fastapi.testclient import TestClient


def test_list_tokens_requires_auth(client: TestClient):
    response = client.get("/api/tokens")
    assert response.status_code == 401


def test_create_token_returns_plaintext_once(authed_client: TestClient):
    response = authed_client.post("/api/tokens", json={"label": "kiosk-iframe"})
    assert response.status_code == 201
    body = response.json()
    assert "token" in body["token"]
    plaintext = body["token"]["token"]
    assert isinstance(plaintext, str) and len(plaintext) >= 10
    assert body["token"]["label"] == "kiosk-iframe"
    assert body["token"]["revoked_at"] is None


def test_list_tokens_omits_plaintext(authed_client: TestClient):
    authed_client.post("/api/tokens", json={"label": "x"})
    response = authed_client.get("/api/tokens")
    assert response.status_code == 200
    tokens = response.json()["tokens"]
    assert len(tokens) == 1
    assert "token" not in tokens[0]
    assert tokens[0]["label"] == "x"


def test_revoke_token_returns_204(authed_client: TestClient):
    create = authed_client.post("/api/tokens", json={"label": "y"})
    token_id = create.json()["token"]["id"]
    response = authed_client.delete(f"/api/tokens/{token_id}")
    assert response.status_code == 204

    listed = authed_client.get("/api/tokens")
    assert listed.status_code == 200
    rows = {t["id"]: t for t in listed.json()["tokens"]}
    assert rows[token_id]["revoked_at"] is not None


def test_revoke_unknown_token_returns_404(authed_client: TestClient):
    response = authed_client.delete(
        "/api/tokens/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_label_persists_verbatim(authed_client: TestClient):
    label = "Kiosk sala"
    authed_client.post("/api/tokens", json={"label": label})
    listed = authed_client.get("/api/tokens").json()["tokens"]
    assert listed[0]["label"] == label


def test_create_token_validation_error(authed_client: TestClient):
    response = authed_client.post("/api/tokens", json={"label": ""})
    assert response.status_code == 422


def test_unauthed_cannot_revoke(authed_client: TestClient, db_session):
    from app.database import get_db
    from app.main import create_app

    create = authed_client.post("/api/tokens", json={"label": "z"})
    token_id = create.json()["token"]["id"]

    app = create_app()
    app.router.lifespan_context = None

    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    c = TestClient(app)
    response = c.delete(f"/api/tokens/{token_id}")
    assert response.status_code == 401
