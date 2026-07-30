"""event_config.queue_mode for moderated vs free submit flow

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_config",
        sa.Column(
            "queue_mode",
            sa.String(length=16),
            nullable=False,
            server_default="moderated",
        ),
    )


def downgrade() -> None:
    op.drop_column("event_config", "queue_mode")
