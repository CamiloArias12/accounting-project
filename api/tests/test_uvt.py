from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.uvt.models import RunStatus
from app.modules.uvt.provider import (
    PUBLISHED,
    SimulatedUvtProvider,
    UvtNotPublished,
    UvtSourceUnavailable,
    fetch_with_retry,
    parse_uvt_table,
)
from app.modules.uvt.service import UvtService


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


async def test_a_transient_failure_is_retried_and_a_dead_source_gives_up() -> None:
    value, attempts = await fetch_with_retry(FlakyOnce(), 2025, base_delay_seconds=0)
    assert value == Decimal("49799")
    assert attempts == 2

    down = AlwaysDown()
    with pytest.raises(UvtSourceUnavailable, match="gave up after 3"):
        await fetch_with_retry(down, 2025, base_delay_seconds=0)
    assert down.calls == 3

    with pytest.raises(UvtNotPublished):
        await fetch_with_retry(SimulatedUvtProvider(), 2099, base_delay_seconds=0)


async def test_a_refresh_records_every_run_and_never_duplicates_a_year(
    session: AsyncSession,
) -> None:
    service = UvtService(session)

    run = await service.refresh(2025, SimulatedUvtProvider())
    assert run.status is RunStatus.SUCCEEDED
    assert await service.value_for(2025) == PUBLISHED[2025]

    await service.refresh(2025, SimulatedUvtProvider())
    assert len([v for v in await service.all_values() if v.year == 2025]) == 1
    assert len(await service.runs()) == 2

    failed = await UvtService(session).refresh(2099, AlwaysDown())
    assert failed.status is RunStatus.FAILED
    assert failed.attempts == 3
    assert "gave up" in (failed.detail or "")
    assert [v.year for v in await service.all_values()] == [2025]

    await service.set_manually(2025, Decimal("12345.00"))
    skipped = await service.refresh(2025, SimulatedUvtProvider())
    assert skipped.status is RunStatus.SKIPPED
    assert await service.value_for(2025) == Decimal("12345.00")


PAGE = """
<h2>Valor de la UVT</h2>
<table>
  <tr><td>2026</td><td>52.374</td></tr>
  <tr><td>2025</td><td>49.799</td></tr>
</table>
<p>La UVT para 2026 quedó en 52.374 pesos.</p>
"""


def test_the_parser_reads_the_published_table() -> None:
    table = parse_uvt_table(PAGE)

    assert table == {2026: Decimal("52374"), 2025: Decimal("49799")}

    assert parse_uvt_table("<td>2025</td><td>12.500</td>") == {}
