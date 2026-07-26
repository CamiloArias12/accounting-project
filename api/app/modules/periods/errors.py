"""Accounting period errors. The web layer maps them to status codes."""

from app.shared.errors import DomainError


class PeriodClosed(DomainError):
    """Nothing may be added to a period once it is closed.

    Checked against the voucher's period, never against the date on the
    document: the two can differ, and it is the period that the figures belong
    to.
    """

    def __init__(self, period: str) -> None:
        super().__init__(f"Period {period} is closed; no voucher can be posted into it")
        self.period = period


class PeriodAlreadyClosed(DomainError):
    def __init__(self, period: str) -> None:
        super().__init__(f"Period {period} is already closed")
        self.period = period


class PeriodAlreadyOpen(DomainError):
    def __init__(self, period: str) -> None:
        super().__init__(f"Period {period} is already open")
        self.period = period
