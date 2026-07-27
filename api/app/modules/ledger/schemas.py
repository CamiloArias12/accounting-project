from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.accounts.puc import Nature


class LedgerAccount(BaseModel):
    """One account's movement over the range, and where it ended up."""

    code: str = Field(examples=["110505"])
    name: str
    nature: Nature
    opening_balance: Decimal
    debit: Decimal
    credit: Decimal
    closing_balance: Decimal


class LedgerTotals(BaseModel):
    debit: Decimal
    credit: Decimal
    balance: Decimal
    is_balanced: bool


class LedgerReport(BaseModel):
    date_from: dt.date | None
    date_to: dt.date | None
    accounts: list[LedgerAccount]
    totals: LedgerTotals


class LedgerEntry(BaseModel):
    """One line of one voucher, as it reads in the account's ledger."""

    voucher_id: int
    voucher_number: int | None
    date: dt.date
    period_year: int
    period_month: int
    description: str
    third_party_id: int | None
    third_party_name: str | None
    third_party_document: str | None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal
    reverses_voucher_id: int | None


class AccountLedger(BaseModel):
    """The detail behind one account: every movement, in order."""

    code: str
    name: str
    nature: Nature
    date_from: dt.date | None
    date_to: dt.date | None
    opening_balance: Decimal
    entries: list[LedgerEntry]
    debit: Decimal
    credit: Decimal
    closing_balance: Decimal
