from datetime import UTC, datetime


class SystemClock:
    """Real time. Stored naive to match the other timestamp columns."""

    def now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)
