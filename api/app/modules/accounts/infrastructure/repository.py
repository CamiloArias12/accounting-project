"""SQLAlchemy adapter for `AccountRepository`.

Every read hides soft-deleted rows unless asked otherwise, so no caller can
forget the filter and leak deleted accounts.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.application.queries import AccountFilters
from app.modules.accounts.domain.account import Account
from app.modules.accounts.infrastructure.orm import (
    AccountRow,
    apply_to_row,
    to_entity,
    to_row,
)

#: Bounds the parameter count of `IN (...)` lookups.
_CHUNK = 500


class SqlAlchemyAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, code: str, *, include_deleted: bool = False) -> Account | None:
        row = await self._row(code, include_deleted=include_deleted)
        return to_entity(row) if row is not None else None

    async def exists(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self._row(code, include_deleted=include_deleted) is not None

    async def existing_codes(
        self, codes: Iterable[str], *, include_deleted: bool = False
    ) -> set[str]:
        wanted = list(codes)
        found: set[str] = set()

        # Chunked: a single IN() with thousands of parameters is what makes a
        # large import fall over.
        for start in range(0, len(wanted), _CHUNK):
            chunk = wanted[start : start + _CHUNK]
            query = select(AccountRow.code).where(AccountRow.code.in_(chunk))
            if not include_deleted:
                query = query.where(AccountRow.deleted_at.is_(None))
            result = await self._session.execute(query)
            found.update(result.scalars().all())

        return found

    async def find_many(self, filters: AccountFilters) -> Sequence[Account]:
        query = self._base(include_deleted=filters.include_deleted)

        if filters.level is not None:
            query = query.where(AccountRow.level == filters.level)
        if filters.parent_code is not None:
            query = query.where(AccountRow.parent_code == filters.parent_code)
        if filters.only_active is not None:
            query = query.where(AccountRow.is_active.is_(filters.only_active))
        if filters.search:
            pattern = f"%{filters.search}%"
            query = query.where(
                AccountRow.name.ilike(pattern) | AccountRow.code.like(pattern)
            )

        query = (
            query.order_by(AccountRow.code).offset(filters.skip).limit(filters.limit)
        )
        result = await self._session.execute(query)
        return [to_entity(row) for row in result.scalars().all()]

    async def list_subtree(
        self, root_code: str | None, *, include_deleted: bool = False
    ) -> Sequence[Account]:
        query = self._base(include_deleted=include_deleted)

        # Descendants share the root's code as a prefix, which the primary key
        # index serves directly.
        if root_code is not None:
            query = query.where(AccountRow.code.startswith(root_code))

        query = query.order_by(AccountRow.code)
        result = await self._session.execute(query)
        return [to_entity(row) for row in result.scalars().all()]

    async def has_children(self, code: str, *, include_deleted: bool = False) -> bool:
        query = (
            select(func.count())
            .select_from(AccountRow)
            .where(AccountRow.parent_code == code)
        )
        if not include_deleted:
            query = query.where(AccountRow.deleted_at.is_(None))

        result = await self._session.execute(query)
        return result.scalar_one() > 0

    async def add(self, account: Account) -> Account:
        row = to_row(account)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return to_entity(row)

    async def add_many(self, accounts: Sequence[Account]) -> int:
        if not accounts:
            return 0

        self._session.add_all([to_row(account) for account in accounts])
        await self._session.commit()
        return len(accounts)

    async def save(self, account: Account) -> Account:
        row = await self._row(account.code, include_deleted=True)
        if row is None:
            raise LookupError(f"Account {account.code} vanished before saving")

        apply_to_row(row, account)
        await self._session.commit()
        await self._session.refresh(row)
        return to_entity(row)

    async def _row(self, code: str, *, include_deleted: bool) -> AccountRow | None:
        query = self._base(include_deleted=include_deleted).where(
            AccountRow.code == code
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _base(*, include_deleted: bool) -> Select[tuple[AccountRow]]:
        query = select(AccountRow)
        return (
            query if include_deleted else query.where(AccountRow.deleted_at.is_(None))
        )
