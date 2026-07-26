"""What the ledger looks like over HTTP.

Balances are signed: `debit - credit`, always, whatever the account's nature.
That is what makes the whole report add up to zero — the single check that says
every voucher behind it was balanced. A client that wants to show a payable as a
positive figure has `nature` to work it out.
"""

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
    #: Where the account stood before the range began.
    opening_balance: Decimal
    debit: Decimal
    credit: Decimal
    #: opening_balance + debit - credit
    closing_balance: Decimal


class LedgerTotals(BaseModel):
    debit: Decimal
    credit: Decimal
    #: Must be zero. If it is not, some voucher went in unbalanced.
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
    #: Resolved here rather than left to the client: an id in a ledger column
    #: is not something a person reads.
    third_party_name: str | None
    #: The number as people write it, check digit included. What identifies a
    #: third party on a printed book; two of them can share a name.
    third_party_document: str | None
    debit: Decimal
    credit: Decimal
    #: The account's balance after this movement.
    running_balance: Decimal
    #: Set when this line belongs to a reversing entry.
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
