"""Exógena errors. The web layer maps them to status codes."""

from app.shared.errors import DomainError


class GenerationNotFound(DomainError):
    def __init__(self, generation_id: int) -> None:
        super().__init__(f"Generation {generation_id} does not exist")
        self.generation_id = generation_id


class ThresholdNeedsUvt(DomainError):
    """A threshold in UVT is meaningless without the year's UVT.

    Refused rather than defaulted: falling back to a neighbouring year's value
    would move the threshold by thousands of pesos without anybody noticing.
    """

    def __init__(self, year: int) -> None:
        super().__init__(
            f"A threshold in UVT needs the UVT of {year}; refresh it from the "
            "source or set it by hand, or ask for a threshold of 0"
        )
        self.year = year
