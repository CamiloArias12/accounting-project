"""Pydantic at the edge: what an accounting period looks like over HTTP."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.modules.periods.period import (
    MAX_PERIOD_YEAR,
    MIN_PERIOD_YEAR,
    PeriodStatus,
)


class PeriodRead(BaseModel):
    """A month and whether it accepts entries.

    Reported for any month asked about, closed or not: only closed periods are
    stored, so an open one has no row to read `changed_at` off.
    """

    year: int = Field(ge=MIN_PERIOD_YEAR, le=MAX_PERIOD_YEAR)
    month: int = Field(ge=1, le=12)
    status: PeriodStatus
    changed_at: dt.datetime | None = None
    changed_by_user_id: int | None = None

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"
