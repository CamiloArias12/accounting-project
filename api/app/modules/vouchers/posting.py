"""Rules of double-entry bookkeeping.

The innermost layer, like `accounts.puc`: no database, no HTTP, no framework.

The rule this module exists for is that a voucher's debits must equal its
credits. The reference project computes those two totals only to print them at
the foot of a report, so an unbalanced entry saves happily and the trial balance
stops balancing with nothing to point at. Here it is a precondition of posting.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

#: Money is stored and compared as a fixed-point decimal, never as a float:
#: 0.1 + 0.2 must be 0.3 in a ledger.
CENT: Final = Decimal("0.01")
ZERO: Final = Decimal("0")

MAX_AMOUNT: Final = Decimal("9999999999999999.99")

#: An entry is a movement and its counterpart. One line alone would already be
#: caught by the balance check, but as a difference for the whole amount — which
#: says nothing about what is actually missing.
MIN_LINES: Final = 2


class VoucherStatus(enum.StrEnum):
    """Where a voucher is in its life.

    `DRAFT` is a working document: editable, deletable, and outside the books.
    `POSTED` is an accounting record: it has a consecutive number, it is part of
    the balances, and it cannot be altered — only reversed.
    """

    DRAFT = "Draft"
    POSTED = "Posted"


class PostingError(ValueError):
    """The lines do not form a valid accounting entry."""


class TooFewLines(PostingError):
    def __init__(self, count: int) -> None:
        super().__init__(
            f"A voucher needs at least {MIN_LINES} lines, and this one has "
            f"{count}: every movement has a counterpart"
        )
        self.count = count


class UnbalancedVoucher(PostingError):
    def __init__(self, debit: Decimal, credit: Decimal) -> None:
        super().__init__(
            f"Debits ({debit}) and credits ({credit}) must be equal; "
            f"the entry is off by {abs(debit - credit)}"
        )
        self.debit = debit
        self.credit = credit
        self.difference = debit - credit


@dataclass(frozen=True, slots=True)
class Amounts:
    """One line's two columns. Exactly one of them carries the value."""

    debit: Decimal
    credit: Decimal

    def __post_init__(self) -> None:
        for name, value in (("debit", self.debit), ("credit", self.credit)):
            if value < ZERO:
                raise PostingError(f"A {name} cannot be negative")
            if value > MAX_AMOUNT:
                raise PostingError(f"A {name} exceeds the largest storable amount")
            if value != value.quantize(CENT):
                raise PostingError(f"A {name} cannot have more than two decimals")

        if self.debit == ZERO and self.credit == ZERO:
            raise PostingError("A line must carry either a debit or a credit")
        if self.debit != ZERO and self.credit != ZERO:
            # Allowing both would let one line hide a compensation inside itself,
            # which no report could then break down.
            raise PostingError("A line cannot be both a debit and a credit")


def totals(amounts: list[Amounts]) -> tuple[Decimal, Decimal]:
    """The two column sums, in the order debit, credit."""
    debit = sum((line.debit for line in amounts), ZERO)
    credit = sum((line.credit for line in amounts), ZERO)
    return debit, credit


def check_balanced(amounts: list[Amounts]) -> None:
    """Raise unless the entry balances. The one rule that cannot be skipped."""
    if len(amounts) < MIN_LINES:
        raise TooFewLines(len(amounts))

    debit, credit = totals(amounts)
    if debit != credit:
        raise UnbalancedVoucher(debit, credit)
