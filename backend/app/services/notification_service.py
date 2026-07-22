from ..models import QueueEntry, QueueEntryStatus
from ..schemas import NotificationEventRead
from .sse_hub import deliver_notification


def emit_song_approved(entry: QueueEntry) -> None:
    participant_id = entry.submitted_by_participant_id
    if not participant_id:
        return
    deliver_notification(
        participant_id,
        NotificationEventRead(
            type="song.approved",
            queue_entry_id=entry.id,
            participant_id=participant_id,
            title=entry.title,
        ),
    )


def emit_song_up_next(entry: QueueEntry) -> None:
    participant_id = entry.submitted_by_participant_id
    if not participant_id:
        return
    if entry.status != QueueEntryStatus.queued:
        return
    deliver_notification(
        participant_id,
        NotificationEventRead(
            type="song.up_next",
            queue_entry_id=entry.id,
            participant_id=participant_id,
            title=entry.title,
        ),
    )
