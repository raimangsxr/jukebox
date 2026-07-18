"""queue_entries and jukebox_runtime tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

queue_entry_status = sa.Enum(
    "pending_review",
    "rejected",
    "queued",
    "playing",
    "played",
    name="queue_entry_status",
    native_enum=False,
)


def _drop_orphan_native_enum_if_needed(connection: sa.Connection) -> None:
    """Drop legacy PG enum from earlier 0003 revisions when upgrade failed mid-flight."""
    inspector = sa.inspect(connection)
    if inspector.has_table("queue_entries"):
        return
    connection.execute(sa.text("DROP TYPE IF EXISTS queue_entry_status"))


def upgrade() -> None:
    bind = op.get_bind()
    _drop_orphan_native_enum_if_needed(bind)
    op.create_table(
        "queue_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=11), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("submitted_by_participant_id", sa.String(length=36), nullable=True),
        sa.Column("vote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("status", queue_entry_status, nullable=False),
        sa.Column("rejection_reason", sa.String(length=200), nullable=True),
        sa.Column("original_query", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_queue_entries_status"), "queue_entries", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_queue_entries_youtube_video_id"),
        "queue_entries",
        ["youtube_video_id"],
        unique=False,
    )
    op.create_table(
        "jukebox_runtime",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("now_playing_entry_id", sa.String(length=36), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["now_playing_entry_id"], ["queue_entries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("jukebox_runtime")
    op.drop_index(op.f("ix_queue_entries_youtube_video_id"), table_name="queue_entries")
    op.drop_index(op.f("ix_queue_entries_status"), table_name="queue_entries")
    op.drop_table("queue_entries")
