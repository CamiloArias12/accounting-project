from httpx import AsyncClient, Response

REGISTRATION = {
    "email": "someone@example.com",
    "password": "sup3r-secret",
    "full_name": "Someone",
}


async def register(client: AsyncClient, **overrides: object) -> Response:
    return await client.post(
        "/api/v1/auth/register", json={**REGISTRATION, **overrides}
    )


async def test_register_returns_the_user_without_the_password(
    client: AsyncClient,
) -> None:
    response = await register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "someone@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


async def test_email_is_normalized(client: AsyncClient) -> None:
    response = await register(client, email="  MiXeD@Example.COM  ")

    assert response.json()["email"] == "mixed@example.com"


async def test_duplicate_email_returns_409(client: AsyncClient) -> None:
    await register(client)
    assert (await register(client)).status_code == 409


async def test_short_password_is_rejected(client: AsyncClient) -> None:
    assert (await register(client, password="short")).status_code == 422


async def test_login_returns_a_bearer_token(client: AsyncClient) -> None:
    await register(client)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


async def test_wrong_password_returns_401(client: AsyncClient) -> None:
    await register(client)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": REGISTRATION["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_unknown_email_returns_401_with_the_same_message(
    client: AsyncClient,
) -> None:
    """The response must not reveal whether the email exists."""
    await register(client)

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


async def test_me_requires_a_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_me_rejects_a_forged_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


async def test_me_returns_the_authenticated_user(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "tester@example.com"


# --- accounts are protected ----------------------------------------------

ACCOUNT = {"code": "1", "name": "ACTIVOS", "nature": "Debito"}


async def test_reading_accounts_is_public(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/accounts")).status_code == 200
    assert (await client.get("/api/v1/accounts/tree")).status_code == 200


async def test_creating_an_account_requires_a_token(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/accounts", json=ACCOUNT)).status_code == 401


async def test_deleting_an_account_requires_a_token(client: AsyncClient) -> None:
    assert (await client.delete("/api/v1/accounts/1")).status_code == 401


async def test_importing_requires_a_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/accounts/import",
        files={"file": ("puc.xlsx", b"x", "application/vnd.ms-excel")},
    )
    assert response.status_code == 401


async def test_a_token_unlocks_writing(auth_client: AsyncClient) -> None:
    assert (await auth_client.post("/api/v1/accounts", json=ACCOUNT)).status_code == 201
