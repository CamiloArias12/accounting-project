"""Use cases that change accounts.

Each one is a small object holding its collaborators, so the web adapter only
knows how to build it and call it — never how the rule is enforced.
"""

from __future__ import annotations

from app.modules.accounts.application.ports import AccountRepository, Clock
from app.modules.accounts.application.queries import AccountChanges, NewAccount
from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.errors import (
    AccountAlreadyExists,
    AccountHasChildren,
    AccountNotDeleted,
    AccountNotFound,
    ParentAccountDeleted,
    ParentAccountMissing,
)
from app.modules.accounts.domain.puc import parent_code_of


class CreateAccount:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def __call__(self, request: NewAccount) -> Account:
        """Open an account. Level and parent come from the code, not the caller.

        A code that exists but was soft-deleted is revived with the new data:
        the row still occupies the primary key, and reusing it is what the
        caller means by "create this account again".
        """
        existing = await self._repository.get(request.code, include_deleted=True)

        if existing is not None and not existing.is_deleted:
            raise AccountAlreadyExists(request.code)

        account = Account.open(
            code=request.code,
            name=request.name,
            nature=request.nature,
            is_active=request.is_active,
        )

        if account.parent_code is not None and not await self._repository.exists(
            account.parent_code
        ):
            raise ParentAccountMissing(account.code, account.parent_code)

        if existing is None:
            return await self._repository.add(account)

        existing.rename(request.name)
        existing.change_nature(request.nature)
        existing.set_active(request.is_active)
        existing.restore()
        return await self._repository.save(existing)


class UpdateAccount:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def __call__(self, code: str, changes: AccountChanges) -> Account:
        account = await self._repository.get(code)
        if account is None:
            raise AccountNotFound(code)

        if changes.name is not None:
            account.rename(changes.name)
        if changes.nature is not None:
            account.change_nature(changes.nature)
        if changes.is_active is not None:
            account.set_active(changes.is_active)

        return await self._repository.save(account)


class DeleteAccount:
    def __init__(self, repository: AccountRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def __call__(self, code: str) -> Account:
        """Soft-delete an account. Refused while live children hang off it."""
        account = await self._repository.get(code)
        if account is None:
            raise AccountNotFound(code)

        if await self._repository.has_children(code):
            raise AccountHasChildren(code)

        account.delete(self._clock.now())
        return await self._repository.save(account)


class RestoreAccount:
    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    async def __call__(self, code: str) -> Account:
        """Bring a soft-deleted account back, provided its parent is alive."""
        account = await self._repository.get(code, include_deleted=True)
        if account is None:
            raise AccountNotFound(code)

        if not account.is_deleted:
            raise AccountNotDeleted(code)

        parent_code = parent_code_of(account.code)
        if parent_code is not None and not await self._repository.exists(parent_code):
            raise ParentAccountDeleted(account.code, parent_code)

        account.restore()
        return await self._repository.save(account)
