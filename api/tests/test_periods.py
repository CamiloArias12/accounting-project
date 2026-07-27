from httpx import AsyncClient

BASE = "/api/v1/periods"


async def test_a_month_nobody_closed_is_open(auth_client: AsyncClient) -> None:
    read = await auth_client.get(f"{BASE}/2026/7")

    assert read.status_code == 200
    assert read.json()["status"] == "Open"
    assert read.json()["changed_at"] is None

    year = await auth_client.get(f"{BASE}/2026")
    assert [m["month"] for m in year.json()] == list(range(1, 13))
    assert {m["status"] for m in year.json()} == {"Open"}


async def test_closing_records_who_did_it_and_can_be_undone(
    auth_client: AsyncClient,
) -> None:
    closed = await auth_client.post(f"{BASE}/2026/7/close")

    assert closed.status_code == 200
    assert closed.json()["status"] == "Closed"
    assert closed.json()["changed_at"] is not None
    assert closed.json()["changed_by_user_id"] is not None

    again = await auth_client.post(f"{BASE}/2026/7/close")
    assert again.status_code == 409
    assert "already closed" in again.json()["detail"]

    reopened = await auth_client.post(f"{BASE}/2026/7/reopen")
    assert reopened.json()["status"] == "Open"
    assert reopened.json()["changed_at"] is not None
