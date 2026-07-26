from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.auth.models import User
from app.modules.periods.period import (
    MAX_PERIOD_YEAR,
    MIN_PERIOD_YEAR,
    AccountingPeriod,
)
from app.modules.periods.schemas import PeriodRead
from app.modules.periods.service import PeriodService
from app.shared.database import get_session

router = APIRouter(
    prefix="/periods",
    tags=["accounting periods"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(current_user)]

Year = Annotated[int, Path(ge=MIN_PERIOD_YEAR, le=MAX_PERIOD_YEAR)]
Month = Annotated[int, Path(ge=1, le=12)]


def get_service(session: SessionDep) -> PeriodService:
    return PeriodService(session)


ServiceDep = Annotated[PeriodService, Depends(get_service)]


@router.get("/{year}", response_model=list[PeriodRead])
async def year_of_periods(year: Year, service: ServiceDep) -> list[PeriodRead]:
    """The twelve months of a year and whether each accepts entries."""
    return await service.year(year)


@router.get("/{year}/{month}", response_model=PeriodRead)
async def read_period(year: Year, month: Month, service: ServiceDep) -> PeriodRead:
    return await service.read(AccountingPeriod(year=year, month=month))


@router.post("/{year}/{month}/close", response_model=PeriodRead)
async def close_period(
    year: Year, month: Month, service: ServiceDep, user: CurrentUser
) -> PeriodRead:
    """Close a month.

    From here on nothing can be posted into it. Drafts already written against
    it stay as they are — they are not in the books — but they can no longer be
    posted.
    """
    return await service.close(
        AccountingPeriod(year=year, month=month), user_id=user.id
    )


@router.post("/{year}/{month}/reopen", response_model=PeriodRead)
async def reopen_period(
    year: Year, month: Month, service: ServiceDep, user: CurrentUser
) -> PeriodRead:
    """Undo a close, recording who did it."""
    return await service.reopen(
        AccountingPeriod(year=year, month=month), user_id=user.id
    )
