"""Business rules for the chart of accounts.

The service owns the session and therefore the transaction: it decides what a
unit of work is, and commits once. Queries live here too — a repository layer
over a single table would only forward calls.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.accounts.cache import AccountTreeCache
from app.modules.accounts.errors import (
    AccountAlreadyExists,
    AccountHasChildren,
    AccountNotDeleted,
    AccountNotFound,
    ParentAccountDeleted,
    ParentAccountMissing,
)
from app.modules.accounts.models import Account
from app.modules.accounts.puc import (
    AccountLevel,
    code_lengths_up_to,
    depth_of,
    parent_code_of,
)
from app.modules.accounts.schemas import (
    AccountCreate,
    AccountNode,
    AccountRead,
    AccountUpdate,
)


class AccountService:
    def __init__(self, session: AsyncSession, cache: AccountTreeCache) -> None:
        self._session = session
        self._cache = cache

    # --- reads ------------------------------------------------------------

    async def get(self, code: str, *, include_deleted: bool = False) -> Account:
        account = await self._find(code, include_deleted=include_deleted)
        if account is None:
            raise AccountNotFound(code)
        return account

    async def find_many(
        self,
        *,
        level: AccountLevel | None = None,
        parent_code: str | None = None,
        search: str | None = None,
        only_active: bool | None = None,
        only_postable: bool = False,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Account]:
        query = self._visible(include_deleted)

        if level is not None:
            query = query.where(Account.level == level)
        if parent_code is not None:
            query = query.where(Account.parent_code == parent_code)
        if only_postable:
            # Leaves, whatever their level: a six-digit subaccount with nothing
            # under it takes entries, and a heading never does because its
            # balance is already the sum of its children.
            child = aliased(Account)
            query = query.where(
                ~select(child.code)
                .where(child.parent_code == Account.code, child.deleted_at.is_(None))
                .exists()
            )
        if only_active is not None:
            query = query.where(Account.is_active.is_(only_active))
        if search:
            pattern = f"%{search}%"
            query = query.where(
                Account.name.ilike(pattern) | Account.code.like(pattern)
            )

        result = await self._session.execute(
            query.order_by(Account.code).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def tree(
        self,
        *,
        root_code: str | None = None,
        max_depth: int | None = None,
        include_deleted: bool = False,
    ) -> list[AccountNode]:
        """The chart, or one branch of it, nested.

        Served from cache when possible, and assembled in memory from a single
        query: recursing per level would multiply the round trips.
        """
        cached = await self._cache.get(root_code, max_depth, include_deleted)
        if cached is not None:
            return cached

        rows = await self._subtree_rows(root_code, max_depth, include_deleted)
        nodes = _assemble(rows, root_code)
        await self._cache.set(root_code, max_depth, include_deleted, nodes)
        return nodes

    async def _subtree_rows(
        self, root_code: str | None, max_depth: int | None, include_deleted: bool
    ) -> Sequence[Account]:
        query = self._visible(include_deleted)

        # Descendants share the root's code as a prefix, which the primary key
        # index serves directly.
        if root_code is not None:
            query = query.where(Account.code.startswith(root_code))

        # Bounded in SQL, not after loading: asking for the classes of a
        # 2,446-row chart should not read 2,446 rows.
        if max_depth is not None:
            base = depth_of(root_code) if root_code else 0
            query = query.where(
                func.length(Account.code).in_(code_lengths_up_to(base + max_depth))
            )

        result = await self._session.execute(query.order_by(Account.code))
        return result.scalars().all()

    # --- writes -----------------------------------------------------------

    async def create(self, payload: AccountCreate) -> Account:
        """Create an account.

        A code that exists but was soft-deleted is revived with the new data:
        the row still occupies the primary key, and reusing it is what the
        caller means by "create this account again".
        """
        existing = await self._find(payload.code, include_deleted=True)
        if existing is not None and not existing.is_deleted:
            raise AccountAlreadyExists(payload.code)

        parent_code = parent_code_of(payload.code)
        if parent_code is not None and not await self._exists(parent_code):
            raise ParentAccountMissing(payload.code, parent_code)

        if existing is None:
            account = Account.open(
                code=payload.code,
                name=payload.name,
                nature=payload.nature,
                is_active=payload.is_active,
                requires_third_party=payload.requires_third_party,
            )
            self._session.add(account)
        else:
            account = existing
            account.name = payload.name
            account.nature = payload.nature
            account.is_active = payload.is_active
            account.requires_third_party = payload.requires_third_party
            account.restore()

        return await self._commit(account)

    async def update(self, code: str, payload: AccountUpdate) -> Account:
        account = await self.get(code)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(account, field, value)

        return await self._commit(account)

    async def delete(self, code: str) -> Account:
        """Soft delete. Refused while live children hang off the account."""
        account = await self.get(code)

        if await self._has_children(code):
            raise AccountHasChildren(code)

        account.mark_deleted()
        return await self._commit(account)

    async def restore(self, code: str) -> Account:
        account = await self.get(code, include_deleted=True)

        if not account.is_deleted:
            raise AccountNotDeleted(code)

        parent_code = parent_code_of(account.code)
        if parent_code is not None and not await self._exists(parent_code):
            raise ParentAccountDeleted(account.code, parent_code)

        account.restore()
        return await self._commit(account)

    # --- plumbing ---------------------------------------------------------

    async def _commit(self, account: Account) -> Account:
        await self._session.commit()
        await self._session.refresh(account)
        await self._cache.clear()
        return account

    async def _find(self, code: str, *, include_deleted: bool) -> Account | None:
        result = await self._session.execute(
            self._visible(include_deleted).where(Account.code == code)
        )
        return result.scalar_one_or_none()

    async def _exists(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self._find(code, include_deleted=include_deleted) is not None

    async def _has_children(self, code: str) -> bool:
        result = await self._session.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.parent_code == code, Account.deleted_at.is_(None))
        )
        return result.scalar_one() > 0

    @staticmethod
    def _visible(include_deleted: bool) -> Select[tuple[Account]]:
        query = select(Account)
        return query if include_deleted else query.where(Account.deleted_at.is_(None))


def _assemble(rows: Sequence[Account], root_code: str | None) -> list[AccountNode]:
    # Built through AccountRead on purpose: validating AccountNode against the
    # model would make Pydantic read the `children` relationship, triggering a
    # lazy load that is illegal in async context.
    nodes = {
        row.code: AccountNode(**AccountRead.model_validate(row).model_dump())
        for row in rows
    }
    roots: list[AccountNode] = []

    for row in rows:
        parent_code = parent_code_of(row.code)
        parent = nodes.get(parent_code) if parent_code else None

        # An account whose parent is outside the requested slice becomes a root,
        # so the result never silently hides rows.
        if parent is None or row.code == root_code:
            roots.append(nodes[row.code])
        else:
            parent.children.append(nodes[row.code])

    return roots
