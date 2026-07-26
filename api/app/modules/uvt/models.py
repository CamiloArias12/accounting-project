"""The UVT per year, and the record of every attempt to fetch it."""

from __future__ import annotations

import datetime as dt
import enum
from decimal import Decimal

from sqlalchemy import Enum, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin

#: The UVT is a peso amount with two decimals, like every other figure here.
MONEY = Numeric(18, 2)


class UvtSource(enum.StrEnum):
    """Where a stored value came from, which decides whether a fetch may
    overwrite it: a figure typed by a person outranks one a scraper guessed.
    """

    FETCHED = "Fetched"
    MANUAL = "Manual"


class RunStatus(enum.StrEnum):
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    SKIPPED = "Skipped"


class UvtValue(Base, TimestampMixin):
    __tablename__ = "uvt_values"
    __table_args__ = (
        # One row per year, which is what makes a repeated run an update rather
        # than a duplicate.
        UniqueConstraint("year", name="uq_uvt_values_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True)
    value: Mapped[Decimal] = mapped_column(MONEY)

    source: Mapped[UvtSource] = mapped_column(
        Enum(UvtSource, name="uvt_source", native_enum=False, length=20),
        default=UvtSource.FETCHED,
    )
    #: Which provider answered, so a value can be traced back to its origin.
    provider: Mapped[str | None] = mapped_column(String(50), default=None)
    fetched_at: Mapped[dt.datetime | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return f"<UvtValue {self.year} {self.value}>"


class UvtFetchRun(Base, TimestampMixin):
    """One attempt to refresh a year, kept whether it worked or not.

    The failures are the point: a threshold that quietly used last year's UVT
    because a fetch died is exactly what this table exists to make visible.
    """

    __tablename__ = "uvt_fetch_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="uvt_run_status", native_enum=False, length=20),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50))
    attempts: Mapped[int] = mapped_column(default=0)
    value: Mapped[Decimal | None] = mapped_column(MONEY, default=None)
    #: Why it failed, or why it was skipped. Empty on success.
    detail: Mapped[str | None] = mapped_column(String(255), default=None)

    started_at: Mapped[dt.datetime] = mapped_column()
    finished_at: Mapped[dt.datetime] = mapped_column()

    @property
    def duration_ms(self) -> int:
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    def __repr__(self) -> str:
        return f"<UvtFetchRun {self.year} {self.status.value}>"
