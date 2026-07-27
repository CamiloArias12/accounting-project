from __future__ import annotations

import asyncio
import random
import re
from decimal import Decimal
from typing import Final, Protocol

import httpx

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
    """The year is valid but nobody has published a value for it yet."""

    def __init__(self, year: int) -> None:
        super().__init__(
            f"No UVT published for {year}; set it by hand once the DIAN issues it"
        )
        self.year = year


class UvtSourceUnavailable(UvtError):
    """The source failed in a way that might work on the next try."""

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
    """Stands in for the DIAN."""

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
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await provider.fetch(year), attempt
        except UvtNotPublished:
            raise
        except UvtError as exc:
            last = exc
            if attempt < attempts:
                await asyncio.sleep(base_delay_seconds * 2 ** (attempt - 1))

    raise UvtSourceUnavailable(
        f"gave up after {attempts} attempts: {last}", attempts=attempts
    ) from last


DEFAULT_SOURCE_URL: Final = "https://www.gerencie.com/uvt.html"

_YEAR_AND_VALUE: Final = re.compile(r"(20[0-9]{2})\D{1,40}?(\d{2}\.\d{3})")

_PLAUSIBLE_MINIMUM: Final = Decimal("20000")


class HttpUvtProvider:
    """Reads the UVT off a published table."""

    def __init__(
        self,
        *,
        url: str = DEFAULT_SOURCE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._url = url
        self._timeout = timeout_seconds

    @property
    def name(self) -> str:
        return "http"

    async def fetch(self, year: int) -> Decimal:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=True
            ) as client:
                response = await client.get(
                    self._url,
                    headers={"User-Agent": "accounting-project/1.0 (+uvt-sync)"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UvtSourceUnavailable(f"{type(exc).__name__}: {exc}") from exc

        table = parse_uvt_table(response.text)
        value = table.get(year)
        if value is None:
            raise UvtNotPublished(year)

        return value


def parse_uvt_table(html: str) -> dict[int, Decimal]:
    found: dict[int, Decimal] = {}

    for raw_year, raw_value in _YEAR_AND_VALUE.findall(html):
        year = int(raw_year)
        value = Decimal(raw_value.replace(".", ""))

        if value < _PLAUSIBLE_MINIMUM:
            continue
        found.setdefault(year, value)

    return found
