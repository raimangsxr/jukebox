from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas import SearchConfigResponse, SearchResponse
from ..security import CurrentParticipant
from ..services import search_rate_limiter
from ..services.youtube_search_service import search_videos, validate_search_query


router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.get("/search/config", response_model=SearchConfigResponse)
def get_search_config() -> SearchConfigResponse:
    keys = get_settings().youtube_api_keys
    enabled = bool(keys.strip())
    return SearchConfigResponse(enabled=enabled)


@router.get("/search", response_model=SearchResponse)
def search_youtube(
    participant: CurrentParticipant,
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> SearchResponse:
    del db
    validate_search_query(q)
    if not search_rate_limiter.check_and_record(participant.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="search rate limit exceeded",
        )
    results = search_videos(q)
    return SearchResponse(results=results)
