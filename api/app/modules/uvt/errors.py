"""UVT errors. The web layer maps them to status codes."""

from app.shared.errors import DomainError


class UvtValueNotFound(DomainError):
    """Refusing to guess.

    A threshold in UVT cannot be turned into pesos without the year's value,
    and picking a neighbouring year's would silently move the threshold.
    """

    def __init__(self, year: int) -> None:
        super().__init__(
            f"No UVT stored for {year}; refresh it from the source or set it "
            "by hand before using a threshold"
        )
        self.year = year
