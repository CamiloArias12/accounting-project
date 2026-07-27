from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.models import Account
from app.modules.periods.errors import PeriodClosed
from app.modules.periods.period import AccountingPeriod, PeriodStatus
from app.modules.periods.service import PeriodService
from app.modules.third_parties.models import ThirdParty
from app.modules.vouchers.errors import (
    AccountNotPostable,
    ThirdPartyRequired,
    UnknownThirdParty,
    VoucherAlreadyPosted,
    VoucherNotFound,
)
from app.modules.vouchers.models import Voucher, VoucherLine
from app.modules.vouchers.posting import VoucherStatus
from app.modules.vouchers.schemas import (
    VoucherCreate,
    VoucherLineInput,
    VoucherReverse,
    VoucherUpdate,
)
from app.shared.pagination import count_of

_NUMBER_ATTEMPTS = 5


class VoucherService:
    """Business rules for accounting vouchers."""
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


    async def get(self, voucher_id: int) -> Voucher:
        voucher = await self._session.get(Voucher, voucher_id)
        if voucher is None:
            raise VoucherNotFound(voucher_id)
        return voucher

    async def find_many(
        self,
        *,
        status: VoucherStatus | None = None,
        period_year: int | None = None,
        period_month: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[Voucher], int]:
        query: Select[tuple[Voucher]] = select(Voucher)

        if status is not None:
            query = query.where(Voucher.status == status)
        if period_year is not None:
            query = query.where(Voucher.period_year == period_year)
        if period_month is not None:
            query = query.where(Voucher.period_month == period_month)
        if date_from is not None:
            query = query.where(Voucher.date >= date_from)
        if date_to is not None:
            query = query.where(Voucher.date <= date_to)
        if search:
            query = query.where(Voucher.description.ilike(f"%{search.strip()}%"))

        total = await count_of(self._session, query)
        result = await self._session.execute(
            query.order_by(Voucher.date.desc(), Voucher.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total


    async def create(
        self, payload: VoucherCreate, *, user_id: int | None = None
    ) -> Voucher:
        voucher = Voucher.open(
            date=payload.date,
            description=payload.description,
            period=_period_of(payload.period_year, payload.period_month, payload.date),
            created_by_user_id=user_id,
        )
        voucher.lines = await self._build_lines(payload.lines)
        voucher.require_balanced()

        self._session.add(voucher)
        await self._session.commit()
        await self._session.refresh(voucher)
        return voucher

    async def update(self, voucher_id: int, payload: VoucherUpdate) -> Voucher:
        voucher = await self.get(voucher_id)
        voucher.require_editable()

        if payload.date is not None:
            voucher.date = payload.date
        if payload.description is not None:
            voucher.description = payload.description.strip()
        if payload.period_year is not None and payload.period_month is not None:
            voucher.period_year = payload.period_year
            voucher.period_month = payload.period_month

        if payload.lines is not None:
            voucher.lines = await self._build_lines(payload.lines)

        voucher.require_balanced()

        await self._session.commit()
        await self._session.refresh(voucher)
        return voucher

    async def delete(self, voucher_id: int) -> None:
        voucher = await self.get(voucher_id)
        voucher.require_editable()

        await self._session.delete(voucher)
        await self._session.commit()

    async def post(self, voucher_id: int, *, user_id: int | None = None) -> Voucher:
        voucher = await self.get(voucher_id)
        if voucher.is_posted:
            raise VoucherAlreadyPosted(voucher_id)

        await self._require_open_period(voucher.period)
        for line in voucher.lines:
            await self._postable_account(line.account_code)

        for attempt in range(_NUMBER_ATTEMPTS):
            voucher.post(await self._next_number(), user_id=user_id)
            try:
                await self._session.commit()
            except IntegrityError:
                await self._session.rollback()
                voucher = await self.get(voucher_id)
                if attempt == _NUMBER_ATTEMPTS - 1:
                    raise
                continue

            await self._session.refresh(voucher)
            return voucher

        raise AssertionError("unreachable")

    async def reverse(
        self,
        voucher_id: int,
        payload: VoucherReverse,
        *,
        user_id: int | None = None,
    ) -> Voucher:
        original = await self.get(voucher_id)
        original.require_reversible()

        on = payload.date or original.date
        period = (
            original.period
            if payload.date is None
            else AccountingPeriod.of(payload.date)
        )
        await self._require_open_period(period)

        undo = original.reversal(
            date=on,
            description=(
                payload.description or f"Reversal of voucher {original.number}"
            ),
            period=period,
            user_id=user_id,
        )
        undo.require_balanced()
        undo.post(await self._next_number(), user_id=user_id)

        self._session.add(undo)
        await self._session.commit()
        await self._session.refresh(undo)
        return undo


    async def _require_open_period(self, period: AccountingPeriod) -> None:
        if await PeriodService(self._session).status_of(period) is PeriodStatus.CLOSED:
            raise PeriodClosed(str(period))

    async def _next_number(self) -> int:
        result = await self._session.execute(select(func.max(Voucher.number)))
        return (result.scalar_one() or 0) + 1

    async def _build_lines(self, inputs: list[VoucherLineInput]) -> list[VoucherLine]:
        lines: list[VoucherLine] = []

        for position, line in enumerate(inputs, start=1):
            account = await self._postable_account(line.account_code)

            if account.requires_third_party and line.third_party_id is None:
                raise ThirdPartyRequired(account.code)
            if line.third_party_id is not None:
                await self._known_third_party(line.third_party_id)

            lines.append(
                VoucherLine.write(
                    line_number=position,
                    account_code=account.code,
                    third_party_id=line.third_party_id,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                )
            )

        return lines

    async def _postable_account(self, code: str) -> Account:
        account = await self._session.get(Account, code.strip())

        if account is None or account.is_deleted:
            raise AccountNotPostable(code, "it does not exist")
        if not account.is_active:
            raise AccountNotPostable(code, "it is inactive")
        if await self._has_children(account.code):
            raise AccountNotPostable(code, "it is a heading, not a leaf")

        return account

    async def _has_children(self, code: str) -> bool:
        result = await self._session.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.parent_code == code, Account.deleted_at.is_(None))
        )
        return result.scalar_one() > 0

    async def _known_third_party(self, third_party_id: int) -> ThirdParty:
        third_party = await self._session.get(ThirdParty, third_party_id)
        if third_party is None or third_party.is_deleted:
            raise UnknownThirdParty(third_party_id)
        return third_party


def _period_of(
    year: int | None, month: int | None, day: date
) -> AccountingPeriod | None:
    if year is None or month is None:
        return None
    return AccountingPeriod(year=year, month=month)
