from httpx import AsyncClient

from app.shared.pagination import DEFAULT_LIMIT, MAX_LIMIT

ACCOUNTS = "/api/v1/accounts"


async def test_every_list_is_paged_and_says_how_much_it_left_out(
    auth_client: AsyncClient,
) -> None:
    await auth_client.post(
        ACCOUNTS, json={"code": "1", "name": "ACTIVOS", "nature": "Debito"}
    )
    for number in range(1, 6):
        created = await auth_client.post(
            ACCOUNTS,
            json={"code": f"1{number}", "name": f"GRUPO {number}", "nature": "Debito"},
        )
        assert created.status_code == 201, created.text

    # The one number a bare array cannot express: whether this is everything.
    page = (await auth_client.get(ACCOUNTS, params={"limit": 2})).json()
    assert len(page["items"]) == 2
    assert page["total"] == 6
    assert (page["skip"], page["limit"]) == (0, 2)

    # Not the whole table: a pager over a filtered list needs the filtered
    # count, or its last page comes back empty.
    filtered = (
        await auth_client.get(ACCOUNTS, params={"search": "GRUPO 3", "limit": 1})
    ).json()
    assert filtered["total"] == 1

    # 2.446 accounts must not arrive in one response by accident.
    assert (await auth_client.get(ACCOUNTS)).json()["limit"] == DEFAULT_LIMIT
    too_much = await auth_client.get(ACCOUNTS, params={"limit": MAX_LIMIT + 1})
    assert too_much.status_code == 422

    for path in (ACCOUNTS, "/api/v1/third-parties", "/api/v1/vouchers"):
        body = (await auth_client.get(path)).json()
        assert set(body) >= {"items", "total", "skip", "limit"}, path
