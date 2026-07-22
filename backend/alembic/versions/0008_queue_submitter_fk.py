"""queue_entries.submitted_by_participant_id -> participants FK

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-22

"""

from typing import Sequence, Union

from alembic import op


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Null orphan references before adding the constraint so the FK can be
    # created cleanly (010-hardening-and-polish, FR-012).
    op.execute(
        """
        UPDATE queue_entries
        SET submitted_by_participant_id = NULL
        WHERE submitted_by_participant_id IS NOT NULL
          AND submitted_by_participant_id NOT IN (SELECT id FROM participants)
        """
    )
    with op.batch_alter_table("queue_entries") as batch:
        batch.create_index(
            "ix_queue_entries_submitted_by_participant_id",
            ["submitted_by_participant_id"],
        )
        batch.create_foreign_key(
            "fk_queue_entries_submitter_participant",
            "participants",
            ["submitted_by_participant_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("queue_entries") as batch:
        batch.drop_constraint(
            "fk_queue_entries_submitter_participant", type_="foreignkey"
        )
        batch.drop_index("ix_queue_entries_submitted_by_participant_id")
