"""queue history, filler reserve, priority and source columns

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "queue_entries",
        sa.Column(
            "priority",
            sa.String(length=16),
            nullable=False,
            server_default="normal",
        ),
    )
    op.add_column(
        "queue_entries",
        sa.Column(
            "source",
            sa.String(length=24),
            nullable=False,
            server_default="participant",
        ),
    )
    op.add_column(
        "queue_entries",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_queue_entries_status_finished_at",
        "queue_entries",
        ["status", "finished_at"],
    )
    op.execute(
        """
        UPDATE queue_entries
        SET finished_at = created_at
        WHERE status IN ('played', 'rejected') AND finished_at IS NULL
        """
    )

    op.create_table(
        "filler_reserve_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("youtube_video_id", sa.String(length=11), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("original_query", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("youtube_video_id", name="uq_filler_reserve_video"),
    )
    op.create_index(
        "ix_filler_reserve_entries_position",
        "filler_reserve_entries",
        ["position"],
    )

    op.add_column(
        "event_config",
        sa.Column(
            "filler_auto_inject_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("event_config", "filler_auto_inject_enabled")
    op.drop_index("ix_filler_reserve_entries_position", table_name="filler_reserve_entries")
    op.drop_table("filler_reserve_entries")
    op.drop_index("ix_queue_entries_status_finished_at", table_name="queue_entries")
    op.drop_column("queue_entries", "finished_at")
    op.drop_column("queue_entries", "source")
    op.drop_column("queue_entries", "priority")
