"""Persistence model and its mapping to the domain entity.

The row and the entity are kept apart on purpose: the table can grow indexes,
denormalised columns or a different key strategy without any of it leaking into
the business rules. The price is this mapper, which is the honest cost of the
separation.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.puc import MAX_CODE_LENGTH, AccountLevel, Nature
from app.shared.database import Base, TimestampMixin


class AccountRow(Base, TimestampMixin):
    __tablename__ = "accounts"

    code: Mapped[str] = mapped_column(String(MAX_CODE_LENGTH), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    nature: Mapped[Nature] = mapped_column(
        Enum(Nature, name="account_nature", native_enum=False, length=20)
    )
    level: Mapped[AccountLevel] = mapped_column(
        Enum(AccountLevel, name="account_level", native_enum=False, length=20),
        index=True,
    )
    parent_code: Mapped[str | None] = mapped_column(
        String(MAX_CODE_LENGTH),
        # RESTRICT: deleting a parent that still has children must fail in the
        # database too, even if the service check were bypassed.
        ForeignKey("accounts.code", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
        default=None,
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)

    def __repr__(self) -> str:
        return f"<AccountRow {self.code} {self.name}>"


def to_entity(row: AccountRow) -> Account:
    return Account(
        code=row.code,
        name=row.name,
        nature=row.nature,
        level=row.level,
        parent_code=row.parent_code,
        is_active=row.is_active,
        deleted_at=row.deleted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def to_row(account: Account) -> AccountRow:
    return AccountRow(
        code=account.code,
        name=account.name,
        nature=account.nature,
        level=account.level,
        parent_code=account.parent_code,
        is_active=account.is_active,
        deleted_at=account.deleted_at,
    )


def apply_to_row(row: AccountRow, account: Account) -> None:
    """Copies the mutable fields back. The code and level never change."""
    row.name = account.name
    row.nature = account.nature
    row.is_active = account.is_active
    row.deleted_at = account.deleted_at
