"""Opening and closing accounting periods.

Only closed periods are stored, so `status_of` answers for any month rather
than looking one up — which is what lets the books be used before anyone has
created a single period.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.periods.errors import PeriodAlreadyClosed, PeriodAlreadyOpen
from app.modules.periods.models import Period
from app.modules.periods.period import AccountingPeriod, PeriodStatus
from app.modules.periods.schemas import PeriodRead


class PeriodService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def status_of(self, period: AccountingPeriod) -> PeriodStatus:
        """Whether a month accepts entries. Absent means open."""
        stored = await self._find(period)
        return stored.status if stored else PeriodStatus.OPEN

    async def read(self, period: AccountingPeriod) -> PeriodRead:
        stored = await self._find(period)

        if stored is None:
            return PeriodRead(
                year=period.year, month=period.month, status=PeriodStatus.OPEN
            )

        return PeriodRead(
            year=stored.year,
            month=stored.month,
            status=stored.status,
            changed_at=stored.changed_at,
            changed_by_user_id=stored.changed_by_user_id,
        )

    async def year(self, year: int) -> list[PeriodRead]:
        """The twelve months of a year, whether or not they have a row."""
        stored = {row.month: row for row in await self._of_year(year)}

        return [
            PeriodRead(
                year=year,
                month=month,
                status=(stored[month].status if month in stored else PeriodStatus.OPEN),
                changed_at=stored[month].changed_at if month in stored else None,
                changed_by_user_id=(
                    stored[month].changed_by_user_id if month in stored else None
                ),
            )
            for month in range(1, 13)
        ]

    async def close(
        self, period: AccountingPeriod, *, user_id: int | None = None
    ) -> PeriodRead:
        """Close a month.

        Drafts already written into it are left alone: they are not in the
        books, so they alter nothing. They simply can no longer be posted.
        """
        stored = await self._find(period)

        if stored is None:
            stored = Period.closed(period, user_id=user_id)
            self._session.add(stored)
        elif stored.is_closed:
            raise PeriodAlreadyClosed(str(period))
        else:
            stored.close(user_id=user_id)

        await self._session.commit()
        return await self.read(period)

    async def reopen(
        self, period: AccountingPeriod, *, user_id: int | None = None
    ) -> PeriodRead:
        stored = await self._find(period)

        if stored is None or not stored.is_closed:
            raise PeriodAlreadyOpen(str(period))

        stored.reopen(user_id=user_id)
        await self._session.commit()
        return await self.read(period)

    async def _find(self, period: AccountingPeriod) -> Period | None:
        result = await self._session.execute(
            select(Period).where(
                Period.year == period.year, Period.month == period.month
            )
        )
        return result.scalar_one_or_none()

    async def _of_year(self, year: int) -> Sequence[Period]:
        result = await self._session.execute(
            select(Period).where(Period.year == year).order_by(Period.month)
        )
        return result.scalars().all()
