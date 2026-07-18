"""Canonical public route policy for change 002."""

from app.main import create_app

PUBLIC_PATHS_002 = {
    "/api/health": {"get"},
    "/api/auth/login": {"post"},
    "/api/auth/token": {"post"},
    "/api/auth/google/login": {"get"},
    "/api/auth/google/callback": {"get"},
    "/api/youtube/search/config": {"get"},
}

PROTECTED_PATHS_002 = {
    "/api/auth/me": {"get"},
    "/api/tokens": {"get", "post"},
}

PROTECTED_PATHS_004 = {
    "/api/state": {"get"},
    "/api/events/stream": {"get"},
    "/api/queue/pending": {"get"},
    "/api/queue/{entry_id}/approve": {"post"},
    "/api/queue/{entry_id}/reject": {"post"},
    "/api/queue/skip": {"post"},
}


PROTECTED_PATHS_005 = {
    "/api/participant/me": {"get"},
    "/api/participant/state": {"get"},
    "/api/participant/submissions": {"get"},
    "/api/votes": {"post"},
    "/api/queue/submit": {"post"},
    "/api/youtube/search": {"get"},
}


def test_public_route_policy_matches_contract():
    schema = create_app().openapi()["paths"]
    for path, methods in PUBLIC_PATHS_002.items():
        assert path in schema, f"missing public path {path}"
        for method in methods:
            assert method in schema[path], f"{path} missing {method}"


def test_protected_routes_exist_in_openapi():
    schema = create_app().openapi()["paths"]
    for path, methods in PROTECTED_PATHS_002.items():
        assert path in schema, f"missing path {path}"
        for method in methods:
            assert method in schema[path], f"{path} missing {method}"
    for path, methods in PROTECTED_PATHS_004.items():
        assert path in schema, f"missing path {path}"
        for method in methods:
            assert method in schema[path], f"{path} missing {method}"
    for path, methods in PROTECTED_PATHS_005.items():
        assert path in schema, f"missing path {path}"
        for method in methods:
            assert method in schema[path], f"{path} missing {method}"


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_me_requires_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_tokens_require_auth(client):
    response = client.get("/api/tokens")
    assert response.status_code == 401


def test_state_requires_auth(client):
    response = client.get("/api/state")
    assert response.status_code == 401


def test_queue_pending_requires_auth(client):
    response = client.get("/api/queue/pending")
    assert response.status_code == 401


def test_participant_me_requires_auth(client):
    response = client.get("/api/participant/me")
    assert response.status_code == 401


def test_votes_require_participant_auth(client, queued_entry):
    response = client.post("/api/votes", json={"queue_entry_id": queued_entry.id})
    assert response.status_code == 401


def test_submit_requires_participant_auth(client):
    response = client.post(
        "/api/queue/submit",
        json={"youtube_url_or_id": "dQw4w9WgXcQ"},
    )
    assert response.status_code == 401


def test_submissions_require_participant_auth(client):
    response = client.get("/api/participant/submissions")
    assert response.status_code == 401


def test_youtube_search_config_is_public(client):
    response = client.get("/api/youtube/search/config")
    assert response.status_code == 200


def test_youtube_search_requires_participant_auth(client):
    response = client.get("/api/youtube/search", params={"q": "test query"})
    assert response.status_code == 401
