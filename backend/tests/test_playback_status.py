"""Display playback status API and SSE routing."""

from app.services import playback_status_service, sse_hub


def test_playback_status_requires_auth(client):
    assert client.get("/api/display/playback-status").status_code == 401
    assert client.post(
        "/api/display/playback-status",
        json={"audio_mode": "sound"},
    ).status_code == 401


def test_playback_status_round_trip(authed_client):
    assert authed_client.get("/api/display/playback-status").json()["audio_mode"] == "idle"

    response = authed_client.post(
        "/api/display/playback-status",
        json={"audio_mode": "sound"},
    )
    assert response.status_code == 200
    assert response.json()["audio_mode"] == "sound"

    assert authed_client.get("/api/display/playback-status").json()["audio_mode"] == "sound"


def test_playback_status_sse_reaches_operators_only():
    operator_q = sse_hub.subscribe(audience=sse_hub.OPERATOR)
    participant_q = sse_hub.subscribe(
        audience=sse_hub.PARTICIPANT, participant_id="p-1"
    )
    try:
        playback_status_service.update_playback_status("muted")
        sse_hub.broadcast_playback_status(playback_status_service.get_playback_status())
        assert operator_q.get_nowait().startswith("event: playback_status")
        assert participant_q.qsize() == 0
    finally:
        sse_hub.unsubscribe(operator_q)
        sse_hub.unsubscribe(participant_q)
        playback_status_service.reset_for_tests()


def test_playback_status_post_broadcasts_sse(authed_client):
    operator_q = sse_hub.subscribe(audience=sse_hub.OPERATOR)
    try:
        response = authed_client.post(
            "/api/display/playback-status",
            json={"audio_mode": "muted"},
        )
        assert response.status_code == 200
        message = operator_q.get_nowait()
        assert message.startswith("event: playback_status")
        assert '"audio_mode": "muted"' in message
    finally:
        sse_hub.unsubscribe(operator_q)
        playback_status_service.reset_for_tests()
