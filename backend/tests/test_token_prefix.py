"""API-token prefix lookup and legacy rejection (010, FR-008 / SC-004)."""

from uuid import uuid4

from app import security
from app.models import ApiToken, User


def _operator(db_session, username):
    return db_session.query(User).filter(User.username == username).one()


def test_exchange_succeeds_with_prefixed_token(client, embed_token):
    response = client.post("/api/auth/token", json={"token": embed_token["plaintext"]})
    assert response.status_code == 200


def test_legacy_token_without_prefix_is_rejected(
    client, db_session, operator_credentials
):
    user = _operator(db_session, operator_credentials["username"])
    plaintext = security.generate_token()
    # Simulate a pre-migration token: token_prefix stays NULL.
    db_session.add(
        ApiToken(
            id=str(uuid4()),
            user_id=user.id,
            label="legacy",
            token_hash=security.hash_token(plaintext),
        )
    )
    db_session.commit()

    response = client.post("/api/auth/token", json={"token": plaintext})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid or revoked token"


def test_lookup_verifies_at_most_one_hash(
    client, db_session, operator_credentials, monkeypatch
):
    user = _operator(db_session, operator_credentials["username"])
    plaintexts = []
    for i in range(3):
        p = security.generate_token()
        db_session.add(
            ApiToken(
                id=str(uuid4()),
                user_id=user.id,
                label=f"t{i}",
                token_prefix=security.token_prefix(p),
                token_hash=security.hash_token(p),
            )
        )
        plaintexts.append(p)
    db_session.commit()

    calls = {"n": 0}
    real_verify = security.verify_token

    def counting_verify(plaintext, hashed):
        calls["n"] += 1
        return real_verify(plaintext, hashed)

    monkeypatch.setattr(security, "verify_token", counting_verify)

    response = client.post("/api/auth/token", json={"token": plaintexts[1]})
    assert response.status_code == 200
    # Indexed prefix narrows candidates to the single matching row.
    assert calls["n"] <= 1
