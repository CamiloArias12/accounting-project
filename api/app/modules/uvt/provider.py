"""Where the UVT comes from.

The UVT (unidad de valor tributario) is republished by the DIAN every year and
is what turns a threshold expressed in UVT into pesos. It is not ours to
compute — it has to be fetched.

The port is a protocol with one method, so the simulated provider and a real
HTTP one are interchangeable and the service never learns which it got.

Nothing here touches the database or FastAPI.
"""

from __future__ import annotations

import asyncio
import random
from decimal import Decimal
from typing import Final, Protocol

#: Values published by the DIAN. They are hardcoded rather than guessed for
#: years that have not been published: inventing a UVT would silently move
#: every threshold that depends on it.
PUBLISHED: Final[dict[int, Decimal]] = {
    2021: Decimal("36308"),
    2022: Decimal("38004"),
    2023: Decimal("42412"),
    2024: Decimal("47065"),
    2025: Decimal("49799"),
}

MIN_YEAR: Final = 2000
MAX_YEAR: Final = 2999


class UvtError(Exception):
    """The value could not be obtained."""


class UvtNotPublished(UvtError):
    """The year is valid but nobody has published a value for it yet.

    Not a transient failure: retrying will not make the DIAN publish sooner, so
    the caller is told to set it by hand instead.
    """

    def __init__(self, year: int) -> None:
        super().__init__(
            f"No UVT published for {year}; set it by hand once the DIAN issues it"
        )
        self.year = year


class UvtSourceUnavailable(UvtError):
    """The source failed in a way that might work on the next try.

    Carries how many attempts were spent, so the run record can say three
    rather than leaving the count to be read out of the message.
    """

    def __init__(self, detail: str, *, attempts: int = 1) -> None:
        super().__init__(f"The UVT source is unavailable: {detail}")
        self.detail = detail
        self.attempts = attempts


class UvtProvider(Protocol):
    """One method, so a simulated source and a real one are interchangeable."""

    @property
    def name(self) -> str: ...

    async def fetch(self, year: int) -> Decimal: ...


class SimulatedUvtProvider:
    """Stands in for the DIAN.

    A real integration would scrape or call an API. This one answers from the
    published table and fails at a configurable rate, because what the code has
    to get right is the failure — the retry, the fact that a repeated run does
    not duplicate anything, and the record of what happened. A source that
    always answers exercises none of it.
    """

    def __init__(
        self,
        *,
        failure_rate: float = 0.0,
        latency_seconds: float = 0.0,
        seed: int | None = None,
    ) -> None:
        self._failure_rate = failure_rate
        self._latency = latency_seconds
        self._random = random.Random(seed)

    @property
    def name(self) -> str:
        return "simulated"

    async def fetch(self, year: int) -> Decimal:
        if self._latency:
            await asyncio.sleep(self._latency)

        if self._random.random() < self._failure_rate:
            raise UvtSourceUnavailable("the simulated source timed out")

        value = PUBLISHED.get(year)
        if value is None:
            raise UvtNotPublished(year)

        return value


async def fetch_with_retry(
    provider: UvtProvider,
    year: int,
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.2,
) -> tuple[Decimal, int]:
    """Fetch, retrying only what is worth retrying.

    A source that timed out may answer next time; a year the DIAN has not
    published will not appear because we asked again, so `UvtNotPublished`
    stops the loop at once.

    Returns the value and how many attempts it took, which is what the run
    record reports.
    """
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await provider.fetch(year), attempt
        except UvtNotPublished:
            raise
        except UvtError as exc:
            last = exc
            if attempt < attempts:
                # Backing off, so a source that is merely busy is not hammered.
                await asyncio.sleep(base_delay_seconds * 2 ** (attempt - 1))

    raise UvtSourceUnavailable(
        f"gave up after {attempts} attempts: {last}", attempts=attempts
    ) from last
