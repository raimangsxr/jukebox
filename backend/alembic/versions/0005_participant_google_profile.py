"""participant google profile columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("participants", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("participants", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("participants", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.create_index(
        "ix_participants_google_sub",
        "participants",
        ["google_sub"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_participants_google_sub", table_name="participants")
    op.drop_column("participants", "avatar_url")
    op.drop_column("participants", "email")
    op.drop_column("participants", "google_sub")
