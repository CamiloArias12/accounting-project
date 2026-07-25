"""Input shapes for the use cases.

Plain dataclasses rather than Pydantic models: these cross from the web adapter
into the application layer, and the application must not depend on the
framework used to parse a request.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.domain.puc import AccountLevel, Nature

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


@dataclass(frozen=True, slots=True)
class AccountFilters:
    level: AccountLevel | None = None
    parent_code: str | None = None
    search: str | None = None
    only_active: bool | None = None
    include_deleted: bool = False
    skip: int = 0
    limit: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True, slots=True)
class NewAccount:
    code: str
    name: str
    nature: Nature
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class AccountChanges:
    name: str | None = None
    nature: Nature | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class TreeQuery:
    """Which slice of the chart to render.

    `root_code` keeps a caller from pulling the whole chart when it only needs
    one branch; `max_depth` keeps it from pulling every descendant.
    """

    root_code: str | None = None
    max_depth: int | None = None
    include_deleted: bool = False


@dataclass(frozen=True, slots=True)
class RowFailure:
    row: int
    code: str | None
    message: str


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    created: int
    updated: int
    skipped: int
    errors: list[RowFailure]
