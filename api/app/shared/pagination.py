from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


class Page[T](BaseModel):
    """A slice of a list, and enough context to ask for the next one."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total


async def count_of(session: AsyncSession, query: Select[Any]) -> int:
    result = await session.execute(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    return int(result.scalar_one())
