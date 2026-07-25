"""Redis-backed caching decorator for `AccountRepository`.

It implements the same port as the SQLAlchemy adapter and wraps it, so the use
cases cannot tell whether a read came from Postgres or Redis — caching stays a
persistence detail.

Only `list_subtree` is cached: it is the expensive read (the whole chart is
thousands of rows) and the one the UI hits on every page load. Any write drops
the whole namespace, which is cheap and correct — a chart of accounts is read
far more often than it changes.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any, Final

from redis.asyncio import Redis

from app.modules.accounts.application.ports import AccountRepository
from app.modules.accounts.application.queries import AccountFilters
from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.puc import AccountLevel, Nature

_NAMESPACE: Final = "accounts:subtree"
_logger = logging.getLogger(__name__)


class CachedAccountRepository:
    def __init__(self, inner: AccountRepository, redis: Redis, ttl: int) -> None:
        self._inner = inner
        self._redis = redis
        self._ttl = ttl

    # --- cached read -----------------------------------------------------

    async def list_subtree(
        self, root_code: str | None, *, include_deleted: bool = False
    ) -> Sequence[Account]:
        key = f"{_NAMESPACE}:{root_code or '*'}:{int(include_deleted)}"

        cached = await self._read(key)
        if cached is not None:
            return cached

        accounts = await self._inner.list_subtree(
            root_code, include_deleted=include_deleted
        )
        await self._write(key, accounts)
        return accounts

    # --- writes: pass through, then drop the namespace -------------------

    async def add(self, account: Account) -> Account:
        saved = await self._inner.add(account)
        await self._invalidate()
        return saved

    async def add_many(self, accounts: Sequence[Account]) -> int:
        count = await self._inner.add_many(accounts)
        if count:
            await self._invalidate()
        return count

    async def save(self, account: Account) -> Account:
        saved = await self._inner.save(account)
        await self._invalidate()
        return saved

    # --- uncached reads --------------------------------------------------

    async def get(self, code: str, *, include_deleted: bool = False) -> Account | None:
        return await self._inner.get(code, include_deleted=include_deleted)

    async def exists(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self._inner.exists(code, include_deleted=include_deleted)

    async def existing_codes(
        self, codes: Iterable[str], *, include_deleted: bool = False
    ) -> set[str]:
        return await self._inner.existing_codes(codes, include_deleted=include_deleted)

    async def find_many(self, filters: AccountFilters) -> Sequence[Account]:
        return await self._inner.find_many(filters)

    async def has_children(self, code: str, *, include_deleted: bool = False) -> bool:
        return await self._inner.has_children(code, include_deleted=include_deleted)

    # --- plumbing --------------------------------------------------------

    async def _read(self, key: str) -> list[Account] | None:
        # A cache must never take the request down with it: on any Redis
        # trouble the call falls through to the database.
        try:
            payload = await self._redis.get(key)
        except Exception:
            _logger.warning("account cache unavailable on read", exc_info=True)
            return None

        if payload is None:
            return None

        try:
            return [_decode(item) for item in json.loads(payload)]
        except (ValueError, KeyError, TypeError):
            _logger.warning("discarding unreadable account cache entry %s", key)
            return None

    async def _write(self, key: str, accounts: Sequence[Account]) -> None:
        try:
            payload = json.dumps([_encode(account) for account in accounts])
            await self._redis.set(key, payload, ex=self._ttl)
        except Exception:
            _logger.warning("account cache unavailable on write", exc_info=True)

    async def _invalidate(self) -> None:
        try:
            keys = [key async for key in self._redis.scan_iter(f"{_NAMESPACE}:*")]
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            _logger.warning("could not invalidate the account cache", exc_info=True)


def _encode(account: Account) -> dict[str, Any]:
    return {
        "code": account.code,
        "name": account.name,
        "nature": account.nature.value,
        "level": account.level.value,
        "parent_code": account.parent_code,
        "is_active": account.is_active,
        "deleted_at": _iso(account.deleted_at),
        "created_at": _iso(account.created_at),
        "updated_at": _iso(account.updated_at),
    }


def _decode(data: dict[str, Any]) -> Account:
    return Account(
        code=data["code"],
        name=data["name"],
        nature=Nature(data["nature"]),
        level=AccountLevel(data["level"]),
        parent_code=data["parent_code"],
        is_active=data["is_active"],
        deleted_at=_parse(data["deleted_at"]),
        created_at=_parse(data["created_at"]),
        updated_at=_parse(data["updated_at"]),
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
