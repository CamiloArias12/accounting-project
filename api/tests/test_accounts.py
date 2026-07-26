from httpx import AsyncClient

CLASS_ = {"code": "1", "name": "ACTIVOS", "nature": "Debito"}
GROUP = {"code": "11", "name": "DISPONIBLE", "nature": "Debito"}
ACCOUNT = {"code": "1105", "name": "CAJA", "nature": "Debito"}
SUBACCOUNT = {"code": "110505", "name": "CAJA GENERAL", "nature": "Debito"}


async def seed_branch(auth_client: AsyncClient) -> None:
    """Create the branch 1 > 11 > 1105 > 110505."""
    for payload in (CLASS_, GROUP, ACCOUNT, SUBACCOUNT):
        response = await auth_client.post("/api/v1/accounts", json=payload)
        assert response.status_code == 201, response.text


async def test_create_derives_level_and_parent_from_code(
    auth_client: AsyncClient,
) -> None:
    await auth_client.post("/api/v1/accounts", json=CLASS_)
    response = await auth_client.post("/api/v1/accounts", json=GROUP)

    assert response.status_code == 201
    body = response.json()
    assert body["level"] == "Grupo"
    assert body["parent_code"] == "1"


async def test_class_has_no_parent(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/api/v1/accounts", json=CLASS_)

    assert response.status_code == 201
    assert response.json()["level"] == "Clase"
    assert response.json()["parent_code"] is None


async def test_create_requires_the_parent_to_exist(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/api/v1/accounts", json=GROUP)

    assert response.status_code == 422
    assert "1" in response.json()["detail"]


async def test_duplicate_code_returns_409(auth_client: AsyncClient) -> None:
    assert (await auth_client.post("/api/v1/accounts", json=CLASS_)).status_code == 201
    assert (await auth_client.post("/api/v1/accounts", json=CLASS_)).status_code == 409


async def test_rejects_code_with_no_puc_level(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/accounts", json={**CLASS_, "code": "110"}
    )
    assert response.status_code == 422


async def test_rejects_non_numeric_code(auth_client: AsyncClient) -> None:
    response = await auth_client.post("/api/v1/accounts", json={**CLASS_, "code": "1A"})
    assert response.status_code == 422


async def test_rejects_unknown_nature(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        "/api/v1/accounts", json={**CLASS_, "nature": "None"}
    )
    assert response.status_code == 422


async def test_list_filters_by_level(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    response = await auth_client.get("/api/v1/accounts", params={"level": "Cuenta"})

    assert response.status_code == 200
    assert [a["code"] for a in response.json()["items"]] == ["1105"]


async def test_list_filters_by_parent(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    response = await auth_client.get("/api/v1/accounts", params={"parent_code": "11"})

    assert [a["code"] for a in response.json()["items"]] == ["1105"]


async def test_search_matches_code_and_name(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    by_name = await auth_client.get(
        "/api/v1/accounts", params={"search": "CAJA GENERAL"}
    )
    assert [a["code"] for a in by_name.json()["items"]] == ["110505"]

    by_code = await auth_client.get("/api/v1/accounts", params={"search": "1105"})
    assert {a["code"] for a in by_code.json()["items"]} == {"1105", "110505"}


async def test_tree_nests_the_whole_branch(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    response = await auth_client.get("/api/v1/accounts/tree")

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 1

    klass = tree[0]
    assert klass["code"] == "1"
    group = klass["children"][0]
    assert group["code"] == "11"
    account = group["children"][0]
    assert account["code"] == "1105"
    assert account["children"][0]["code"] == "110505"


async def test_update_changes_name_but_not_code(auth_client: AsyncClient) -> None:
    await auth_client.post("/api/v1/accounts", json=CLASS_)

    response = await auth_client.patch(
        "/api/v1/accounts/1", json={"name": "ACTIVO CORRIENTE", "code": "9"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "ACTIVO CORRIENTE"
    assert response.json()["code"] == "1"


async def test_get_missing_account_returns_404(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/api/v1/accounts/9999")).status_code == 404


async def test_only_postable_returns_the_leaves(auth_client: AsyncClient) -> None:
    """A heading never takes entries: its balance is the sum of its children."""
    await seed_branch(auth_client)

    postable = await auth_client.get("/api/v1/accounts", params={"only_postable": True})

    # 1 > 11 > 1105 > 110505: only the deepest one takes entries, even though it
    # is a six-digit subaccount rather than an auxiliary.
    assert [a["code"] for a in postable.json()["items"]] == ["110505"]
