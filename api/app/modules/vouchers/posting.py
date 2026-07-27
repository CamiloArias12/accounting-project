from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

CENT: Final = Decimal("0.01")
ZERO: Final = Decimal("0")

MAX_AMOUNT: Final = Decimal("9999999999999999.99")

MIN_LINES: Final = 2


class VoucherStatus(enum.StrEnum):
    """Where a voucher is in its life."""

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
    """One line's two columns."""

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
            raise PostingError("A line cannot be both a debit and a credit")


def totals(amounts: list[Amounts]) -> tuple[Decimal, Decimal]:
    debit = sum((line.debit for line in amounts), ZERO)
    credit = sum((line.credit for line in amounts), ZERO)
    return debit, credit


def check_balanced(amounts: list[Amounts]) -> None:
    if len(amounts) < MIN_LINES:
        raise TooFewLines(len(amounts))

    debit, credit = totals(amounts)
    if debit != credit:
        raise UnbalancedVoucher(debit, credit)
