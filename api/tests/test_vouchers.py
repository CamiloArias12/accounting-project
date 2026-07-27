from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_third_parties_api import natural_payload, seed_places

BASE = "/api/v1/vouchers"
ACCOUNTS = "/api/v1/accounts"


async def seed_chart(auth_client: AsyncClient) -> None:
    """A branch down to two postable leaves, one of which wants a third party.

    1 > 11 > 1105 > 110505  CAJA GENERAL          (no third party)
    2 > 22 > 2205 > 220505  PROVEEDORES NACIONALES (third party required)
    """
    branch: list[dict[str, Any]] = [
        {"code": "1", "name": "ACTIVOS", "nature": "Debito"},
        {"code": "11", "name": "DISPONIBLE", "nature": "Debito"},
        {"code": "1105", "name": "CAJA", "nature": "Debito"},
        {"code": "110505", "name": "CAJA GENERAL", "nature": "Debito"},
        {"code": "2", "name": "PASIVOS", "nature": "Crédito"},
        {"code": "22", "name": "PROVEEDORES", "nature": "Crédito"},
        {"code": "2205", "name": "NACIONALES", "nature": "Crédito"},
        {
            "code": "220505",
            "name": "PROVEEDORES NACIONALES",
            "nature": "Crédito",
            "requires_third_party": True,
        },
    ]
    for payload in branch:
        response = await auth_client.post(ACCOUNTS, json=payload)
        assert response.status_code == 201, response.text


async def a_third_party(auth_client: AsyncClient, session: AsyncSession) -> int:
    places = await seed_places(session)
    created = await auth_client.post(
        "/api/v1/third-parties", json=natural_payload(places)
    )
    assert created.status_code == 201, created.text
    return int(created.json()["id"])


def entry(**overrides: Any) -> dict[str, Any]:
    """A balanced two-line voucher: cash in, payable down."""
    payload: dict[str, Any] = {
        "date": "2026-07-26",
        "description": "Pago a proveedor",
        "lines": [
            {"account_code": "110505", "credit": "150000.00"},
            {"account_code": "110505", "debit": "150000.00"},
        ],
    }
    payload.update(overrides)
    return payload


async def a_posted_voucher(
    auth_client: AsyncClient, **overrides: Any
) -> dict[str, Any]:
    created = (await auth_client.post(BASE, json=entry(**overrides))).json()
    posted = await auth_client.post(f"{BASE}/{created['id']}/post")
    assert posted.status_code == 200, posted.text
    return dict(posted.json())


async def test_writing_a_draft(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)

    created = await auth_client.post(BASE, json=entry())

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "Draft"
    # A draft takes no consecutive number: the series must have no gaps.
    assert body["number"] is None
    assert body["total_debit"] == "150000.00"
    assert body["is_balanced"] is True
    # The period follows the date unless it is given.
    assert (body["period_year"], body["period_month"]) == (2026, 7)


async def test_an_entry_that_does_not_balance_is_refused(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    refused = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "110505", "debit": "100000.00"},
                {"account_code": "110505", "credit": "30000.00"},
            ]
        ),
    )

    assert refused.status_code == 422
    assert "off by 70000.00" in refused.json()["detail"]

    # And the same rule holds when the lines are replaced on a draft.
    draft = (await auth_client.post(BASE, json=entry())).json()
    patched = await auth_client.patch(
        f"{BASE}/{draft['id']}",
        json={"lines": [{"account_code": "110505", "debit": "100.00"}]},
    )
    assert patched.status_code == 422


async def test_a_line_names_a_leaf_and_its_third_party(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)

    # 1105 has 110505 under it; its balance is the sum of its children.
    heading = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "1105", "debit": "100.00"},
                {"account_code": "110505", "credit": "100.00"},
            ]
        ),
    )
    assert heading.status_code == 422
    assert "heading, not a leaf" in heading.json()["detail"]

    anonymous = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {"account_code": "220505", "credit": "150000.00"},
            ]
        ),
    )
    assert anonymous.status_code == 422
    assert "requires a third party" in anonymous.json()["detail"]

    third_party_id = await a_third_party(auth_client, session)
    named = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {
                    "account_code": "220505",
                    "credit": "150000.00",
                    "third_party_id": third_party_id,
                },
            ]
        ),
    )
    assert named.status_code == 201, named.text
    assert named.json()["lines"][1]["third_party_id"] == third_party_id


