"""replace accounts with the PUC hierarchy

The previous `accounts` table was scaffolding (autoincrement id, flat
code/name/type) and never reached production, so it is recreated rather than
migrated column by column: the new model moves the primary key to `code` and
adds the self-referencing hierarchy.

Revision ID: b380327a2da0
Revises: baf178afffce
Create Date: 2026-07-25 05:51:57.223685

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b380327a2da0"
down_revision: str | None = "baf178afffce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NATURE = sa.Enum(
    "DEBIT", "CREDIT", name="account_nature", native_enum=False, length=20
)
_LEVEL = sa.Enum(
    "CLASS",
    "GROUP",
    "ACCOUNT",
    "SUBACCOUNT",
    "AUXILIARY",
    name="account_level",
    native_enum=False,
    length=20,
)
_OLD_TYPE = sa.Enum(
    "ASSET",
    "LIABILITY",
    "EQUITY",
    "REVENUE",
    "EXPENSE",
    name="account_type",
    native_enum=False,
)


def upgrade() -> None:
    op.drop_table("accounts")
    op.create_table(
        "accounts",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("nature", _NATURE, nullable=False),
        sa.Column("level", _LEVEL, nullable=False),
        sa.Column("parent_code", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("code"),
        sa.ForeignKeyConstraint(
            ["parent_code"],
            ["accounts.code"],
            name="fk_accounts_parent_code",
            onupdate="CASCADE",
            # RESTRICT: deleting a parent that still has children fails in
            # the database, even if the service check were bypassed.
            ondelete="RESTRICT",
        ),
    )
    op.create_index(op.f("ix_accounts_level"), "accounts", ["level"])
    op.create_index(op.f("ix_accounts_parent_code"), "accounts", ["parent_code"])


def downgrade() -> None:
    op.drop_index(op.f("ix_accounts_parent_code"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_level"), table_name="accounts")
    op.drop_table("accounts")

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", _OLD_TYPE, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_code"), "accounts", ["code"], unique=True)
