"""Reading the books.

Only posted vouchers appear. A draft is a working document — counting it would
mean the balances change while someone is still typing.

There is no table behind this module: the ledger is what the voucher lines add
up to. Keeping a running balance per account in its own table would be a second
copy of the same truth, and the two would drift the first time a write failed
halfway.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Row, Select, and_, case, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.modules.accounts.models import Account
from app.modules.accounts.puc import Nature
from app.modules.ledger.schemas import (
    AccountLedger,
    LedgerAccount,
    LedgerEntry,
    LedgerReport,
    LedgerTotals,
)
from app.modules.third_parties.models import ThirdParty
from app.modules.vouchers.errors import AccountNotPostable
from app.modules.vouchers.models import Voucher, VoucherLine
from app.modules.vouchers.posting import ZERO, VoucherStatus


class LedgerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def report(
        self,
        *,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        account_prefix: str | None = None,
        third_party_id: int | None = None,
    ) -> LedgerReport:
        """Every account that moved, with what it carried in and what it ended on.

        One query rather than two: the opening balance is the same sum over an
        earlier slice of dates, so conditional aggregation gets both at once.
        """
        # The opening balance is the same sum over an earlier slice of dates,
        # so one set of conditions per slice gets both in a single query.
        before: list[ColumnElement[bool]] = (
            [Voucher.date < date_from] if date_from is not None else []
        )
        within: list[ColumnElement[bool]] = []
        if date_from is not None:
            within.append(Voucher.date >= date_from)
        if date_to is not None:
            within.append(Voucher.date <= date_to)

        query = (
            select(
                Account.code,
                Account.name,
                Account.nature,
                # No `date_from` means no "before", so the opening is zero
                # rather than everything.
                _summed(VoucherLine.debit, before, unbounded=False).label(
                    "opening_debit"
                ),
                _summed(VoucherLine.credit, before, unbounded=False).label(
                    "opening_credit"
                ),
                _summed(VoucherLine.debit, within).label("debit"),
                _summed(VoucherLine.credit, within).label("credit"),
            )
            .select_from(VoucherLine)
            .join(Voucher, Voucher.id == VoucherLine.voucher_id)
            .join(Account, Account.code == VoucherLine.account_code)
            .where(Voucher.status == VoucherStatus.POSTED)
            .group_by(Account.code, Account.name, Account.nature)
            .order_by(Account.code)
        )
        query = _narrow(query, account_prefix, third_party_id)

        accounts: list[LedgerAccount] = []
        for row in (await self._session.execute(query)).all():
            opening = _money(row.opening_debit) - _money(row.opening_credit)
            debit, credit = _money(row.debit), _money(row.credit)

            # An account whose only movement is outside the range still belongs
            # in the report when it carries a balance into it.
            if opening == ZERO and debit == ZERO and credit == ZERO:
                continue

            accounts.append(
                LedgerAccount(
                    code=row.code,
                    name=row.name,
                    nature=row.nature,
                    opening_balance=opening,
                    debit=debit,
                    credit=credit,
                    closing_balance=opening + debit - credit,
                )
            )

        return LedgerReport(
            date_from=date_from,
            date_to=date_to,
            accounts=accounts,
            totals=_totals(accounts),
        )

    async def account(
        self,
        code: str,
        *,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        third_party_id: int | None = None,
    ) -> AccountLedger:
        """The movements behind one account, in the order they were posted."""
        account = await self._session.get(Account, code.strip())
        if account is None or account.is_deleted:
            raise AccountNotPostable(code, "it does not exist")

        opening = await self._balance_before(account.code, date_from, third_party_id)
        rows = await self._movements(account.code, date_from, date_to, third_party_id)

        running = opening
        entries: list[LedgerEntry] = []
        for row in rows:
            debit, credit = _money(row.debit), _money(row.credit)
            running = running + debit - credit
            entries.append(
                LedgerEntry(
                    voucher_id=row.voucher_id,
                    voucher_number=row.number,
                    date=row.date,
                    period_year=row.period_year,
                    period_month=row.period_month,
                    # The line's own note when it has one, the voucher's
                    # otherwise: a ledger reads badly with a blank column.
                    description=row.line_description or row.description,
                    third_party_id=row.third_party_id,
                    third_party_name=(
                        row.ThirdParty.full_name if row.ThirdParty else None
                    ),
                    third_party_document=(
                        row.ThirdParty.formatted_document if row.ThirdParty else None
                    ),
                    debit=debit,
                    credit=credit,
                    running_balance=running,
                    reverses_voucher_id=row.reverses_voucher_id,
                )
            )

        return AccountLedger(
            code=account.code,
            name=account.name,
            nature=account.nature,
            date_from=date_from,
            date_to=date_to,
            opening_balance=opening,
            entries=entries,
            debit=sum((e.debit for e in entries), ZERO),
            credit=sum((e.credit for e in entries), ZERO),
            closing_balance=running,
        )

    async def auxiliary_book(
        self,
        *,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        account_prefix: str | None = None,
        third_party_id: int | None = None,
    ) -> list[AccountLedger]:
        """The auxiliary book: every account's movements, account by account.

        The same thing `account()` returns, for as many accounts as the filters
        match — two queries for all of them rather than two per account, which
        is what makes exporting a whole chart survivable.

        An account whose movement all falls outside the range still belongs in
        the book when it carries a balance into it: a book that omits an opening
        balance does not add up.
        """
        openings = await self._balances_before(
            date_from, account_prefix, third_party_id
        )
        rows = await self._movements(
            None, date_from, date_to, third_party_id, account_prefix
        )

        grouped: dict[str, list[Row[Any]]] = {}
        names: dict[str, tuple[str, Nature]] = {}
        for row in rows:
            grouped.setdefault(row.account_code, []).append(row)
            names[row.account_code] = (row.account_name, row.nature)

        book: list[AccountLedger] = []
        # Sorted by code, which is also the order of the chart: the book reads
        # top-down like the plan it follows.
        for code in sorted(set(grouped) | set(openings)):
            movements = grouped.get(code, [])
            opening = openings.get(code, ZERO)
            if not movements and opening == ZERO:
                continue

            name, nature = names.get(code) or await self._describe(code)
            running = opening
            entries: list[LedgerEntry] = []
            for row in movements:
                debit, credit = _money(row.debit), _money(row.credit)
                running = running + debit - credit
                entries.append(
                    LedgerEntry(
                        voucher_id=row.voucher_id,
                        voucher_number=row.number,
                        date=row.date,
                        period_year=row.period_year,
                        period_month=row.period_month,
                        description=row.line_description or row.description,
                        third_party_id=row.third_party_id,
                        third_party_name=(
                            row.ThirdParty.full_name if row.ThirdParty else None
                        ),
                        third_party_document=(
                            row.ThirdParty.formatted_document
                            if row.ThirdParty
                            else None
                        ),
                        debit=debit,
                        credit=credit,
                        running_balance=running,
                        reverses_voucher_id=row.reverses_voucher_id,
                    )
                )

            book.append(
                AccountLedger(
                    code=code,
                    name=name,
                    nature=nature,
                    date_from=date_from,
                    date_to=date_to,
                    opening_balance=opening,
                    entries=entries,
                    debit=sum((e.debit for e in entries), ZERO),
                    credit=sum((e.credit for e in entries), ZERO),
                    closing_balance=running,
                )
            )

        return book

    # --- plumbing ---------------------------------------------------------

    async def _describe(self, code: str) -> tuple[str, Nature]:
        """Name and nature of an account with no movement in the range.

        Only reached for the accounts that are in the book on the strength of an
        opening balance alone, so it stays a handful of lookups rather than one
        per account.
        """
        account = await self._session.get(Account, code)
        if account is None:
            return code, Nature.DEBIT
        return account.name, account.nature

    async def _balances_before(
        self,
        date_from: dt.date | None,
        account_prefix: str | None,
        third_party_id: int | None,
    ) -> dict[str, Decimal]:
        """What every account carried into the range, in one query."""
        if date_from is None:
            return {}

        query = (
            select(
                VoucherLine.account_code,
                func.coalesce(func.sum(VoucherLine.debit), 0).label("debit"),
                func.coalesce(func.sum(VoucherLine.credit), 0).label("credit"),
            )
            .select_from(VoucherLine)
            .join(Voucher, Voucher.id == VoucherLine.voucher_id)
            .where(
                Voucher.status == VoucherStatus.POSTED,
                Voucher.date < date_from,
            )
            .group_by(VoucherLine.account_code)
        )
        if account_prefix:
            query = query.where(VoucherLine.account_code.startswith(account_prefix))
        if third_party_id is not None:
            query = query.where(VoucherLine.third_party_id == third_party_id)

        return {
            row.account_code: _money(row.debit) - _money(row.credit)
            for row in (await self._session.execute(query)).all()
        }

    async def _balance_before(
        self, code: str, date_from: dt.date | None, third_party_id: int | None
    ) -> Decimal:
        if date_from is None:
            return ZERO

        query = (
            select(
                func.coalesce(func.sum(VoucherLine.debit), 0),
                func.coalesce(func.sum(VoucherLine.credit), 0),
            )
            .select_from(VoucherLine)
            .join(Voucher, Voucher.id == VoucherLine.voucher_id)
            .where(
                Voucher.status == VoucherStatus.POSTED,
                VoucherLine.account_code == code,
                Voucher.date < date_from,
            )
        )
        if third_party_id is not None:
            query = query.where(VoucherLine.third_party_id == third_party_id)

        debit, credit = (await self._session.execute(query)).one()
        return _money(debit) - _money(credit)

    async def _movements(
        self,
        code: str | None,
        date_from: dt.date | None,
        date_to: dt.date | None,
        third_party_id: int | None,
        account_prefix: str | None = None,
    ) -> Sequence[Row[Any]]:
        """Lines in the order the books were written in.

        `code` narrows to one account, `account_prefix` to a branch, neither to
        the whole chart — the auxiliary book reads many accounts at once, and
        querying them one at a time would be one round trip per account.
        """
        query = (
            select(
                Voucher.id.label("voucher_id"),
                Voucher.number,
                Voucher.date,
                Voucher.period_year,
                Voucher.period_month,
                Voucher.description,
                Voucher.reverses_voucher_id,
                VoucherLine.account_code,
                Account.name.label("account_name"),
                Account.nature,
                VoucherLine.third_party_id,
                VoucherLine.debit,
                VoucherLine.credit,
                VoucherLine.description.label("line_description"),
                # The entity, not its name columns: `full_name` is a Python
                # property, and selecting the pieces here would be a third copy
                # of the rule that assembles them.
                ThirdParty,
            )
            .select_from(VoucherLine)
            .join(Voucher, Voucher.id == VoucherLine.voucher_id)
            .join(Account, Account.code == VoucherLine.account_code)
            # Outer: most lines name no third party, and an inner join would
            # drop them from the account's own ledger.
            .outerjoin(ThirdParty, ThirdParty.id == VoucherLine.third_party_id)
            .where(Voucher.status == VoucherStatus.POSTED)
            # By number within the date, not by date alone: the consecutive is
            # the order the books were written in, which is what a running
            # balance follows. Account first, so one pass yields whole blocks.
            .order_by(
                VoucherLine.account_code,
                Voucher.date,
                Voucher.number,
                VoucherLine.line_number,
            )
        )
        if code is not None:
            query = query.where(VoucherLine.account_code == code)
        if account_prefix:
            query = query.where(VoucherLine.account_code.startswith(account_prefix))
        if date_from is not None:
            query = query.where(Voucher.date >= date_from)
        if date_to is not None:
            query = query.where(Voucher.date <= date_to)
        if third_party_id is not None:
            query = query.where(VoucherLine.third_party_id == third_party_id)

        return (await self._session.execute(query)).all()


def _summed(
    column: InstrumentedAttribute[Decimal],
    conditions: list[ColumnElement[bool]],
    *,
    unbounded: bool = True,
) -> ColumnElement[Any]:
    """Sum a column over the rows the conditions select.

    With no conditions the meaning depends on the slice: an unbounded range is
    everything, while a "before" with no starting date is nothing at all.
    """
    if conditions:
        return func.coalesce(func.sum(case((and_(*conditions), column), else_=0)), 0)
    if unbounded:
        return func.coalesce(func.sum(column), 0)
    return literal(0)


def _narrow(
    query: Select[Any],
    account_prefix: str | None,
    third_party_id: int | None,
) -> Select[Any]:
    if account_prefix:
        # Codes are prefixes of their children, so one branch is one LIKE.
        query = query.where(Account.code.startswith(account_prefix.strip()))
    if third_party_id is not None:
        query = query.where(VoucherLine.third_party_id == third_party_id)
    return query


def _totals(accounts: list[LedgerAccount]) -> LedgerTotals:
    debit = sum((a.debit for a in accounts), ZERO)
    credit = sum((a.credit for a in accounts), ZERO)
    balance = sum((a.closing_balance for a in accounts), ZERO)

    return LedgerTotals(
        debit=debit,
        credit=credit,
        balance=balance,
        # The one check that covers everything behind it: if every voucher
        # balanced, the books as a whole add up to nothing.
        is_balanced=balance == ZERO,
    )


def _money(value: Any) -> Decimal:
    """Aggregates come back as float on SQLite and Decimal on Postgres."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))
