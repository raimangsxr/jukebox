from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    FillerReserveAddRequest,
    FillerReserveBatchValidation,
    FillerReserveEnqueueBatchRequest,
    FillerReserveEntryRead,
    FillerReserveListResponse,
    FillerReservePlaylistRequest,
    FillerReserveReorderRequest,
    QueueEntryRead,
)
from ..security import CurrentUser
from ..services import filler_reserve_service


router = APIRouter(prefix="/api/filler-reserve", tags=["filler-reserve"])


@router.get("", response_model=FillerReserveListResponse)
def list_filler_reserve(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> FillerReserveListResponse:
    return FillerReserveListResponse(entries=filler_reserve_service.list_reserve_reads(db))


@router.delete("", status_code=204)
def clear_filler_reserve(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    filler_reserve_service.clear_reserve(db)


@router.get("/export")
def export_filler_reserve(
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    content = filler_reserve_service.export_reserve_csv(db)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="filler-reserve-{date_str}.csv"'
        },
    )


@router.post("/import/validate", response_model=FillerReserveBatchValidation)
async def validate_filler_reserve_import(
    _user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> FillerReserveBatchValidation:
    content = await file.read()
    result = filler_reserve_service.validate_import_file(db, content)
    return result.validation


@router.post("/import", response_model=FillerReserveListResponse)
async def import_filler_reserve(
    _user: CurrentUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> FillerReserveListResponse:
    content = await file.read()
    entries, validation = filler_reserve_service.commit_import_file(db, content)
    if entries is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "errors": [error.model_dump() for error in validation.errors]
            },
        )
    return FillerReserveListResponse(entries=entries)


@router.post("/playlist/validate", response_model=FillerReserveBatchValidation)
def validate_filler_reserve_playlist(
    body: FillerReservePlaylistRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> FillerReserveBatchValidation:
    result = filler_reserve_service.validate_playlist_url(db, body.youtube_playlist_url)
    return result.validation


@router.post("/playlist", response_model=FillerReserveListResponse)
def import_filler_reserve_playlist(
    body: FillerReservePlaylistRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> FillerReserveListResponse:
    entries, validation = filler_reserve_service.commit_playlist_url(
        db, body.youtube_playlist_url
    )
    if entries is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "errors": [error.model_dump() for error in validation.errors]
            },
        )
    return FillerReserveListResponse(entries=entries)


@router.post("", response_model=FillerReserveEntryRead, status_code=201)
def add_filler_reserve(
    body: FillerReserveAddRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> FillerReserveEntryRead:
    entry = filler_reserve_service.add_to_reserve(
        db, body.youtube_url_or_id, body.search_query
    )
    return FillerReserveEntryRead.model_validate(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_filler_reserve(
    entry_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    filler_reserve_service.delete_from_reserve(db, entry_id)


@router.put("/reorder", response_model=FillerReserveListResponse)
def reorder_filler_reserve(
    body: FillerReserveReorderRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> FillerReserveListResponse:
    entries = filler_reserve_service.reorder_reserve(db, body.ordered_ids)
    return FillerReserveListResponse(entries=entries)


@router.post("/{entry_id}/enqueue", response_model=QueueEntryRead, status_code=201)
def enqueue_filler_reserve_entry(
    entry_id: str,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> QueueEntryRead:
    entries = filler_reserve_service.transfer_to_queue(db, [entry_id])
    return QueueEntryRead.model_validate(entries[0])


@router.post("/enqueue-batch", response_model=list[QueueEntryRead], status_code=201)
def enqueue_filler_reserve_batch(
    body: FillerReserveEnqueueBatchRequest,
    _user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[QueueEntryRead]:
    entries = filler_reserve_service.transfer_to_queue(db, body.ids)
    return [QueueEntryRead.model_validate(entry) for entry in entries]
