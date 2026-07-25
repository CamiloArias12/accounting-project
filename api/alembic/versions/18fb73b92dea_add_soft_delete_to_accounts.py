"""add soft delete to accounts

Nullable column, so it applies to an already populated table: every existing
row is simply not deleted.

Revision ID: 18fb73b92dea
Revises: b380327a2da0
Create Date: 2026-07-25 06:25:24.743544

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "18fb73b92dea"
down_revision: str | None = "b380327a2da0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_accounts_deleted_at"), "accounts", ["deleted_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_accounts_deleted_at"), table_name="accounts")
    op.drop_column("accounts", "deleted_at")
