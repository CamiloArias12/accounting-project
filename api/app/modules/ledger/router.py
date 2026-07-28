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

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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
    return await service.report(
        date_from=date_from,
        date_to=date_to,
        account_prefix=account_code,
        third_party_id=third_party_id,
    )


@router.get("/book", response_model=list[AccountLedger])
async def auxiliary_book(
    service: ServiceDep,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    account_code: Annotated[
        str | None, Query(description="Restrict to this branch of the chart")
    ] = None,
    third_party_id: ThirdParty = None,
) -> list[AccountLedger]:
    """The movements themselves, account by account.

    What `/export` writes into a spreadsheet, as JSON, so the screen and the
    file are the same book and cannot drift apart.
    """
    return await service.auxiliary_book(
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
    return await service.account(
        account_code,
        date_from=date_from,
        date_to=date_to,
        third_party_id=third_party_id,
    )
