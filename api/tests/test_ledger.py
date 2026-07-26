from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_vouchers import a_posted_voucher, a_third_party, seed_chart

BASE = "/api/v1/ledger"
VOUCHERS = "/api/v1/vouchers"


def sale(**overrides: Any) -> dict[str, Any]:
    """Cash in, payable down: 110505 debit, 220505 credit."""
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
    """The same chart, but with 220505 not demanding a third party."""
    await seed_chart(auth_client)
    await auth_client.patch(
        "/api/v1/accounts/220505", json={"requires_third_party": False}
    )


async def test_a_draft_does_not_reach_the_ledger(auth_client: AsyncClient) -> None:
    await seed_chart_without_third_party(auth_client)
    await auth_client.post(VOUCHERS, json=sale())

    report = await auth_client.get(BASE)

    # Balances must not move while somebody is still typing.
    assert report.json()["accounts"] == []


async def test_a_posted_voucher_reaches_the_ledger(auth_client: AsyncClient) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    accounts = (await auth_client.get(BASE)).json()["accounts"]

    by_code = {a["code"]: a for a in accounts}
    assert by_code["110505"]["debit"] == "150000.00"
    assert by_code["110505"]["closing_balance"] == "150000.00"
    # Signed: a credit balance comes back negative, which is what makes the
    # whole report add up to zero.
    assert by_code["220505"]["credit"] == "150000.00"
    assert by_code["220505"]["closing_balance"] == "-150000.00"


async def test_the_whole_report_adds_up_to_zero(auth_client: AsyncClient) -> None:
    # The one check that covers every voucher behind it at once.
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())
    await a_posted_voucher(auth_client, **sale(date="2026-07-20"))

    totals = (await auth_client.get(BASE)).json()["totals"]

    assert totals["debit"] == "300000.00"
    assert totals["credit"] == "300000.00"
    assert totals["balance"] == "0.00"
    assert totals["is_balanced"] is True


async def test_a_reversal_puts_the_balance_back(auth_client: AsyncClient) -> None:
    """What the reversal is for, measured on the books rather than asserted."""
    await seed_chart_without_third_party(auth_client)
    original = await a_posted_voucher(auth_client, **sale())

    before = (await auth_client.get(f"{BASE}/110505")).json()["closing_balance"]
    assert before == "150000.00"

    await auth_client.post(f"{VOUCHERS}/{original['id']}/reverse", json={})

    after = (await auth_client.get(f"{BASE}/110505")).json()
    assert after["closing_balance"] == "0.00"
    # And both entries are still there: the mistake and its correction.
    assert len(after["entries"]) == 2
    assert after["entries"][1]["reverses_voucher_id"] == original["id"]


async def test_the_ledger_is_bounded_by_dates(auth_client: AsyncClient) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale(date="2026-06-15"))
    await a_posted_voucher(auth_client, **sale(date="2026-07-10"))

    july = await auth_client.get(
        BASE, params={"date_from": "2026-07-01", "date_to": "2026-07-31"}
    )

    cash = next(a for a in july.json()["accounts"] if a["code"] == "110505")
    # June is not movement of July, it is what July started with.
    assert cash["opening_balance"] == "150000.00"
    assert cash["debit"] == "150000.00"
    assert cash["closing_balance"] == "300000.00"


async def test_the_account_detail_carries_a_running_balance(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())
    await a_posted_voucher(auth_client, **sale(date="2026-07-20"))

    detail = (await auth_client.get(f"{BASE}/110505")).json()

    assert [e["running_balance"] for e in detail["entries"]] == [
        "150000.00",
        "300000.00",
    ]
    assert detail["closing_balance"] == "300000.00"
    assert detail["nature"] == "Debito"


async def test_the_detail_falls_back_to_the_voucher_description(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    detail = (await auth_client.get(f"{BASE}/110505")).json()

    assert detail["entries"][0]["description"] == "Venta de contado"


async def test_a_branch_of_the_chart_can_be_asked_for_on_its_own(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    assets = await auth_client.get(BASE, params={"account_code": "11"})

    assert [a["code"] for a in assets.json()["accounts"]] == ["110505"]
    # One branch on its own does not balance, and should not pretend to.
    assert assets.json()["totals"]["is_balanced"] is False


async def test_the_ledger_can_be_read_for_one_third_party(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    """A payable is worth reading per third party: who is owed what."""
    await seed_chart(auth_client)
    supplier = await a_third_party(auth_client, session)

    await a_posted_voucher(
        auth_client,
        **sale(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {
                    "account_code": "220505",
                    "credit": "150000.00",
                    "third_party_id": supplier,
                },
            ]
        ),
    )

    theirs = await auth_client.get(
        f"{BASE}/220505", params={"third_party_id": supplier}
    )
    assert theirs.json()["closing_balance"] == "-150000.00"

    somebody_else = await auth_client.get(
        f"{BASE}/220505", params={"third_party_id": supplier + 999}
    )
    assert somebody_else.json()["entries"] == []
    assert somebody_else.json()["closing_balance"] == "0"


async def test_an_unknown_account_is_refused(auth_client: AsyncClient) -> None:
    assert (await auth_client.get(f"{BASE}/999999")).status_code == 422


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401
