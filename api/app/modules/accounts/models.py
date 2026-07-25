"""The account table, which is also the object the service works with.

No separate domain entity: for a chart of accounts the SQLAlchemy model carries
the data and the handful of rules that do not need I/O, and a mapper between two
near-identical shapes would be ceremony with nothing to show for it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.accounts.puc import (
    MAX_CODE_LENGTH,
    AccountLevel,
    Nature,
    level_of,
    parent_code_of,
    validate_code,
)
from app.shared.database import Base, TimestampMixin


class Account(Base, TimestampMixin):
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

    #: Whether the account may be posted to. Unrelated to whether it exists.
    is_active: Mapped[bool] = mapped_column(default=True)

    #: Soft delete marker. Rows are never removed: accounting records must stay
    #: auditable, and a deleted code must not be reused by a different account.
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)

    parent: Mapped[Account | None] = relationship(
        back_populates="children", remote_side=[code]
    )
    children: Mapped[list[Account]] = relationship(
        back_populates="parent", order_by="Account.code"
    )

    @classmethod
    def open(
        cls, *, code: str, name: str, nature: Nature, is_active: bool = True
    ) -> Account:
        """Build an account, deriving level and parent from its code."""
        normalized = validate_code(code)
        return cls(
            code=normalized,
            name=name,
            nature=nature,
            is_active=is_active,
            level=level_of(normalized),
            parent_code=parent_code_of(normalized),
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        # Naive, to match the other timestamp columns.
        self.deleted_at = datetime.now(UTC).replace(tzinfo=None)

    def restore(self) -> None:
        self.deleted_at = None

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"
