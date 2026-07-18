from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.google_oauth_service import (
    build_authorize_url,
    complete_google_callback,
    create_oauth_state,
)
from ..services.participant_session import set_participant_cookie


router = APIRouter(prefix="/api/auth/google", tags=["auth-google"])


@router.get("/login")
def google_login() -> RedirectResponse:
    state = create_oauth_state()
    url = build_authorize_url(state)
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
def google_callback(
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    redirect_url, participant_id = complete_google_callback(
        db,
        code=code,
        state=state,
        error=error,
    )
    response = RedirectResponse(url=redirect_url, status_code=302)
    if participant_id:
        set_participant_cookie(response, participant_id)
    return response
