"""Business rules for chart-of-accounts accounts."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from app.domain.puc import AccountLevel, level_of, parent_code_of
from app.models.account import Account
from app.repositories.account import AccountRepository
from app.schemas.account import AccountCreate, AccountNode, AccountRead, AccountUpdate
from app.services.errors import (
    AccountAlreadyExists,
    AccountHasChildren,
    AccountNotDeleted,
    AccountNotFound,
    ParentAccountDeleted,
    ParentAccountMissing,
)


class AccountService:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def get(self, code: str, *, include_deleted: bool = False) -> Account:
        account = await self._repository.get(code, include_deleted=include_deleted)
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
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Account]:
        return await self._repository.find_many(
            level=level,
            parent_code=parent_code,
            search=search,
            only_active=only_active,
            include_deleted=include_deleted,
            skip=skip,
            limit=limit,
        )

    async def create(self, payload: AccountCreate) -> Account:
        """Create an account. Level and parent come from the code, not the client.

        A code that exists but was soft-deleted is revived with the new data:
        the row still occupies the primary key, and reusing it is what the
        caller means by "create this account again".
        """
        existing = await self._repository.get(payload.code, include_deleted=True)

        if existing is not None and not existing.is_deleted:
            raise AccountAlreadyExists(payload.code)

        parent_code = parent_code_of(payload.code)
        if parent_code is not None and not await self._repository.exists(parent_code):
            raise ParentAccountMissing(payload.code, parent_code)

        if existing is not None:
            existing.name = payload.name
            existing.nature = payload.nature
            existing.is_active = payload.is_active
            existing.deleted_at = None
            account = existing
        else:
            account = Account(
                code=payload.code,
                name=payload.name,
                nature=payload.nature,
                is_active=payload.is_active,
                level=level_of(payload.code),
                parent_code=parent_code,
            )
            self._repository.add(account)

        await self._repository.commit()
        await self._repository.refresh(account)
        return account

    async def update(self, code: str, payload: AccountUpdate) -> Account:
        account = await self.get(code)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(account, field, value)

        await self._repository.commit()
        await self._repository.refresh(account)
        return account

    async def delete(self, code: str) -> Account:
        """Soft-delete an account. Refused while live children hang off it."""
        account = await self.get(code)

        if await self._repository.has_children(code):
            raise AccountHasChildren(code)

        # Stored naive to match the other timestamp columns.
        account.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        await self._repository.commit()
        await self._repository.refresh(account)
        return account

    async def restore(self, code: str) -> Account:
        """Bring a soft-deleted account back, provided its parent is alive."""
        account = await self.get(code, include_deleted=True)

        if not account.is_deleted:
            raise AccountNotDeleted(code)

        if account.parent_code is not None and not await self._repository.exists(
            account.parent_code
        ):
            raise ParentAccountDeleted(code, account.parent_code)

        account.deleted_at = None
        await self._repository.commit()
        await self._repository.refresh(account)
        return account

    async def tree(self, *, include_deleted: bool = False) -> list[AccountNode]:
        """The whole chart of accounts as a tree.

        Built in memory from a single query: the chart is around 2,500 rows and
        recursing per level would multiply the round trips to the database.
        """
        accounts = await self._repository.list_all_ordered(
            include_deleted=include_deleted
        )
        # Going through AccountRead is deliberate: validating AccountNode against
        # the ORM object would make Pydantic read the `children` relationship,
        # triggering a lazy load that is illegal in async context.
        nodes = {
            account.code: AccountNode(
                **AccountRead.model_validate(account).model_dump()
            )
            for account in accounts
        }

        roots: list[AccountNode] = []
        for account in accounts:
            node = nodes[account.code]
            parent = nodes.get(account.parent_code) if account.parent_code else None
            # An account whose parent is not loaded is treated as a root, so the
            # tree never hides rows.
            if parent is None:
                roots.append(node)
            else:
                parent.children.append(node)

        return roots
