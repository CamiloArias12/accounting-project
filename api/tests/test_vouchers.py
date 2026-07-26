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


async def test_the_period_defaults_to_the_month_of_the_date(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    body = (await auth_client.post(BASE, json=entry())).json()

    assert (body["period_year"], body["period_month"]) == (2026, 7)


async def test_the_period_can_be_set_apart_from_the_date(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    body = (
        await auth_client.post(BASE, json=entry(period_year=2025, period_month=12))
    ).json()

    assert (body["period_year"], body["period_month"]) == (2025, 12)


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


async def test_a_line_cannot_be_both_a_debit_and_a_credit(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    refused = await auth_client.post(
        BASE,
        json=entry(
            lines=[{"account_code": "110505", "debit": "10.00", "credit": "10.00"}]
        ),
    )

    assert refused.status_code == 422


async def test_a_voucher_needs_at_least_two_lines(auth_client: AsyncClient) -> None:
    """Every movement has a counterpart; one line alone is half an operation."""
    await seed_chart(auth_client)

    assert (await auth_client.post(BASE, json=entry(lines=[]))).status_code == 422

    only_one = await auth_client.post(
        BASE, json=entry(lines=[{"account_code": "110505", "debit": "100.00"}])
    )
    assert only_one.status_code == 422
    # Not reported as a 100.00 imbalance, which says nothing about what is
    # missing.
    assert "at least 2 lines" in only_one.json()["detail"]


async def test_posting_to_a_heading_is_refused(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)

    # 1105 has 110505 under it; its balance is the sum of its children.
    refused = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "1105", "debit": "100.00"},
                {"account_code": "110505", "credit": "100.00"},
            ]
        ),
    )

    assert refused.status_code == 422
    assert "heading, not a leaf" in refused.json()["detail"]


async def test_posting_to_an_unknown_account_is_refused(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    refused = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "999999", "debit": "100.00"},
                {"account_code": "110505", "credit": "100.00"},
            ]
        ),
    )

    assert refused.status_code == 422
    assert "does not exist" in refused.json()["detail"]


async def test_an_account_that_requires_a_third_party_gets_one(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    third_party_id = await a_third_party(auth_client, session)

    lines = [
        {"account_code": "110505", "debit": "150000.00"},
        {
            "account_code": "220505",
            "credit": "150000.00",
            "third_party_id": third_party_id,
        },
    ]
    created = await auth_client.post(BASE, json=entry(lines=lines))

    assert created.status_code == 201, created.text
    assert created.json()["lines"][1]["third_party_id"] == third_party_id


async def test_an_account_that_requires_a_third_party_refuses_without_one(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    refused = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {"account_code": "220505", "credit": "150000.00"},
            ]
        ),
    )

    assert refused.status_code == 422
    assert "requires a third party" in refused.json()["detail"]


async def test_a_line_naming_an_unknown_third_party_is_refused(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    refused = await auth_client.post(
        BASE,
        json=entry(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {
                    "account_code": "220505",
                    "credit": "150000.00",
                    "third_party_id": 9999,
                },
            ]
        ),
    )

    assert refused.status_code == 422


