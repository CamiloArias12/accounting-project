from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.auth.models import User
from app.modules.vouchers.models import Voucher
from app.modules.vouchers.posting import VoucherStatus
from app.modules.vouchers.schemas import (
    CompanyRead,
    VoucherCreate,
    VoucherRead,
    VoucherReverse,
    VoucherUpdate,
)
from app.modules.vouchers.service import VoucherService
from app.shared.config import settings
from app.shared.database import get_session
from app.shared.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page

router = APIRouter(
    prefix="/vouchers",
    tags=["vouchers"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(current_user)]


def get_service(session: SessionDep) -> VoucherService:
    return VoucherService(session)


ServiceDep = Annotated[VoucherService, Depends(get_service)]


@router.get("/company", response_model=CompanyRead)
async def issuing_company() -> CompanyRead:
    return CompanyRead(
        nit=settings.COMPANY_NIT,
        legal_name=settings.COMPANY_LEGAL_NAME,
        address=settings.COMPANY_ADDRESS,
        phone=settings.COMPANY_PHONE,
        email=settings.COMPANY_EMAIL,
    )


@router.get("", response_model=Page[VoucherRead])
async def list_vouchers(
    service: ServiceDep,
    voucher_status: Annotated[VoucherStatus | None, Query(alias="status")] = None,
    period_year: Annotated[int | None, Query()] = None,
    period_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    search: Annotated[str | None, Query(description="Match the description")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> Page[VoucherRead]:
    items, total = await service.find_many(
        status=voucher_status,
        period_year=period_year,
        period_month=period_month,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=limit,
    )
    return Page[VoucherRead](items=list(items), total=total, skip=skip, limit=limit)


@router.post("", response_model=VoucherRead, status_code=status.HTTP_201_CREATED)
async def create_voucher(
    payload: VoucherCreate, service: ServiceDep, user: CurrentUser
) -> Voucher:
    return await service.create(payload, user_id=user.id)


@router.get("/{voucher_id}", response_model=VoucherRead)
async def get_voucher(voucher_id: int, service: ServiceDep) -> Voucher:
    return await service.get(voucher_id)


@router.patch("/{voucher_id}", response_model=VoucherRead)
async def update_voucher(
    voucher_id: int, payload: VoucherUpdate, service: ServiceDep
) -> Voucher:
    return await service.update(voucher_id, payload)


@router.post("/{voucher_id}/post", response_model=VoucherRead)
async def post_voucher(
    voucher_id: int, service: ServiceDep, user: CurrentUser
) -> Voucher:
    return await service.post(voucher_id, user_id=user.id)


@router.post(
    "/{voucher_id}/reverse",
    response_model=VoucherRead,
    status_code=status.HTTP_201_CREATED,
)
async def reverse_voucher(
    voucher_id: int,
    payload: VoucherReverse,
    service: ServiceDep,
    user: CurrentUser,
) -> Voucher:
    return await service.reverse(voucher_id, payload, user_id=user.id)


@router.delete("/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voucher(voucher_id: int, service: ServiceDep) -> Response:
    await service.delete(voucher_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
