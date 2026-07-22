import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import StateResponse
from ..security import CurrentUser, StreamSubscriber
from ..services.sse_hub import format_state_event, subscribe, unsubscribe
from ..services.state_service import build_state_response


router = APIRouter(prefix="/api", tags=["state"])


@router.get("/state", response_model=StateResponse)
def get_state(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> StateResponse:
    return build_state_response(db)


@router.get("/events/stream")
async def events_stream(
    request: Request,
    subscriber: StreamSubscriber,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    async def event_generator():
        initial = build_state_response(db)
        yield format_state_event(initial)
        queue = subscribe(
            audience=subscriber.audience,
            participant_id=subscriber.participant_id,
        )
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
