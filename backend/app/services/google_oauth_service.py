import json
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from fastapi import HTTPException, status
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Participant

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
STATE_SALT = "jukebox-google-oauth-state"
SCOPES = "openid email profile"


def _state_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt=STATE_SALT)


def create_oauth_state() -> str:
    return _state_serializer().dumps({"nonce": str(uuid4())})


def verify_oauth_state(state: str | None) -> bool:
    if not state:
        return False
    try:
        payload = _state_serializer().loads(state)
    except BadSignature:
        return False
    return isinstance(payload, dict) and bool(payload.get("nonce"))


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="google oauth not configured",
        )
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    settings = get_settings()
    body = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="exchange_failed",
        ) from exc


def fetch_google_userinfo(access_token: str) -> dict:
    request = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="exchange_failed",
        ) from exc


def upsert_participant_from_google(db: Session, profile: dict) -> Participant:
    google_sub = profile.get("sub")
    if not isinstance(google_sub, str) or not google_sub:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="exchange_failed",
        )

    display_name = profile.get("name") or profile.get("email") or "Participante"
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = "Participante"
    display_name = display_name.strip()[:120]

    email = profile.get("email")
    email = email.strip()[:255] if isinstance(email, str) and email.strip() else None

    avatar_url = profile.get("picture")
    avatar_url = (
        avatar_url.strip()[:500]
        if isinstance(avatar_url, str) and avatar_url.strip()
        else None
    )

    participant = db.execute(
        select(Participant).where(Participant.google_sub == google_sub)
    ).scalar_one_or_none()

    if participant is None:
        participant = Participant(
            id=str(uuid4()),
            google_sub=google_sub,
            display_name=display_name,
            email=email,
            avatar_url=avatar_url,
        )
        db.add(participant)
    else:
        participant.display_name = display_name
        participant.email = email
        participant.avatar_url = avatar_url

    db.commit()
    db.refresh(participant)
    return participant


def complete_google_callback(
    db: Session,
    *,
    code: str | None,
    state: str | None,
    error: str | None,
) -> tuple[str, str | None]:
    settings = get_settings()
    return_url = settings.participant_oauth_return_url

    if error:
        return f"{return_url}?oauth_error=denied", None
    if not code or not verify_oauth_state(state):
        return f"{return_url}?oauth_error=invalid_state", None

    try:
        tokens = exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            return f"{return_url}?oauth_error=exchange_failed", None
        profile = fetch_google_userinfo(access_token)
        participant = upsert_participant_from_google(db, profile)
    except HTTPException:
        return f"{return_url}?oauth_error=exchange_failed", None

    separator = "&" if "?" in return_url else "?"
    return f"{return_url}{separator}oauth=ok", participant.id
