from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.uvt.models import RunStatus, UvtSource
from app.modules.uvt.provider import (
    PUBLISHED,
    SimulatedUvtProvider,
    UvtNotPublished,
    UvtSourceUnavailable,
    fetch_with_retry,
)
from app.modules.uvt.service import UvtService

BASE = "/api/v1/uvt"


class AlwaysDown:
    """A source that never answers, to exercise the retry and the give-up."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "always-down"

    async def fetch(self, year: int) -> Decimal:
        self.calls += 1
        raise UvtSourceUnavailable("down")


class FlakyOnce:
    """Fails the first time and answers the second, like a real timeout."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def name(self) -> str:
        return "flaky"

    async def fetch(self, year: int) -> Decimal:
        self.calls += 1
        if self.calls == 1:
            raise UvtSourceUnavailable("first call timed out")
        return Decimal("49799")


async def test_a_published_year_comes_back() -> None:
    provider = SimulatedUvtProvider()
    assert await provider.fetch(2025) == PUBLISHED[2025]


async def test_an_unpublished_year_is_not_invented() -> None:
    with pytest.raises(UvtNotPublished):
        await SimulatedUvtProvider().fetch(2099)


async def test_a_transient_failure_is_retried() -> None:
    provider = FlakyOnce()

    value, attempts = await fetch_with_retry(provider, 2025, base_delay_seconds=0)

    assert value == Decimal("49799")
    assert attempts == 2


async def test_the_retry_gives_up_and_says_so() -> None:
    provider = AlwaysDown()

    with pytest.raises(UvtSourceUnavailable, match="gave up after 3"):
        await fetch_with_retry(provider, 2025, base_delay_seconds=0)

    assert provider.calls == 3


async def test_an_unpublished_year_is_not_retried() -> None:
    # Asking again will not make the DIAN publish sooner.
    provider = SimulatedUvtProvider()

    with pytest.raises(UvtNotPublished):
        await fetch_with_retry(provider, 2099, base_delay_seconds=0)


async def test_a_refresh_stores_the_value_and_records_the_run(
    session: AsyncSession,
) -> None:
    service = UvtService(session)

    run = await service.refresh(2025, SimulatedUvtProvider())

    assert run.status is RunStatus.SUCCEEDED
    assert run.value == PUBLISHED[2025]
    assert await service.value_for(2025) == PUBLISHED[2025]


async def test_running_twice_updates_rather_than_duplicates(
    session: AsyncSession,
) -> None:
    # What makes a nightly job safe: the year is unique, so the second run
    # writes over the first instead of adding another row.
    service = UvtService(session)
    await service.refresh(2025, SimulatedUvtProvider())
    await service.refresh(2025, SimulatedUvtProvider())

    values = [v for v in await service.all_values() if v.year == 2025]
    assert len(values) == 1
    assert len(await service.runs()) == 2


async def test_a_failure_is_recorded_and_nothing_is_stored(
    session: AsyncSession,
) -> None:
    service = UvtService(session)

    run = await service.refresh(2025, AlwaysDown())

    assert run.status is RunStatus.FAILED
    assert "gave up" in (run.detail or "")
    assert await service.all_values() == []


async def test_an_unpublished_year_is_skipped_not_failed(
    session: AsyncSession,
) -> None:
    run = await UvtService(session).refresh(2099, SimulatedUvtProvider())

    assert run.status is RunStatus.SKIPPED
    assert "set it by hand" in (run.detail or "")


async def test_a_manual_value_is_not_overwritten_by_a_fetch(
    session: AsyncSession,
) -> None:
    # A figure read off the resolution outranks whatever a scraper makes of it.
    service = UvtService(session)
    await service.set_manually(2025, Decimal("12345.00"))

    run = await service.refresh(2025, SimulatedUvtProvider())

    assert run.status is RunStatus.SKIPPED
    assert await service.value_for(2025) == Decimal("12345.00")


async def test_the_refresh_endpoint_answers_before_the_work(
    auth_client: AsyncClient,
) -> None:
    # 202, not 200: three attempts with backoff is not something a caller
    # should hold a connection open for.
    accepted = await auth_client.post(f"{BASE}/refresh", json={"year": 2025})

    assert accepted.status_code == 202
    assert accepted.json() == {"year": 2025, "accepted": True}


async def test_setting_and_reading_a_value(auth_client: AsyncClient) -> None:
    stored = await auth_client.put(f"{BASE}/2026", json={"value": "51000.00"})
    assert stored.status_code == 200
    assert stored.json()["source"] == UvtSource.MANUAL.value

    read = await auth_client.get(f"{BASE}/2026")
    assert read.json()["value"] == "51000.00"


async def test_a_year_with_no_value_is_refused_not_guessed(
    auth_client: AsyncClient,
) -> None:
    missing = await auth_client.get(f"{BASE}/2019")

    assert missing.status_code == 404
    assert "refresh it from the source" in missing.json()["detail"]


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401


async def test_a_failed_run_records_the_attempts_it_spent(
    session: AsyncSession,
) -> None:
    # The count is the point of keeping failures: a run that says zero
    # attempts reads as if it never tried.
    run = await UvtService(session).refresh(2025, AlwaysDown())

    assert run.status is RunStatus.FAILED
    assert run.attempts == 3
