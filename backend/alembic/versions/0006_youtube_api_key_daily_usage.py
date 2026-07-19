"""youtube api key daily usage

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "youtube_api_key_daily_usage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("quota_day", sa.Date(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exhausted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", "quota_day", name="uq_youtube_api_key_daily_usage_key_day"),
    )
    op.create_index(
        "ix_youtube_api_key_daily_usage_quota_day",
        "youtube_api_key_daily_usage",
        ["quota_day"],
    )


def downgrade() -> None:
    op.drop_index("ix_youtube_api_key_daily_usage_quota_day", table_name="youtube_api_key_daily_usage")
    op.drop_table("youtube_api_key_daily_usage")
