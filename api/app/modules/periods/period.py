"""What an accounting period is, and when it accepts entries.

The innermost layer, like `accounts.puc` and `vouchers.posting`: no database,
no HTTP, no framework.

A period is a month of the books. It matters because closing one is what makes
a set of figures final — after the close, nothing may be added to it, so a
balance printed today still says the same thing next year.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from typing import Final

#: Books do not go back before this, and a typo of a century should not pass.
MIN_PERIOD_YEAR: Final = 1900
MAX_PERIOD_YEAR: Final = 2999


class PeriodStatus(enum.StrEnum):
    OPEN = "Open"
    CLOSED = "Closed"


class InvalidPeriod(ValueError):
    """The year and month do not name a period."""


@dataclass(frozen=True, slots=True, order=True)
class AccountingPeriod:
    """The month a voucher's figures belong to.

    Kept apart from the document's date rather than derived from it: an
    adjustment written in January can belong to December, and once a period is
    closed, what decides whether an entry is allowed is the period, not the date
    typed on the paper.
    """

    year: int
    month: int

    def __post_init__(self) -> None:
        if not MIN_PERIOD_YEAR <= self.year <= MAX_PERIOD_YEAR:
            raise InvalidPeriod(
                f"Year {self.year} is outside {MIN_PERIOD_YEAR}-{MAX_PERIOD_YEAR}"
            )
        if not 1 <= self.month <= 12:
            raise InvalidPeriod(f"Month {self.month} is not a month")

    @classmethod
    def of(cls, day: date) -> AccountingPeriod:
        """The period a date falls in, which is the default when none is given."""
        return cls(year=day.year, month=day.month)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"
