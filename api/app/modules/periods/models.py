from __future__ import annotations

import datetime as dt

from sqlalchemy import CheckConstraint, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.periods.period import AccountingPeriod, PeriodStatus
from app.shared.database import Base, TimestampMixin


class Period(Base, TimestampMixin):
    """The stored state of an accounting period."""
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_accounting_periods_month"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_accounting_periods_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True)
    month: Mapped[int] = mapped_column()

    status: Mapped[PeriodStatus] = mapped_column(
        Enum(PeriodStatus, name="period_status", native_enum=False, length=20),
        default=PeriodStatus.CLOSED,
        index=True,
    )

    changed_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), default=None
    )

    @classmethod
    def closed(cls, period: AccountingPeriod, *, user_id: int | None = None) -> Period:
        return cls(
            year=period.year,
            month=period.month,
            status=PeriodStatus.CLOSED,
            changed_at=_now(),
            changed_by_user_id=user_id,
        )

    @property
    def key(self) -> AccountingPeriod:
        return AccountingPeriod(year=self.year, month=self.month)

    @property
    def is_closed(self) -> bool:
        return self.status is PeriodStatus.CLOSED

    def close(self, *, user_id: int | None = None) -> None:
        self.status = PeriodStatus.CLOSED
        self.changed_at = _now()
        self.changed_by_user_id = user_id

    def reopen(self, *, user_id: int | None = None) -> None:
        self.status = PeriodStatus.OPEN
        self.changed_at = _now()
        self.changed_by_user_id = user_id

    def __repr__(self) -> str:
        return f"<Period {self.key} {self.status.value}>"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)
