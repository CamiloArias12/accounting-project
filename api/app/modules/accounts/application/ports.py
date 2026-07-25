"""Ports: what the use cases need, stated as abstractions.

Declared here — in the application layer — and implemented in
`infrastructure/`, so the dependency points inward: SQLAlchemy and Redis know
about the use cases, never the other way round.

`Protocol` rather than ABC on purpose: adapters do not import this module to
inherit from it, which keeps the coupling one-directional.

Note there is no cache port. Caching is a persistence concern, so it lives in
infrastructure as a decorator implementing `AccountRepository` — the use cases
cannot tell whether a read was served from Postgres or Redis.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import IO, Protocol

from app.modules.accounts.application.queries import AccountFilters
from app.modules.accounts.domain.account import Account


class AccountRepository(Protocol):
    async def get(
        self, code: str, *, include_deleted: bool = False
    ) -> Account | None: ...

    async def exists(self, code: str, *, include_deleted: bool = False) -> bool: ...

    async def existing_codes(
        self, codes: Iterable[str], *, include_deleted: bool = False
    ) -> set[str]: ...

    async def find_many(self, filters: AccountFilters) -> Sequence[Account]: ...

    async def list_subtree(
        self, root_code: str | None, *, include_deleted: bool = False
    ) -> Sequence[Account]:
        """Every account under `root_code`, root included.

        `None` means the whole chart.
        """
        ...

    async def has_children(
        self, code: str, *, include_deleted: bool = False
    ) -> bool: ...

    async def add(self, account: Account) -> Account: ...

    async def add_many(self, accounts: Sequence[Account]) -> int: ...

    async def save(self, account: Account) -> Account: ...


class SpreadsheetRow(Protocol):
    """One parsed row, still untyped: validation belongs to the use case."""

    @property
    def number(self) -> int: ...

    @property
    def values(self) -> tuple[object, object, object, object]: ...


class SpreadsheetReader(Protocol):
    """Reads the import file, so the use case never imports openpyxl."""

    def rows(self, file: IO[bytes]) -> Iterable[SpreadsheetRow]: ...


class Clock(Protocol):
    """Injected so time-dependent behaviour stays testable."""

    def now(self) -> datetime: ...
