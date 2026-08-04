from sqlalchemy import case

from ..models import QueueEntry, QueueEntryPriority


def queued_order_columns():
    """Sort queued entries: votes desc, normal before low, oldest first."""
    priority_rank = case(
        (QueueEntry.priority == QueueEntryPriority.low.value, 1),
        else_=0,
    )
    return (
        QueueEntry.vote_count.desc(),
        priority_rank.asc(),
        QueueEntry.created_at.asc(),
    )
