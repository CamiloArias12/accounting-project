"""Data access for accounts. No business rules: those live in `services/`.

Every read hides soft-deleted rows unless `include_deleted` is set, so callers
cannot forget the filter and leak deleted accounts.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.puc import AccountLevel
from app.models.account import Account


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, code: str, *, include_deleted: bool = False) -> Account | None:
        query = self._base(include_deleted=include_deleted).where(Account.code == code)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def exists(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self.get(code, include_deleted=include_deleted) is not None

    async def existing_codes(
        self, codes: Iterable[str], *, include_deleted: bool = False
    ) -> set[str]:
        """Which of these codes are already stored, in one round trip."""
        wanted = list(codes)
        if not wanted:
            return set()

        query = select(Account.code).where(Account.code.in_(wanted))
        if not include_deleted:
            query = query.where(Account.deleted_at.is_(None))

        result = await self._session.execute(query)
        return set(result.scalars().all())

    async def find_many(
        self,
        *,
        level: AccountLevel | None = None,
        parent_code: str | None = None,
        search: str | None = None,
        only_active: bool | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Account]:
        query = self._base(include_deleted=include_deleted)

        if level is not None:
            query = query.where(Account.level == level)
        if parent_code is not None:
            query = query.where(Account.parent_code == parent_code)
        if only_active is not None:
            query = query.where(Account.is_active.is_(only_active))
        if search:
            pattern = f"%{search}%"
            query = query.where(
                Account.name.ilike(pattern) | Account.code.like(pattern)
            )

        query = query.order_by(Account.code).offset(skip).limit(limit)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def list_all_ordered(
        self, *, include_deleted: bool = False
    ) -> Sequence[Account]:
        """Every account by code; the tree is assembled in memory from this."""
        query = self._base(include_deleted=include_deleted).order_by(Account.code)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def count_children(self, code: str, *, include_deleted: bool = False) -> int:
        query = (
            select(func.count()).select_from(Account).where(Account.parent_code == code)
        )
        if not include_deleted:
            query = query.where(Account.deleted_at.is_(None))

        result = await self._session.execute(query)
        return result.scalar_one()

    async def has_children(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self.count_children(code, include_deleted=include_deleted) > 0

    def add(self, account: Account) -> None:
        self._session.add(account)

    def add_all(self, accounts: Iterable[Account]) -> None:
        self._session.add_all(list(accounts))

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, account: Account) -> None:
        await self._session.refresh(account)

    @staticmethod
    def _base(*, include_deleted: bool) -> Select[tuple[Account]]:
        query = select(Account)
        return query if include_deleted else query.where(Account.deleted_at.is_(None))
