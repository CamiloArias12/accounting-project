from httpx import AsyncClient

from tests.test_accounts import CLASS_, SUBACCOUNT, seed_branch


async def test_delete_stamps_deleted_at_and_keeps_the_row(client: AsyncClient) -> None:
    await seed_branch(client)

    deleted = await client.delete("/api/v1/accounts/110505")

    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None

    # Gone from the normal view, still there when asked for explicitly.
    assert (await client.get("/api/v1/accounts/110505")).status_code == 404
    kept = await client.get("/api/v1/accounts/110505", params={"include_deleted": True})
    assert kept.status_code == 200
    assert kept.json()["name"] == "CAJA GENERAL"


async def test_deleted_accounts_are_hidden_from_lists(client: AsyncClient) -> None:
    await seed_branch(client)
    await client.delete("/api/v1/accounts/110505")

    listed = await client.get("/api/v1/accounts")
    assert "110505" not in [a["code"] for a in listed.json()]

    with_deleted = await client.get(
        "/api/v1/accounts", params={"include_deleted": True}
    )
    assert "110505" in [a["code"] for a in with_deleted.json()]


async def test_deleted_accounts_are_hidden_from_the_tree(client: AsyncClient) -> None:
    await seed_branch(client)
    await client.delete("/api/v1/accounts/110505")

    tree = (await client.get("/api/v1/accounts/tree")).json()
    account = tree[0]["children"][0]["children"][0]
    assert account["children"] == []

    with_deleted = (
        await client.get("/api/v1/accounts/tree", params={"include_deleted": True})
    ).json()
    revived = with_deleted[0]["children"][0]["children"][0]
    assert [c["code"] for c in revived["children"]] == ["110505"]


async def test_delete_is_blocked_while_it_has_live_children(
    client: AsyncClient,
) -> None:
    await seed_branch(client)

    response = await client.delete("/api/v1/accounts/1")

    assert response.status_code == 409
    assert (await client.get("/api/v1/accounts/1")).status_code == 200


async def test_deleting_children_first_unblocks_the_parent(
    client: AsyncClient,
) -> None:
    await seed_branch(client)

    assert (await client.delete("/api/v1/accounts/110505")).status_code == 200
    # The parent is now childless as far as live rows are concerned.
    assert (await client.delete("/api/v1/accounts/1105")).status_code == 200


async def test_restore_brings_the_account_back(client: AsyncClient) -> None:
    await seed_branch(client)
    await client.delete("/api/v1/accounts/110505")

    restored = await client.post("/api/v1/accounts/110505/restore")

    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None
    assert (await client.get("/api/v1/accounts/110505")).status_code == 200


async def test_restore_requires_the_account_to_be_deleted(
    client: AsyncClient,
) -> None:
    await seed_branch(client)

    response = await client.post("/api/v1/accounts/110505/restore")

    assert response.status_code == 409


async def test_restore_is_blocked_while_the_parent_is_deleted(
    client: AsyncClient,
) -> None:
    await seed_branch(client)
    await client.delete("/api/v1/accounts/110505")
    await client.delete("/api/v1/accounts/1105")

    response = await client.post("/api/v1/accounts/110505/restore")

    assert response.status_code == 422
    assert "1105" in response.json()["detail"]


async def test_recreating_a_deleted_code_revives_it(client: AsyncClient) -> None:
    await seed_branch(client)
    await client.delete("/api/v1/accounts/110505")

    recreated = await client.post(
        "/api/v1/accounts", json={**SUBACCOUNT, "name": "CAJA GENERAL NUEVA"}
    )

    assert recreated.status_code == 201
    assert recreated.json()["deleted_at"] is None
    assert recreated.json()["name"] == "CAJA GENERAL NUEVA"


async def test_restoring_a_missing_account_returns_404(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/accounts/9999/restore")).status_code == 404


async def test_deleting_twice_returns_404_the_second_time(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/accounts", json=CLASS_)

    assert (await client.delete("/api/v1/accounts/1")).status_code == 200
    assert (await client.delete("/api/v1/accounts/1")).status_code == 404