async def test_posting_assigns_the_next_consecutive_number(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    first = (await auth_client.post(BASE, json=entry())).json()
    second = (await auth_client.post(BASE, json=entry())).json()

    posted_first = await auth_client.post(f"{BASE}/{first['id']}/post")
    posted_second = await auth_client.post(f"{BASE}/{second['id']}/post")

    assert posted_first.json()["number"] == 1
    assert posted_second.json()["number"] == 2
    assert posted_first.json()["status"] == "Posted"
    assert posted_first.json()["posted_at"] is not None


async def test_a_posted_voucher_cannot_be_changed(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.post(f"{BASE}/{created['id']}/post")

    changed = await auth_client.patch(
        f"{BASE}/{created['id']}", json={"description": "Otra cosa"}
    )

    assert changed.status_code == 409
    assert "reverse it instead" in changed.json()["detail"]


async def test_a_posted_voucher_cannot_be_deleted(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.post(f"{BASE}/{created['id']}/post")

    assert (await auth_client.delete(f"{BASE}/{created['id']}")).status_code == 409


async def test_posting_twice_is_refused(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.post(f"{BASE}/{created['id']}/post")

    again = await auth_client.post(f"{BASE}/{created['id']}/post")

    assert again.status_code == 409
    assert "already posted" in again.json()["detail"]


async def test_a_draft_can_be_changed_and_deleted(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()

    changed = await auth_client.patch(
        f"{BASE}/{created['id']}", json={"description": "Corregido"}
    )
    assert changed.status_code == 200
    assert changed.json()["description"] == "Corregido"

    assert (await auth_client.delete(f"{BASE}/{created['id']}")).status_code == 204
    assert (await auth_client.get(f"{BASE}/{created['id']}")).status_code == 404


async def test_replacing_the_lines_must_still_balance(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()

    refused = await auth_client.patch(
        f"{BASE}/{created['id']}",
        json={"lines": [{"account_code": "110505", "debit": "100.00"}]},
    )

    assert refused.status_code == 422


async def test_lines_keep_the_order_they_were_written_in(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)

    body = (await auth_client.post(BASE, json=entry())).json()

    assert [line["line_number"] for line in body["lines"]] == [1, 2]


async def test_filtering_by_status_and_period(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    draft = (await auth_client.post(BASE, json=entry())).json()
    other = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.post(f"{BASE}/{other['id']}/post")

    drafts = await auth_client.get(BASE, params={"status": "Draft"})
    assert [v["id"] for v in drafts.json()["items"]] == [draft["id"]]

    july = await auth_client.get(BASE, params={"period_year": 2026, "period_month": 7})
    assert july.json()["total"] == 2

    june = await auth_client.get(BASE, params={"period_month": 6})
    assert june.json()["items"] == []


async def test_the_issuing_company_comes_from_configuration(
    auth_client: AsyncClient,
) -> None:
    # There is no company table: one set of books, so it is the same on every
    # voucher and lives in settings.
    company = await auth_client.get(f"{BASE}/company")

    assert company.status_code == 200
    assert company.json()["legal_name"]
    assert company.json()["nit"]


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401


async def test_a_closed_period_refuses_the_posting(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.post("/api/v1/periods/2026/7/close")

    refused = await auth_client.post(f"{BASE}/{created['id']}/post")

    assert refused.status_code == 409
    assert "2026-07 is closed" in refused.json()["detail"]


async def test_a_closed_period_still_takes_drafts(auth_client: AsyncClient) -> None:
    # A draft is not in the books, so it alters nothing; it just cannot be
    # posted while the period stays closed.
    await seed_chart(auth_client)
    await auth_client.post("/api/v1/periods/2026/7/close")

    assert (await auth_client.post(BASE, json=entry())).status_code == 201


async def test_reopening_the_period_lets_the_posting_through(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    created = (await auth_client.post(BASE, json=entry())).json()
    await auth_client.post("/api/v1/periods/2026/7/close")
    await auth_client.post("/api/v1/periods/2026/7/reopen")

    assert (await auth_client.post(f"{BASE}/{created['id']}/post")).status_code == 200


async def test_the_close_follows_the_period_not_the_date(
    auth_client: AsyncClient,
) -> None:
    """An adjustment dated in July but belonging to June follows June."""
    await seed_chart(auth_client)
    created = (
        await auth_client.post(BASE, json=entry(period_year=2026, period_month=6))
    ).json()
    await auth_client.post("/api/v1/periods/2026/6/close")

    refused = await auth_client.post(f"{BASE}/{created['id']}/post")

    assert refused.status_code == 409
    assert "2026-06" in refused.json()["detail"]


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


async def a_posted_voucher(
    auth_client: AsyncClient, **overrides: Any
) -> dict[str, Any]:
    created = (await auth_client.post(BASE, json=entry(**overrides))).json()
    posted = await auth_client.post(f"{BASE}/{created['id']}/post")
    assert posted.status_code == 200, posted.text
    return dict(posted.json())


async def test_reversing_swaps_the_columns(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)

    reversal = await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})

    assert reversal.status_code == 201, reversal.text
    body = reversal.json()
    # Same accounts, columns the other way round.
    assert [(line["debit"], line["credit"]) for line in original["lines"]] == [
        (line["credit"], line["debit"]) for line in body["lines"]
    ]


async def test_the_reversal_is_posted_and_takes_its_own_number(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)

    body = (await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})).json()

    assert body["status"] == "Posted"
    assert body["number"] == original["number"] + 1
    assert body["reverses_voucher_id"] == original["id"]
    assert body["is_reversal"] is True


async def test_the_original_is_left_untouched(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)
    await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})

    after = (await auth_client.get(f"{BASE}/{original['id']}")).json()

    # It keeps its number, its date and its lines; only that it was reversed is
    # new. A gap in the numbering is what deleting it would have left.
    assert after["number"] == original["number"]
    assert after["date"] == original["date"]
    assert after["lines"] == original["lines"]
    assert after["is_reversed"] is True
    assert after["status"] == "Posted"


async def test_the_pair_cancels_out(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)

    reversal = (
        await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})
    ).json()

    # What the ledger will add up: the two together move nothing.
    assert original["total_debit"] == reversal["total_credit"]
    assert original["total_credit"] == reversal["total_debit"]


async def test_a_voucher_cannot_be_reversed_twice(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)
    await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})

    again = await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})

    assert again.status_code == 409
    assert "already reversed" in again.json()["detail"]


