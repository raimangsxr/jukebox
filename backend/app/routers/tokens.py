from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ApiToken
from ..schemas import (
    ApiTokenRead,
    ApiTokenWithSecret,
    TokenCreateRequest,
    TokenCreateResponse,
    TokenListResponse,
)
from ..security import CurrentUser, generate_token, hash_token


router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("", response_model=TokenListResponse)
def list_tokens(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> TokenListResponse:
    rows = (
        db.query(ApiToken)
        .filter(ApiToken.user_id == current_user.id)
        .order_by(ApiToken.created_at.desc())
        .all()
    )
    return TokenListResponse(
        tokens=[ApiTokenRead.model_validate(row) for row in rows]
    )


@router.post("", response_model=TokenCreateResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    payload: TokenCreateRequest,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> TokenCreateResponse:
    plaintext = generate_token()
    row = ApiToken(
        id=str(uuid4()),
        user_id=current_user.id,
        label=payload.label,
        token_hash=hash_token(plaintext),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TokenCreateResponse(
        token=ApiTokenWithSecret(
            id=row.id,
            label=row.label,
            created_at=row.created_at,
            last_used_at=row.last_used_at,
            revoked_at=row.revoked_at,
            token=plaintext,
        )
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    row = db.get(ApiToken, token_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="token not found")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your token")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
