from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.puc import MAX_CODE_LENGTH, AccountLevel, Nature


class Account(Base, TimestampMixin):
    """An account of the chart of accounts.

    A single self-referencing table covers all five levels: the hierarchy is
    already encoded in the accounting code itself, so a table per level would
    only duplicate columns and relationships.
    """

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

    #: Whether the account may be used for posting. A business flag, unrelated
    #: to whether the account exists.
    is_active: Mapped[bool] = mapped_column(default=True)

    #: Soft delete marker. Rows are never removed: accounting records must stay
    #: auditable, and a deleted code cannot be silently reused by a new account.
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)

    parent: Mapped[Account | None] = relationship(
        back_populates="children",
        remote_side=[code],
    )
    children: Mapped[list[Account]] = relationship(
        back_populates="parent",
        order_by="Account.code",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"
