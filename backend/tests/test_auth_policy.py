"""Canonical public route policy for change 002."""

from app.main import create_app

PUBLIC_PATHS_002 = {
    "/api/health": {"get"},
    "/api/auth/login": {"post"},
    "/api/auth/token": {"post"},
}

PROTECTED_PATHS_002 = {
    "/api/auth/me": {"get"},
    "/api/tokens": {"get", "post"},
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


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_me_requires_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_tokens_require_auth(client):
    response = client.get("/api/tokens")
    assert response.status_code == 401