async def test_a_reversal_cannot_itself_be_reversed(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)
    reversal = (
        await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})
    ).json()

    undo_the_undo = await auth_client.post(f"{BASE}/{reversal['id']}/reverse", json={})

    assert undo_the_undo.status_code == 409
    assert "itself a reversal" in undo_the_undo.json()["detail"]


async def test_a_draft_cannot_be_reversed(auth_client: AsyncClient) -> None:
    # Nothing to undo: it was never in the books.
    await seed_chart(auth_client)
    draft = (await auth_client.post(BASE, json=entry())).json()

    refused = await auth_client.post(f"{BASE}/{draft['id']}/reverse", json={})

    assert refused.status_code == 409
    assert "edit or discard it" in refused.json()["detail"]


async def test_the_reversal_lands_in_the_original_period(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client, period_year=2026, period_month=6)

    body = (await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})).json()

    # Same period, so the month nets out where the mistake was made.
    assert (body["period_year"], body["period_month"]) == (2026, 6)


async def test_a_closed_period_pushes_the_reversal_to_an_open_one(
    auth_client: AsyncClient,
) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client, period_year=2026, period_month=6)
    await auth_client.post("/api/v1/periods/2026/6/close")

    # Without a date it would go into June, which is now frozen.
    refused = await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})
    assert refused.status_code == 409
    assert "2026-06 is closed" in refused.json()["detail"]

    # With one, it lands in the open period instead — June stays as it closed.
    into_july = await auth_client.post(
        f"{BASE}/{original['id']}/reverse", json={"date": "2026-07-15"}
    )
    assert into_july.status_code == 201
    assert (into_july.json()["period_year"], into_july.json()["period_month"]) == (
        2026,
        7,
    )


async def test_the_reversal_says_what_it_undoes(auth_client: AsyncClient) -> None:
    await seed_chart(auth_client)
    original = await a_posted_voucher(auth_client)

    body = (await auth_client.post(f"{BASE}/{original['id']}/reverse", json={})).json()

    assert body["description"] == f"Reversal of voucher {original['number']}"
