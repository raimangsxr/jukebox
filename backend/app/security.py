import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import ApiToken, User


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
