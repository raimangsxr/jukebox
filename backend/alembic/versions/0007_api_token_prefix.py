"""api token lookup prefix

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-22

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Non-secret indexed lookup prefix. Existing rows keep NULL and therefore
    # stop validating on token exchange; operators regenerate those tokens once
    # (documented in deploy/k8s/README.md).
    with op.batch_alter_table("api_tokens") as batch:
        batch.add_column(sa.Column("token_prefix", sa.String(length=16), nullable=True))
    op.create_index("ix_api_tokens_token_prefix", "api_tokens", ["token_prefix"])


def downgrade() -> None:
    op.drop_index("ix_api_tokens_token_prefix", table_name="api_tokens")
    with op.batch_alter_table("api_tokens") as batch:
        batch.drop_column("token_prefix")
