"""CORS policy tests (010-hardening-and-polish, FR-007)."""

ORIGIN = "http://localhost:4200"


def test_preflight_allows_content_type(client):
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allow_headers
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_preflight_rejects_unlisted_header(client):
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-evil-header",
        },
    )
    # Starlette returns 400 for disallowed CORS request headers when
    # allow_headers is an explicit list (not "*").
    assert response.status_code == 400


def test_health_unaffected_by_cors_scope(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