async def test_posting_numbers_the_voucher_and_freezes_it(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    first = (await auth_client.post(BASE, json=entry())).json()
    second = (await auth_client.post(BASE, json=entry())).json()

    posted = await auth_client.post(f"{BASE}/{first['id']}/post")
    assert posted.json()["number"] == 1
    assert posted.json()["status"] == "Posted"
    assert posted.json()["posted_at"] is not None
    assert (await auth_client.post(f"{BASE}/{second['id']}/post")).json()["number"] == 2

    # An accounting record, not a document somebody is still writing.
    changed = await auth_client.patch(
        f"{BASE}/{first['id']}", json={"description": "Otra cosa"}
    )
    assert changed.status_code == 409
    assert "reverse it instead" in changed.json()["detail"]
    assert (await auth_client.delete(f"{BASE}/{first['id']}")).status_code == 409
    assert (await auth_client.post(f"{BASE}/{first['id']}/post")).status_code == 409

    # A draft is the opposite: editable and disposable.
    draft = (await auth_client.post(BASE, json=entry())).json()
    assert (await auth_client.delete(f"{BASE}/{draft['id']}")).status_code == 204


async def test_a_closed_period_refuses_the_posting_but_still_takes_drafts(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    # Dated in July, belonging to June: the close follows the period, not the
    # date on the paper.
    created = (
        await auth_client.post(BASE, json=entry(period_year=2026, period_month=6))
    ).json()
    await auth_client.post("/api/v1/periods/2026/6/close")

    refused = await auth_client.post(f"{BASE}/{created['id']}/post")
    assert refused.status_code == 409
    assert "2026-06 is closed" in refused.json()["detail"]

    # A draft alters nothing, so it is still allowed in.
    draft = await auth_client.post(
        BASE, json=entry(period_year=2026, period_month=6)
    )
    assert draft.status_code == 201

    await auth_client.post("/api/v1/periods/2026/6/reopen")
    assert (await auth_client.post(f"{BASE}/{created['id']}/post")).status_code == 200


async def test_an_account_deactivated_after_the_draft_blocks_the_posting(
    auth_client: AsyncClient,
) -> None:
    # The gap this closes: the chart is checked when the lines are written, and
    # a draft can sit for days before anyone posts it.
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.patch(f"{ACCOUNTS}/110505", json={"is_active": False})

    refused = await auth_client.post(f"{BASE}/{created['id']}/post")

    assert refused.status_code == 422
    assert "inactive" in refused.json()["detail"]


async def test_reversing_swaps_the_columns_and_leaves_the_original(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client, period_year=2026, period_month=6)

    reversal = await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})

    assert reversal.status_code == 201, reversal.text
    body = reversal.json()
    # Same accounts, columns the other way round.
    assert [(line["debit"], line["credit"]) for line in original["lines"]] == [
        (line["credit"], line["debit"]) for line in body["lines"]
    ]
    # Posted in the same operation and in the same period, so the month nets
    # out where the mistake was made.
    assert body["status"] == "Posted"
    assert body["number"] == original["number"] + 1
    assert body["reverses_voucher_id"] == original["id"]
    assert (body["period_year"], body["period_month"]) == (2026, 6)

    after = (await auth_client.get(f"{BASE}/{original['id']}")).json()
    # It keeps its number, its date and its lines; only that it was reversed is
    # new. A gap in the numbering is what deleting it would have left.
    assert after["number"] == original["number"]
    assert after["lines"] == original["lines"]
    assert after["is_reversed"] is True
    assert after["status"] == "Posted"


async def test_what_cannot_be_reversed(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)
    reversal = (
        await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})
    ).json()

    twice = await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})
    assert twice.status_code == 409
    assert "already reversed" in twice.json()["detail"]

    undo_the_undo = await auth_client.post(f"{BASE}/{reversal['id']}/reverse", json={})
    assert undo_the_undo.status_code == 409
    assert "itself a reversal" in undo_the_undo.json()["detail"]

    # A draft was never in the books: there is nothing to undo.
    draft = (await auth_client.post(BASE, json=entry())).json()
    nothing_to_undo = await auth_client.post(f"{BASE}/{draft['id']}/reverse", json={})
    assert nothing_to_undo.status_code == 409
    assert "edit or discard it" in nothing_to_undo.json()["detail"]
