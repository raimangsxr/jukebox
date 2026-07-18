from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from ..config import get_settings

COOKIE_NAME = "jukebox_participant_session"
SERIALIZER_SALT = "jukebox-participant-session"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().session_secret, salt=SERIALIZER_SALT)


def set_participant_cookie(response: Response, participant_id: str) -> None:
    settings = get_settings()
    token = _serializer().dumps({"participant_id": participant_id})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=60 * 60 * 24 * 7,
    )


def clear_participant_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME)


def read_participant_id(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = _serializer().loads(token)
    except BadSignature:
        return None
    participant_id = payload.get("participant_id")
    if not isinstance(participant_id, str) or not participant_id:
        return None
    return participant_id
