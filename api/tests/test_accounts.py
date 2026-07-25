from httpx import AsyncClient

PAYLOAD = {"code": "1010", "name": "Caja", "type": "asset"}


async def test_create_and_get_account(client: AsyncClient) -> None:
    created = await client.post("/api/v1/accounts", json=PAYLOAD)
    assert created.status_code == 201
    body = created.json()
    assert body["code"] == "1010"
    assert body["type"] == "asset"
    assert body["is_active"] is True

    fetched = await client.get(f"/api/v1/accounts/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Caja"


async def test_duplicate_code_returns_409(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/accounts", json=PAYLOAD)).status_code == 201
    duplicate = await client.post("/api/v1/accounts", json=PAYLOAD)
    assert duplicate.status_code == 409


async def test_list_accounts_is_ordered_by_code(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/accounts",
        json={**PAYLOAD, "code": "2010", "name": "Proveedores", "type": "liability"},
    )
    await client.post("/api/v1/accounts", json=PAYLOAD)

    response = await client.get("/api/v1/accounts")
    assert response.status_code == 200
    assert [a["code"] for a in response.json()] == ["1010", "2010"]


async def test_update_account(client: AsyncClient) -> None:
    created = await client.post("/api/v1/accounts", json=PAYLOAD)
    account_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/accounts/{account_id}", json={"name": "Caja general"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Caja general"
    assert updated.json()["code"] == "1010"


async def test_delete_account(client: AsyncClient) -> None:
    created = await client.post("/api/v1/accounts", json=PAYLOAD)
    account_id = created.json()["id"]

    assert (await client.delete(f"/api/v1/accounts/{account_id}")).status_code == 204
    assert (await client.get(f"/api/v1/accounts/{account_id}")).status_code == 404


async def test_get_missing_account_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/accounts/999")).status_code == 404


async def test_invalid_account_type_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/accounts", json={**PAYLOAD, "type": "not-a-type"}
    )
    assert response.status_code == 422
