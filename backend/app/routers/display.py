from fastapi import APIRouter

from ..schemas import PlaybackStatusRead, PlaybackStatusUpdate
from ..security import CurrentUser
from ..services.playback_status_service import get_playback_status, update_playback_status
from ..services.sse_hub import broadcast_playback_status


router = APIRouter(prefix="/api/display", tags=["display"])


@router.get("/playback-status", response_model=PlaybackStatusRead)
def read_playback_status(_user: CurrentUser) -> PlaybackStatusRead:
    return get_playback_status()


@router.post("/playback-status", response_model=PlaybackStatusRead)
def post_playback_status(
    payload: PlaybackStatusUpdate,
    _user: CurrentUser,
) -> PlaybackStatusRead:
    status = update_playback_status(payload.audio_mode)
    broadcast_playback_status(status)
    return status
