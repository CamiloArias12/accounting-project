"""Use cases that only read accounts."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.accounts.application.ports import AccountRepository
from app.modules.accounts.application.queries import AccountFilters, TreeQuery
from app.modules.accounts.domain.account import Account, AccountNode
from app.modules.accounts.domain.errors import AccountNotFound
from app.modules.accounts.domain.puc import depth_of, parent_code_of


class GetAccount:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def __call__(self, code: str, *, include_deleted: bool = False) -> Account:
        account = await self._repository.get(code, include_deleted=include_deleted)
        if account is None:
            raise AccountNotFound(code)
        return account


class ListAccounts:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def __call__(self, filters: AccountFilters) -> Sequence[Account]:
        return await self._repository.find_many(filters)


class GetAccountTree:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def __call__(self, query: TreeQuery) -> list[AccountNode]:
        """Build the requested slice of the chart as a tree.

        Assembled in memory from one query: the chart runs to thousands of rows
        and recursing per level would multiply the round trips.
        """
        accounts = await self._repository.list_subtree(
            query.root_code, include_deleted=query.include_deleted
        )
        return self._assemble(accounts, query)

    def _assemble(
        self, accounts: Sequence[Account], query: TreeQuery
    ) -> list[AccountNode]:
        base_depth = depth_of(query.root_code) if query.root_code else 0
        nodes = {account.code: AccountNode(account=account) for account in accounts}
        roots: list[AccountNode] = []

        for account in accounts:
            if self._is_too_deep(account.code, base_depth, query.max_depth):
                continue

            node = nodes[account.code]
            parent_code = parent_code_of(account.code)
            parent = nodes.get(parent_code) if parent_code else None

            # An account whose parent is outside the requested slice becomes a
            # root, so the result never silently hides rows.
            if parent is None or account.code == query.root_code:
                roots.append(node)
            else:
                parent.children.append(node)

        return roots

    @staticmethod
    def _is_too_deep(code: str, base_depth: int, max_depth: int | None) -> bool:
        return max_depth is not None and depth_of(code) - base_depth > max_depth
