import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.ledger.book import Locale, build_auxiliary_book
from app.modules.ledger.schemas import AccountLedger, LedgerReport
from app.modules.ledger.service import LedgerService
from app.shared.config import settings
from app.shared.database import get_session

#: What a browser needs to see to hand the file to a spreadsheet application
#: rather than offer it as an unknown blob.
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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


@router.get(
    "/export",
    response_class=Response,
    responses={
        200: {
            "content": {XLSX_MEDIA_TYPE: {}},
            "description": "The auxiliary book as a spreadsheet",
        }
    },
)
async def export_auxiliary_book(
    service: ServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    account_code: Annotated[
        str | None, Query(description="Restrict to this branch of the chart")
    ] = None,
    third_party_id: ThirdParty = None,
    locale: Annotated[Locale, Query(description="Language of the headings")] = "es",
) -> Response:
    """The auxiliary book — every account's movements — as an .xlsx file.

    Built fresh on every request rather than kept: unlike an exógena filing,
    which is a document that was submitted and must come back byte for byte,
    this is a view of the books at the moment it is asked for.

    Declared before `/{account_code}` so that "export" is not read as the code
    of an account.
    """
    accounts = await service.auxiliary_book(
        date_from=date_from,
        date_to=date_to,
        account_prefix=account_code,
        third_party_id=third_party_id,
    )

    workbook = build_auxiliary_book(
        accounts,
        company=settings.COMPANY_LEGAL_NAME,
        date_from=date_from,
        date_to=date_to,
        generated_at=dt.datetime.now(),
        locale=locale,
    )

    filename = _filename(date_from, date_to)

    return Response(
        content=workbook,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _filename(date_from: dt.date | None, date_to: dt.date | None) -> str:
    """The range in the name, so two downloads do not look like the same file."""
    parts = ["libro-auxiliar"]
    if date_from:
        parts.append(date_from.isoformat())
    if date_to:
        parts.append(date_to.isoformat())
    return "-".join(parts) + ".xlsx"


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
