from __future__ import annotations

import logging
from typing import Final

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis

from app.modules.accounts.schemas import AccountNode

_NAMESPACE: Final = "accounts:tree"
_NODES: Final = TypeAdapter(list[AccountNode])
_logger = logging.getLogger(__name__)


class AccountTreeCache:
    """Redis cache for the account tree."""
    def __init__(self, redis: Redis, ttl: int) -> None:
        self._redis = redis
        self._ttl = ttl

    async def get(
        self, root_code: str | None, max_depth: int | None, include_deleted: bool
    ) -> list[AccountNode] | None:
        key = _key(root_code, max_depth, include_deleted)
        try:
            payload = await self._redis.get(key)
        except Exception:
            _logger.warning("account cache unavailable on read", exc_info=True)
            return None

        if payload is None:
            return None

        try:
            return _NODES.validate_json(payload)
        except ValidationError:
            _logger.warning("discarding unreadable cache entry %s", key)
            return None

    async def set(
        self,
        root_code: str | None,
        max_depth: int | None,
        include_deleted: bool,
        nodes: list[AccountNode],
    ) -> None:
        try:
            payload = _NODES.dump_json(nodes)
            await self._redis.set(
                _key(root_code, max_depth, include_deleted), payload, ex=self._ttl
            )
        except Exception:
            _logger.warning("account cache unavailable on write", exc_info=True)

    async def clear(self) -> None:
        try:
            keys = [key async for key in self._redis.scan_iter(f"{_NAMESPACE}:*")]
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            _logger.warning("could not invalidate the account cache", exc_info=True)


class NullAccountTreeCache:
    """No-op cache, for tests and for running without Redis."""

    async def get(
        self, root_code: str | None, max_depth: int | None, include_deleted: bool
    ) -> list[AccountNode] | None:
        return None

    async def set(
        self,
        root_code: str | None,
        max_depth: int | None,
        include_deleted: bool,
        nodes: list[AccountNode],
    ) -> None:
        return None

    async def clear(self) -> None:
        return None


def _key(root_code: str | None, max_depth: int | None, include_deleted: bool) -> str:
    root = root_code or "*"
    depth = "*" if max_depth is None else max_depth
    return f"{_NAMESPACE}:{root}:{depth}:{int(include_deleted)}"
