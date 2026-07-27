from app.shared.errors import DomainError


class UvtValueNotFound(DomainError):
    """Refusing to guess."""

    def __init__(self, year: int) -> None:
        super().__init__(
            f"No UVT stored for {year}; refresh it from the source or set it "
            "by hand before using a threshold"
        )
        self.year = year
