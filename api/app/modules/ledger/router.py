import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.ledger.schemas import AccountLedger, LedgerReport
from app.modules.ledger.service import LedgerService
from app.shared.database import get_session

# Read-only: the ledger is what the posted vouchers add up to, so there is
# nothing here to write.
router = APIRouter(
    prefix="/ledger",
    tags=["ledger"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_service(session: SessionDep) -> LedgerService:
    return LedgerService(session)


ServiceDep = Annotated[LedgerService, Depends(get_service)]

DateFrom = Annotated[dt.date | None, Query(description="Inclusive")]
DateTo = Annotated[dt.date | None, Query(description="Inclusive")]
ThirdParty = Annotated[int | None, Query(description="Only this third party")]


@router.get("", response_model=LedgerReport)
async def ledger_report(
    service: ServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    account_code: Annotated[
        str | None, Query(description="Restrict to this branch of the chart")
    ] = None,
    third_party_id: ThirdParty = None,
) -> LedgerReport:
    """Every account that moved, with its opening and closing balance.

    Only posted vouchers count — a draft is not in the books.

    Balances are signed (`debit - credit`), so the report as a whole adds up to
    zero. `totals.is_balanced` is that check, and it covers every voucher behind
    it at once.
    """
    return await service.report(
        date_from=date_from,
        date_to=date_to,
        account_prefix=account_code,
        third_party_id=third_party_id,
    )


@router.get("/{account_code}", response_model=AccountLedger)
async def account_ledger(
    account_code: str,
    service: ServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    third_party_id: ThirdParty = None,
) -> AccountLedger:
    """The movements behind one account, with a running balance.

    Ordered by date and consecutive number, which is the order the books were
    written in — the only order a running balance means anything in.
    """
    return await service.account(
        account_code,
        date_from=date_from,
        date_to=date_to,
        third_party_id=third_party_id,
    )
