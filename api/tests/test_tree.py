from typing import Any

from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_accounts import seed_branch


async def test_tree_can_start_at_a_branch(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    response = await auth_client.get(
        "/api/v1/accounts/tree", params={"root_code": "1105"}
    )

    tree = response.json()
    assert [node["code"] for node in tree] == ["1105"]
    assert [child["code"] for child in tree[0]["children"]] == ["110505"]


async def test_tree_respects_max_depth(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    tree = (
        await auth_client.get("/api/v1/accounts/tree", params={"max_depth": 1})
    ).json()

    assert tree[0]["code"] == "1"
    assert [child["code"] for child in tree[0]["children"]] == ["11"]
    assert tree[0]["children"][0]["children"] == []


async def test_max_depth_is_bounded_in_sql_not_in_memory(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    """The point of max_depth is reading less, not just sending less."""
    await seed_branch(auth_client)

    fetched: list[int] = []

    @event.listens_for(session.sync_session, "loaded_as_persistent")
    def _count(_: object, __: object) -> None:
        fetched.append(1)

    fetched.clear()
    await auth_client.get("/api/v1/accounts/tree", params={"max_depth": 0})
    shallow = len(fetched)

    fetched.clear()
    await auth_client.get("/api/v1/accounts/tree")
    everything = len(fetched)

    assert shallow < everything


async def test_deeper_max_depth_returns_more(auth_client: AsyncClient) -> None:
    await seed_branch(auth_client)

    def depth(nodes: list[dict[str, Any]]) -> int:
        return 1 + max((depth(n["children"]) for n in nodes), default=0) if nodes else 0

    shallow = (
        await auth_client.get("/api/v1/accounts/tree", params={"max_depth": 0})
    ).json()
    deep = (await auth_client.get("/api/v1/accounts/tree")).json()

    assert depth(shallow) == 1
    assert depth(deep) == 4
