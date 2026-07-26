from typing import Any

import pytest
from httpx import AsyncClient

from app.shared.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page

ACCOUNTS = "/api/v1/accounts"


async def seed_accounts(auth_client: AsyncClient, how_many: int) -> None:
    """A class with `how_many` groups under it, so there is something to page."""
    await auth_client.post(
        ACCOUNTS, json={"code": "1", "name": "ACTIVOS", "nature": "Debito"}
    )
    for number in range(10, 10 + how_many):
        response = await auth_client.post(
            ACCOUNTS,
            json={
                "code": f"1{number - 9}",
                "name": f"GRUPO {number}",
                "nature": "Debito",
            },
        )
        assert response.status_code == 201, response.text


def test_has_more_compares_against_the_total() -> None:
    page: Page[Any] = Page(items=[1, 2], total=10, skip=0, limit=2)
    assert page.has_more

    last: Page[Any] = Page(items=[9, 10], total=10, skip=8, limit=2)
    assert not last.has_more


def test_a_page_cannot_claim_a_negative_total() -> None:
    with pytest.raises(ValueError):
        Page(items=[], total=-1, skip=0, limit=10)


async def test_the_envelope_carries_the_total_not_the_page_size(
    auth_client: AsyncClient,
) -> None:
    # The one number a bare array cannot express: whether this is everything.
    await seed_accounts(auth_client, 5)

    first = await auth_client.get(ACCOUNTS, params={"limit": 2})

    body = first.json()
    assert len(body["items"]) == 2
    assert body["total"] == 6
    assert (body["skip"], body["limit"]) == (0, 2)


async def test_paging_walks_the_whole_list_without_repeating(
    auth_client: AsyncClient,
) -> None:
    await seed_accounts(auth_client, 5)

    seen: list[str] = []
    skip = 0
    while True:
        body = (
            await auth_client.get(ACCOUNTS, params={"skip": skip, "limit": 2})
        ).json()
        seen.extend(a["code"] for a in body["items"])
        skip += 2
        if skip >= body["total"]:
            break

    assert len(seen) == 6
    assert len(set(seen)) == 6


async def test_the_total_counts_what_the_filters_match(
    auth_client: AsyncClient,
) -> None:
    # Not the whole table: a pager over a filtered list needs the filtered
    # count, or the last page comes back empty.
    await seed_accounts(auth_client, 5)

    filtered = await auth_client.get(
        ACCOUNTS, params={"search": "GRUPO 12", "limit": 1}
    )

    body = filtered.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


async def test_a_page_past_the_end_is_empty_rather_than_an_error(
    auth_client: AsyncClient,
) -> None:
    await seed_accounts(auth_client, 2)

    body = (await auth_client.get(ACCOUNTS, params={"skip": 500})).json()

    assert body["items"] == []
    assert body["total"] == 3


async def test_the_default_and_the_ceiling_are_enforced(
    auth_client: AsyncClient,
) -> None:
    # 2,449 accounts must not arrive in one response by accident.
    default = (await auth_client.get(ACCOUNTS)).json()
    assert default["limit"] == DEFAULT_LIMIT

    too_much = await auth_client.get(ACCOUNTS, params={"limit": MAX_LIMIT + 1})
    assert too_much.status_code == 422


async def test_every_list_endpoint_is_paged(auth_client: AsyncClient) -> None:
    for path in (ACCOUNTS, "/api/v1/third-parties", "/api/v1/vouchers"):
        body = (await auth_client.get(path)).json()
        assert set(body) >= {"items", "total", "skip", "limit"}, path
