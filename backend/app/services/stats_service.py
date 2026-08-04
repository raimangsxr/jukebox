"""Admin statistics aggregation (read-only)."""

from __future__ import annotations

from sqlalchemy import func, select, union
from sqlalchemy.orm import Session

from ..models import Participant, QueueEntry, QueueEntryStatus, Vote
from ..schemas import (
    AdminStatsResponse,
    ParticipantRankingItem,
    QueueStatusCounts,
    SongRankingItem,
)

_TOP_LIMIT = 10


def _participant_display_label(participant: Participant) -> str:
    name = (participant.display_name or "").strip()
    if name:
        return name
    if participant.email:
        local = participant.email.split("@", 1)[0].strip()
        if local:
            return local
    return "Participante"


def _count_active_participants(db: Session) -> int:
    submission_ids = (
        select(QueueEntry.submitted_by_participant_id.label("pid"))
        .where(QueueEntry.submitted_by_participant_id.isnot(None))
        .distinct()
    )
    vote_ids = select(Vote.participant_id.label("pid")).distinct()
    active_union = union(submission_ids, vote_ids).subquery()
    return int(db.scalar(select(func.count()).select_from(active_union)) or 0)


def _total_submissions(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(QueueEntry)
            .where(QueueEntry.submitted_by_participant_id.isnot(None))
        )
        or 0
    )


def _total_votes_cast(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Vote)) or 0)


def _distinct_voted_songs_count(db: Session) -> int:
    voted_videos = (
        select(QueueEntry.youtube_video_id)
        .group_by(QueueEntry.youtube_video_id)
        .having(func.sum(QueueEntry.vote_count) > 0)
        .subquery()
    )
    return int(db.scalar(select(func.count()).select_from(voted_videos)) or 0)


def _top_submitters(db: Session) -> list[ParticipantRankingItem]:
    rows = db.execute(
        select(Participant, func.count().label("cnt"))
        .join(QueueEntry, QueueEntry.submitted_by_participant_id == Participant.id)
        .group_by(Participant.id)
        .order_by(func.count().desc(), Participant.display_name.asc())
        .limit(_TOP_LIMIT)
    ).all()
    return [
        ParticipantRankingItem(
            participant_id=participant.id,
            display_name=_participant_display_label(participant),
            count=int(cnt),
        )
        for participant, cnt in rows
    ]


def _top_voters(db: Session) -> list[ParticipantRankingItem]:
    rows = db.execute(
        select(Participant, func.count().label("cnt"))
        .join(Vote, Vote.participant_id == Participant.id)
        .group_by(Participant.id)
        .order_by(func.count().desc(), Participant.display_name.asc())
        .limit(_TOP_LIMIT)
    ).all()
    return [
        ParticipantRankingItem(
            participant_id=participant.id,
            display_name=_participant_display_label(participant),
            count=int(cnt),
        )
        for participant, cnt in rows
    ]


def _top_songs(db: Session) -> list[SongRankingItem]:
    rows = db.execute(
        select(
            QueueEntry.youtube_video_id,
            func.max(QueueEntry.title).label("title"),
            func.sum(QueueEntry.vote_count).label("vote_total"),
        )
        .group_by(QueueEntry.youtube_video_id)
        .having(func.sum(QueueEntry.vote_count) > 0)
        .order_by(func.sum(QueueEntry.vote_count).desc(), func.max(QueueEntry.title).asc())
        .limit(_TOP_LIMIT)
    ).all()
    return [
        SongRankingItem(
            youtube_video_id=video_id,
            title=title,
            vote_count=int(vote_total),
        )
        for video_id, title, vote_total in rows
    ]


def _queue_status_counts(db: Session) -> QueueStatusCounts:
    counts = {
        QueueEntryStatus.pending_review.value: 0,
        QueueEntryStatus.queued.value: 0,
        QueueEntryStatus.playing.value: 0,
        QueueEntryStatus.played.value: 0,
        QueueEntryStatus.rejected.value: 0,
    }
    for status, count in db.execute(
        select(QueueEntry.status, func.count()).group_by(QueueEntry.status)
    ).all():
        counts[status.value] = int(count)
    return QueueStatusCounts(
        pending_review=counts[QueueEntryStatus.pending_review.value],
        queued=counts[QueueEntryStatus.queued.value],
        playing=counts[QueueEntryStatus.playing.value],
        played=counts[QueueEntryStatus.played.value],
        rejected=counts[QueueEntryStatus.rejected.value],
    )


def build_admin_stats_response(db: Session) -> AdminStatsResponse:
    return AdminStatsResponse(
        participants_active_count=_count_active_participants(db),
        total_submissions=_total_submissions(db),
        total_votes_cast=_total_votes_cast(db),
        distinct_voted_songs_count=_distinct_voted_songs_count(db),
        queue_counts=_queue_status_counts(db),
        top_submitters=_top_submitters(db),
        top_voters=_top_voters(db),
        top_songs=_top_songs(db),
    )
