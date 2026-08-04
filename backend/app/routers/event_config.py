from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EVENT_CONFIG_SINGLETON_ID, EventConfig, QueueMode
from ..schemas import EventConfigRead, EventConfigUpdate, FillerAutoInjectUpdate, QueueModeUpdate
from ..security import CurrentUser
from ..services.state_service import bump_revision


router = APIRouter(prefix="/api/event-config", tags=["event-config"])

# Single supported theme for this change (010-hardening-and-polish, FR-019):
# the existing dark theme. Additional themes are out of scope.
SUPPORTED_THEMES = {"dark"}


def _get_config(db: Session) -> EventConfig:
    config = db.get(EventConfig, EVENT_CONFIG_SINGLETON_ID)
    if config is None:  # pragma: no cover - bootstrap guarantees the singleton
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="event config missing",
        )
    return config


@router.get("", response_model=EventConfigRead)
def get_event_config(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> EventConfigRead:
    return EventConfigRead.model_validate(_get_config(db))


@router.put("", response_model=EventConfigRead)
def update_event_config(
    payload: EventConfigUpdate,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> EventConfigRead:
    if payload.theme not in SUPPORTED_THEMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="unsupported theme",
        )
    config = _get_config(db)
    config.name = payload.name
    config.subtitle = payload.subtitle
    config.app_height_px = payload.app_height_px
    config.theme = payload.theme
    config.queue_visible_count = payload.queue_visible_count
    db.commit()
    db.refresh(config)
    # Propagate to kiosk/admin via the SSE `state` snapshot without a reload.
    bump_revision(db)
    return EventConfigRead.model_validate(config)


@router.put("/filler-auto-inject", response_model=EventConfigRead)
def update_filler_auto_inject(
    payload: FillerAutoInjectUpdate,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> EventConfigRead:
    config = _get_config(db)
    was_enabled = config.filler_auto_inject_enabled
    config.filler_auto_inject_enabled = payload.filler_auto_inject_enabled
    db.commit()
    db.refresh(config)
    if not was_enabled and payload.filler_auto_inject_enabled:
        from ..services.filler_reserve_service import maybe_inject_from_reserve

        maybe_inject_from_reserve(db)
    bump_revision(db)
    return EventConfigRead.model_validate(config)


@router.put("/queue-mode", response_model=EventConfigRead)
def update_queue_mode(
    payload: QueueModeUpdate,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> EventConfigRead:
    if payload.queue_mode not in {QueueMode.moderated.value, QueueMode.free.value}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="unsupported queue mode",
        )
    config = _get_config(db)
    config.queue_mode = payload.queue_mode
    db.commit()
    db.refresh(config)
    bump_revision(db)
    return EventConfigRead.model_validate(config)

