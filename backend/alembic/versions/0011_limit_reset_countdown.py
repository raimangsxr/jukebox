"""participant quota reset columns and participant_searches

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participants",
        sa.Column("votes_quota_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("searches_quota_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "participant_searches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("participant_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["participants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_participant_searches_participant_id",
        "participant_searches",
        ["participant_id"],
    )
    op.create_index(
        "ix_participant_searches_participant_id_created_at",
        "participant_searches",
        ["participant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_participant_searches_participant_id_created_at",
        table_name="participant_searches",
    )
    op.drop_index(
        "ix_participant_searches_participant_id",
        table_name="participant_searches",
    )
    op.drop_table("participant_searches")
    op.drop_column("participants", "searches_quota_reset_at")
    op.drop_column("participants", "votes_quota_reset_at")
