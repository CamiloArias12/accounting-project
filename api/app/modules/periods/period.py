from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from typing import Final

MIN_PERIOD_YEAR: Final = 1900
MAX_PERIOD_YEAR: Final = 2999


class PeriodStatus(enum.StrEnum):
    """What an accounting period is, and when it accepts entries."""
    OPEN = "Open"
    CLOSED = "Closed"


class InvalidPeriod(ValueError):
    """The year and month do not name a period."""


@dataclass(frozen=True, slots=True, order=True)
class AccountingPeriod:
    """The month a voucher's figures belong to."""

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
        return cls(year=day.year, month=day.month)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"
