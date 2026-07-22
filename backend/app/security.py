import secrets
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import ApiToken, Participant, User
from .services import sse_hub
from .services.participant_session import read_participant_id


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    return pwd_context.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plaintext, hashed)
    except ValueError:
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(plaintext: str) -> str:
    return pwd_context.hash(plaintext)


def verify_token(plaintext: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plaintext, hashed)
    except ValueError:
        return False


def find_active_token(db: Session, plaintext: str) -> ApiToken | None:
    rows = (
        db.execute(select(ApiToken).where(ApiToken.revoked_at.is_(None)))
        .scalars()
        .all()
    )
    for row in rows:
        if verify_token(plaintext, row.token_hash):
            return row
    return None


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
        )
    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_participant(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Participant:
    participant_id = read_participant_id(request)
    if not participant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
        )
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
        )
    return participant


CurrentParticipant = Annotated[Participant, Depends(get_current_participant)]


@dataclass
class StreamIdentity:
    """Audience of an authorized `/api/events/stream` connection.

    Used by the SSE hub to route events (operator-only vs participant-targeted).
    """

    audience: str
    participant_id: str | None = None


def get_stream_subscriber(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> StreamIdentity:
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
        if user is not None:
            return StreamIdentity(audience=sse_hub.OPERATOR)
    participant_id = read_participant_id(request)
    if participant_id and db.get(Participant, participant_id) is not None:
        return StreamIdentity(
            audience=sse_hub.PARTICIPANT, participant_id=participant_id
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not authenticated",
    )


StreamSubscriber = Annotated[StreamIdentity, Depends(get_stream_subscriber)]
