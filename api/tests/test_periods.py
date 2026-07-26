from datetime import date

import pytest
from httpx import AsyncClient

from app.modules.periods.period import AccountingPeriod, InvalidPeriod

BASE = "/api/v1/periods"


def test_the_period_defaults_to_the_month_of_the_date() -> None:
    assert AccountingPeriod.of(date(2026, 7, 26)) == AccountingPeriod(2026, 7)


def test_a_period_can_differ_from_the_date() -> None:
    # An adjustment written in January belonging to December is ordinary.
    assert str(AccountingPeriod(year=2025, month=12)) == "2025-12"


def test_a_month_outside_the_year_is_refused() -> None:
    with pytest.raises(InvalidPeriod, match="is not a month"):
        AccountingPeriod(year=2026, month=13)


def test_a_year_far_outside_the_books_is_refused() -> None:
    with pytest.raises(InvalidPeriod, match="outside"):
        AccountingPeriod(year=202, month=1)


def test_periods_sort_chronologically() -> None:
    assert AccountingPeriod(2025, 12) < AccountingPeriod(2026, 1)


async def test_a_month_nobody_closed_is_open(auth_client: AsyncClient) -> None:
    # Absence means open, which is what lets the books be used from day one.
    read = await auth_client.get(f"{BASE}/2026/7")

    assert read.status_code == 200
    assert read.json()["status"] == "Open"
    assert read.json()["changed_at"] is None


async def test_closing_a_month_records_who_did_it(auth_client: AsyncClient) -> None:
    closed = await auth_client.post(f"{BASE}/2026/7/close")

    assert closed.status_code == 200
    assert closed.json()["status"] == "Closed"
    assert closed.json()["changed_at"] is not None
    assert closed.json()["changed_by_user_id"] is not None


async def test_closing_twice_is_refused(auth_client: AsyncClient) -> None:
    await auth_client.post(f"{BASE}/2026/7/close")

    again = await auth_client.post(f"{BASE}/2026/7/close")

    assert again.status_code == 409
    assert "already closed" in again.json()["detail"]


async def test_reopening_a_closed_month(auth_client: AsyncClient) -> None:
    await auth_client.post(f"{BASE}/2026/7/close")

    reopened = await auth_client.post(f"{BASE}/2026/7/reopen")

    assert reopened.status_code == 200
    assert reopened.json()["status"] == "Open"
    # The row is kept: that a period was closed and reopened is auditable.
    assert reopened.json()["changed_at"] is not None


async def test_reopening_a_month_that_is_already_open_is_refused(
    auth_client: AsyncClient,
) -> None:
    assert (await auth_client.post(f"{BASE}/2026/7/reopen")).status_code == 409


async def test_a_year_lists_twelve_months(auth_client: AsyncClient) -> None:
    await auth_client.post(f"{BASE}/2026/3/close")

    year = await auth_client.get(f"{BASE}/2026")

    body = year.json()
    assert len(body) == 12
    assert [m["month"] for m in body] == list(range(1, 13))
    assert [m["status"] for m in body if m["month"] == 3] == ["Closed"]
    assert [m["status"] for m in body if m["month"] == 4] == ["Open"]


async def test_a_month_that_is_not_a_month_is_refused(
    auth_client: AsyncClient,
) -> None:
    assert (await auth_client.get(f"{BASE}/2026/13")).status_code == 422


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(f"{BASE}/2026/7")).status_code == 401
