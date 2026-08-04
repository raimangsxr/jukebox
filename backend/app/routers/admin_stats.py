from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AdminStatsResponse
from ..security import CurrentUser
from ..services.stats_service import build_admin_stats_response

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> AdminStatsResponse:
    return build_admin_stats_response(db)
