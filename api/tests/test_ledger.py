from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_vouchers import a_posted_voucher, a_third_party, seed_chart

BASE = "/api/v1/ledger"
VOUCHERS = "/api/v1/vouchers"


def sale(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "date": "2026-07-10",
        "description": "Venta de contado",
        "lines": [
            {"account_code": "110505", "debit": "150000.00"},
            {"account_code": "220505", "credit": "150000.00", "third_party_id": None},
        ],
    }
    payload.update(overrides)
    return payload


async def seed_chart_without_third_party(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    await auth_client.patch(
        "/api/v1/accounts/220505", json={"requires_third_party": False}
    )


async def test_only_posted_vouchers_reach_the_ledger(auth_client: AsyncClient) -> None:
    await seed_chart_without_third_party(auth_client)
    await auth_client.post(VOUCHERS, json=sale())

    assert (await auth_client.get(BASE)).json()["accounts"] == []

    await a_posted_voucher(auth_client, **sale())

    by_code = {a["code"]: a for a in (await auth_client.get(BASE)).json()["accounts"]}
    assert by_code["110505"]["debit"] == "150000.00"
    assert by_code["110505"]["closing_balance"] == "150000.00"
    assert by_code["220505"]["credit"] == "150000.00"
    assert by_code["220505"]["closing_balance"] == "-150000.00"


async def test_the_report_adds_up_to_zero_and_the_dates_bound_it(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale(date="2026-06-15"))
    await a_posted_voucher(auth_client, **sale())

    totals = (await auth_client.get(BASE)).json()["totals"]
    assert totals["debit"] == "300000.00"
    assert totals["credit"] == "300000.00"
    assert totals["balance"] == "0.00"
    assert totals["is_balanced"] is True

    july = await auth_client.get(
        BASE, params={"date_from": "2026-07-01", "date_to": "2026-07-31"}
    )
    cash = next(a for a in july.json()["accounts"] if a["code"] == "110505")
    assert cash["opening_balance"] == "150000.00"
    assert cash["debit"] == "150000.00"
    assert cash["closing_balance"] == "300000.00"


async def test_the_account_detail_runs_the_balance_and_names_the_third_party(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    supplier = await a_third_party(auth_client, session)
    with_supplier = sale(
        lines=[
            {"account_code": "110505", "debit": "150000.00"},
            {
                "account_code": "220505",
                "credit": "150000.00",
                "third_party_id": supplier,
            },
        ]
    )
    original = await a_posted_voucher(auth_client, **with_supplier)
    await a_posted_voucher(auth_client, **{**with_supplier, "date": "2026-07-20"})

    detail = (await auth_client.get(f"{BASE}/110505")).json()
    assert [e["running_balance"] for e in detail["entries"]] == [
        "150000.00",
        "300000.00",
    ]
    assert detail["nature"] == "Debito"
    first = detail["entries"][0]
    assert first["date"] == "2026-07-10"
    assert first["voucher_number"] == original["number"]
    assert first["description"] == "Venta de contado"
    assert (first["debit"], first["credit"]) == ("150000.00", "0.00")

    named = (await auth_client.get(f"{BASE}/220505")).json()["entries"][0]
    assert named["third_party_id"] == supplier
    assert named["third_party_name"]
    assert detail["entries"][0]["third_party_id"] is None

    theirs = await auth_client.get(
        f"{BASE}/220505", params={"third_party_id": supplier}
    )
    assert theirs.json()["closing_balance"] == "-300000.00"

    await auth_client.post(f"{VOUCHERS}/{original['id']}/reverse", json={})
    after = (await auth_client.get(f"{BASE}/110505")).json()
    assert after["closing_balance"] == "150000.00"
    assert len(after["entries"]) == 3
