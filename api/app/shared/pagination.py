"""One shape for every list the API returns.

A bare array cannot be paged: the client has no way to know whether it is
looking at everything or at the first fifty of nine hundred. The envelope
carries the total, which is the one number a pager needs and the one a bare
array cannot express.

`skip`/`limit` rather than `page`/`size`: the services already spoke that way,
and it is the pair that maps straight onto SQL without arithmetic in between.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

#: What a caller gets when it asks for no particular size. Small enough that a
#: chart of 2,449 accounts does not arrive in one response by accident.
DEFAULT_LIMIT = 50
MAX_LIMIT = 500


class Page[T](BaseModel):
    """A slice of a list, and enough context to ask for the next one.

    Parametrised with the *read* schema, never the ORM model: Pydantic builds a
    concrete class per parametrisation and cannot make a schema out of a
    SQLAlchemy mapping. `from_attributes` is what lets the ORM rows go in
    unconverted.
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    #: Rows matching the filters, not rows in this page.
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total


async def count_of(session: AsyncSession, query: Select[Any]) -> int:
    """How many rows the query matches, ignoring any slice.

    The ordering is dropped first: it changes nothing about a count and
    Postgres would sort the whole set to produce it.
    """
    result = await session.execute(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    return int(result.scalar_one())
