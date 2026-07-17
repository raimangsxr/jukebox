from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ApiToken, User
from ..schemas import (
    LoginRequest,
    MeResponse,
    TokenExchangeRequest,
    UserRead,
)
from ..security import (
    CurrentUser,
    find_active_token,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=MeResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MeResponse:
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    request.session["user_id"] = user.id
    return MeResponse(user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(user=UserRead.model_validate(current_user))


@router.post("/token", response_model=MeResponse)
def exchange_token(
    payload: TokenExchangeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MeResponse:
    token = find_active_token(db, payload.token)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or revoked token",
        )

    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or revoked token",
        )

    token.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(token)

    request.session["user_id"] = user.id
    return MeResponse(user=UserRead.model_validate(user))
