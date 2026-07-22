"""queue_entries.submitted_by_participant_id FK integrity (010, FR-012)."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Participant, QueueEntry, QueueEntryStatus


def _fk_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):  # pragma: no cover - trivial
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def _entry(participant_id):
    return QueueEntry(
        id="entry-1",
        youtube_video_id="12345678901",
        title="Song",
        status=QueueEntryStatus.pending_review,
        original_query="q",
        submitted_by_participant_id=participant_id,
    )


def test_orphan_submitter_is_rejected():
    engine = _fk_engine()
    with Session(engine) as session:
        session.add(_entry("does-not-exist"))
        with pytest.raises(IntegrityError):
            session.commit()
    engine.dispose()


def test_valid_submitter_is_accepted():
    engine = _fk_engine()
    with Session(engine) as session:
        participant = Participant(id="p-1", display_name="Alice")
        session.add(participant)
        session.commit()
        session.add(_entry("p-1"))
        session.commit()
        assert session.get(QueueEntry, "entry-1").submitted_by_participant_id == "p-1"
    engine.dispose()
