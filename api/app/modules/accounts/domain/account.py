"""The Account entity.

A plain dataclass, deliberately free of SQLAlchemy. The ORM row is a detail of
the persistence adapter; keeping the entity independent is what lets the use
cases be tested without a database and lets the storage change without
rewriting business rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.modules.accounts.domain.puc import (
    AccountLevel,
    Nature,
    level_of,
    parent_code_of,
    validate_code,
)


@dataclass(slots=True)
class Account:
    code: str
    name: str
    nature: Nature
    level: AccountLevel
    parent_code: str | None
    is_active: bool = True
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def open(
        cls,
        *,
        code: str,
        name: str,
        nature: Nature,
        is_active: bool = True,
    ) -> Account:
        """Build a new account, deriving level and parent from the code.

        Named `open` rather than `create` because persisting is someone else's
        job: this only produces a valid entity.
        """
        normalized = validate_code(code)
        return cls(
            code=normalized,
            name=name,
            nature=nature,
            level=level_of(normalized),
            parent_code=parent_code_of(normalized),
            is_active=is_active,
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def rename(self, name: str) -> None:
        self.name = name

    def change_nature(self, nature: Nature) -> None:
        self.nature = nature

    def set_active(self, is_active: bool) -> None:
        self.is_active = is_active

    def delete(self, at: datetime) -> None:
        self.deleted_at = at

    def restore(self) -> None:
        self.deleted_at = None


@dataclass(slots=True)
class AccountNode:
    """An account together with its descendants."""

    account: Account
    children: list[AccountNode] = field(default_factory=list)
