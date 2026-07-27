from httpx import AsyncClient

REGISTRATION = {
    "email": "someone@example.com",
    "password": "sup3r-secret",
    "full_name": "Someone",
}

PROTECTED = [
    "/api/v1/auth/me",
    "/api/v1/accounts",
    "/api/v1/accounts/tree",
    "/api/v1/third-parties",
    "/api/v1/locations/countries",
    "/api/v1/vouchers",
    "/api/v1/ledger",
    "/api/v1/ledger/export",
    "/api/v1/periods/2026/7",
    "/api/v1/exogena/history",
    "/api/v1/uvt",
]


async def test_registering_and_logging_in(client: AsyncClient) -> None:
    registered = await client.post("/api/v1/auth/register", json=REGISTRATION)

    assert registered.status_code == 201
    assert "password" not in registered.json()
    assert "hashed_password" not in registered.json()

    logged_in = await client.post(
        "/api/v1/auth/login",
        data={"username": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"

    token = logged_in.json()["access_token"]
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.json()["email"] == REGISTRATION["email"]


async def test_a_bad_login_says_nothing_about_the_account(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=REGISTRATION)

    unknown = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "sup3r-secret"},
    )
    wrong = await client.post(
        "/api/v1/auth/login",
        data={"username": REGISTRATION["email"], "password": "wrong-password"},
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


async def test_every_module_is_behind_the_login(client: AsyncClient) -> None:
    for path in PROTECTED:
        assert (await client.get(path)).status_code == 401, path

    account = {"code": "1", "name": "ACTIVOS", "nature": "Debito"}
    assert (await client.post("/api/v1/accounts", json=account)).status_code == 401
    assert (await client.delete("/api/v1/accounts/1")).status_code == 401

    forged = await client.get(
        "/api/v1/accounts", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert forged.status_code == 401
