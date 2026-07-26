"""Keeping the UVT up to date.

The refresh never runs inside the request that asked for it: the endpoint hands
the work to a background task and answers straight away. A source that takes
four seconds to time out three times over must not be four seconds a caller
waits for.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.uvt.errors import UvtValueNotFound
from app.modules.uvt.models import RunStatus, UvtFetchRun, UvtSource, UvtValue
from app.modules.uvt.provider import (
    UvtNotPublished,
    UvtProvider,
    UvtSourceUnavailable,
    fetch_with_retry,
)


class UvtService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- reads ------------------------------------------------------------

    async def value_for(self, year: int) -> Decimal:
        """The UVT of a year, or a refusal to guess one."""
        stored = await self._find(year)
        if stored is None:
            raise UvtValueNotFound(year)
        return stored.value

    async def all_values(self) -> Sequence[UvtValue]:
        result = await self._session.execute(
            select(UvtValue).order_by(UvtValue.year.desc())
        )
        return result.scalars().all()

    async def runs(self, *, limit: int = 50) -> Sequence[UvtFetchRun]:
        result = await self._session.execute(
            select(UvtFetchRun).order_by(UvtFetchRun.id.desc()).limit(limit)
        )
        return result.scalars().all()

    # --- writes -----------------------------------------------------------

    async def set_manually(self, year: int, value: Decimal) -> UvtValue:
        """Type in a value the source does not have yet.

        Marked `MANUAL` so a later fetch leaves it alone: a figure a person read
        off the resolution outranks whatever a scraper makes of the page.
        """
        stored = await self._find(year)

        if stored is None:
            stored = UvtValue(year=year, value=value, source=UvtSource.MANUAL)
            self._session.add(stored)
        else:
            stored.value = value
            stored.source = UvtSource.MANUAL
            stored.provider = None
            stored.fetched_at = None

        await self._session.commit()
        await self._session.refresh(stored)
        return stored

    async def refresh(self, year: int, provider: UvtProvider) -> UvtFetchRun:
        """Fetch a year and record what happened, whatever happened.

        Idempotent by construction: the year is unique, so the second run
        updates the row the first one wrote instead of adding another. Running
        it every night is safe.
        """
        started = _now()
        stored = await self._find(year)

        if stored is not None and stored.source is UvtSource.MANUAL:
            return await self._record(
                year=year,
                provider=provider.name,
                status=RunStatus.SKIPPED,
                started=started,
                attempts=0,
                detail="a manually entered value is already stored",
            )

        try:
            value, attempts = await fetch_with_retry(provider, year)
        except UvtNotPublished as exc:
            return await self._record(
                year=year,
                provider=provider.name,
                status=RunStatus.SKIPPED,
                started=started,
                attempts=1,
                detail=str(exc),
            )
        except UvtSourceUnavailable as exc:
            return await self._record(
                year=year,
                provider=provider.name,
                status=RunStatus.FAILED,
                started=started,
                attempts=0,
                detail=str(exc),
            )

        if stored is None:
            stored = UvtValue(year=year, value=value)
            self._session.add(stored)
        else:
            stored.value = value

        stored.source = UvtSource.FETCHED
        stored.provider = provider.name
        stored.fetched_at = _now()

        return await self._record(
            year=year,
            provider=provider.name,
            status=RunStatus.SUCCEEDED,
            started=started,
            attempts=attempts,
            value=value,
        )

    # --- plumbing ---------------------------------------------------------

    async def _find(self, year: int) -> UvtValue | None:
        result = await self._session.execute(
            select(UvtValue).where(UvtValue.year == year)
        )
        return result.scalar_one_or_none()

    async def _record(
        self,
        *,
        year: int,
        provider: str,
        status: RunStatus,
        started: dt.datetime,
        attempts: int,
        value: Decimal | None = None,
        detail: str | None = None,
    ) -> UvtFetchRun:
        run = UvtFetchRun(
            year=year,
            status=status,
            provider=provider,
            attempts=attempts,
            value=value,
            detail=detail[:255] if detail else None,
            started_at=started,
            finished_at=_now(),
        )
        self._session.add(run)
        # The value and its run are written together: a stored figure with no
        # record of where it came from is the thing this table exists to stop.
        await self._session.commit()
        await self._session.refresh(run)
        return run


def _now() -> dt.datetime:
    # Naive, to match the other timestamp columns.
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)
