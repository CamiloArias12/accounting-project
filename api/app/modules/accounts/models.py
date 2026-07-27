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
    """The account table, which is also the object the service works with."""
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
        ForeignKey("accounts.code", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
        default=None,
    )

    is_active: Mapped[bool] = mapped_column(default=True)

    dian_concept: Mapped[str | None] = mapped_column(String(10), default=None)

    is_withholding: Mapped[bool] = mapped_column(default=False)

    requires_third_party: Mapped[bool] = mapped_column(default=False)

    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)

    parent: Mapped[Account | None] = relationship(
        back_populates="children", remote_side=[code]
    )
    children: Mapped[list[Account]] = relationship(
        back_populates="parent", order_by="Account.code"
    )

    @classmethod
    def open(
        cls,
        *,
        code: str,
        name: str,
        nature: Nature,
        is_active: bool = True,
        requires_third_party: bool = False,
        dian_concept: str | None = None,
        is_withholding: bool = False,
    ) -> Account:
        normalized = validate_code(code)
        return cls(
            code=normalized,
            name=name,
            nature=nature,
            is_active=is_active,
            requires_third_party=requires_third_party,
            dian_concept=(dian_concept or "").strip() or None,
            is_withholding=is_withholding,
            level=level_of(normalized),
            parent_code=parent_code_of(normalized),
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        self.deleted_at = datetime.now(UTC).replace(tzinfo=None)

    def restore(self) -> None:
        self.deleted_at = None

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"
