"""In-memory stand-ins for the ports.

They exist because the use cases depend on abstractions: a test can drive real
business rules without Postgres, Redis or a spreadsheet library.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import IO, Any

from app.modules.accounts.application.queries import AccountFilters
from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.puc import parent_code_of


class FakeRedis:
    """Enough of the Redis surface for the cache decorator."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.set_calls = 0
        self.get_calls = 0

    async def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.set_calls += 1
        self.store[key] = value

    async def delete(self, *keys: str) -> int:
        for key in keys:
            self.store.pop(key, None)
        return len(keys)

    async def scan_iter(self, match: str) -> AsyncIterator[str]:
        prefix = match.rstrip("*")
        for key in list(self.store):
            if key.startswith(prefix):
                yield key

    async def ping(self) -> bool:
        return True


class BrokenRedis(FakeRedis):
    """Fails on every call, to prove the cache never takes a request down."""

    async def get(self, key: str) -> str | None:
        raise ConnectionError("redis is down")

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        raise ConnectionError("redis is down")

    async def scan_iter(self, match: str) -> AsyncIterator[str]:
        raise ConnectionError("redis is down")
        yield ""  # pragma: no cover - unreachable, keeps this an async generator


class InMemoryAccountRepository:
    """Implements the AccountRepository port with a dict."""

    def __init__(self, accounts: Iterable[Account] = ()) -> None:
        self.accounts: dict[str, Account] = {a.code: a for a in accounts}
        self.subtree_calls = 0

    async def get(self, code: str, *, include_deleted: bool = False) -> Account | None:
        account = self.accounts.get(code)
        if account is None:
            return None
        return account if include_deleted or not account.is_deleted else None

    async def exists(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self.get(code, include_deleted=include_deleted) is not None

    async def existing_codes(
        self, codes: Iterable[str], *, include_deleted: bool = False
    ) -> set[str]:
        found = set()
        for code in codes:
            if await self.exists(code, include_deleted=include_deleted):
                found.add(code)
        return found

    async def find_many(self, filters: AccountFilters) -> Sequence[Account]:
        live = [
            a
            for a in self.accounts.values()
            if filters.include_deleted or not a.is_deleted
        ]
        if filters.level is not None:
            live = [a for a in live if a.level == filters.level]
        if filters.parent_code is not None:
            live = [a for a in live if a.parent_code == filters.parent_code]
        live.sort(key=lambda a: a.code)
        return live[filters.skip : filters.skip + filters.limit]

    async def list_subtree(
        self, root_code: str | None, *, include_deleted: bool = False
    ) -> Sequence[Account]:
        self.subtree_calls += 1
        found = [
            a
            for a in self.accounts.values()
            if (include_deleted or not a.is_deleted)
            and (root_code is None or a.code.startswith(root_code))
        ]
        return sorted(found, key=lambda a: a.code)

    async def has_children(self, code: str, *, include_deleted: bool = False) -> bool:
        return any(
            parent_code_of(a.code) == code and (include_deleted or not a.is_deleted)
            for a in self.accounts.values()
        )

    async def add(self, account: Account) -> Account:
        self.accounts[account.code] = account
        return account

    async def add_many(self, accounts: Sequence[Account]) -> int:
        for account in accounts:
            self.accounts[account.code] = account
        return len(accounts)

    async def save(self, account: Account) -> Account:
        self.accounts[account.code] = account
        return account


@dataclass(frozen=True, slots=True)
class FakeRow:
    number: int
    values: tuple[object, object, object, object]


class ListSpreadsheetReader:
    """Feeds the import use case from tuples, with no workbook involved."""

    def __init__(self, rows: Sequence[tuple[Any, ...]]) -> None:
        self._rows = rows

    def rows(self, file: IO[bytes]) -> Iterator[FakeRow]:
        for number, values in enumerate(self._rows, start=2):
            padded = (*values, None, None, None, None)[:4]
            yield FakeRow(number=number, values=padded)


class FrozenClock:
    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at
