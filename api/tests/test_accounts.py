"""The chart of accounts: the code is the hierarchy, and only leaves post."""

import io
from collections.abc import Sequence
from typing import Any

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from app.modules.accounts.puc import (
    AccountLevel,
    InvalidAccountCode,
    level_of,
    parent_code_of,
    validate_code,
)

BASE = "/api/v1/accounts"

CLASS_ = {"code": "1", "name": "ACTIVOS", "nature": "Debito"}
GROUP = {"code": "11", "name": "DISPONIBLE", "nature": "Debito"}
ACCOUNT = {"code": "1105", "name": "CAJA", "nature": "Debito"}
SUBACCOUNT = {"code": "110505", "name": "CAJA GENERAL", "nature": "Debito"}


async def seed_branch(auth_client: AsyncClient) -> None:
    """Create the branch 1 > 11 > 1105 > 110505."""
    for payload in (CLASS_, GROUP, ACCOUNT, SUBACCOUNT):
        response = await auth_client.post(BASE, json=payload)
        assert response.status_code == 201, response.text


# --- the code is the hierarchy -----------------------------------------------


def test_the_level_and_the_parent_derive_from_the_code() -> None:
    cases: list[tuple[str, AccountLevel, str | None]] = [
        ("1", AccountLevel.CLASS, None),
        ("11", AccountLevel.GROUP, "1"),
        ("1105", AccountLevel.ACCOUNT, "11"),
        ("110505", AccountLevel.SUBACCOUNT, "1105"),
        ("11050501", AccountLevel.AUXILIARY, "110505"),
        ("1105050199", AccountLevel.AUXILIARY, "110505"),
    ]
    for code, level, parent in cases:
        assert level_of(code) is level, code
        assert parent_code_of(code) == parent, code


def test_a_code_that_is_not_a_puc_code_is_refused() -> None:
    # Non-numeric, and lengths that name no level: 110 is neither a group nor
    # an account, so it has no place in the tree.
    for code in ("", "   ", "11a", "1.5", "-1", "110", "11050"):
        with pytest.raises(InvalidAccountCode):
            validate_code(code)


# --- the API -----------------------------------------------------------------


async def test_creating_derives_the_level_and_demands_the_parent(
    auth_client: AsyncClient,
) -> None:
    orphan = await auth_client.post(BASE, json=GROUP)
    assert orphan.status_code == 422
    assert "1" in orphan.json()["detail"]

    klass = await auth_client.post(BASE, json=CLASS_)
    assert klass.json()["level"] == "Clase"
    assert klass.json()["parent_code"] is None

    group = await auth_client.post(BASE, json=GROUP)
    assert group.status_code == 201
    assert group.json()["level"] == "Grupo"
    assert group.json()["parent_code"] == "1"

    assert (await auth_client.post(BASE, json=CLASS_)).status_code == 409

    # The code is the identity: renaming it would move the account to another
    # parent and leave its children behind.
    renamed = await auth_client.patch(
        f"{BASE}/1", json={"name": "ACTIVO CORRIENTE", "code": "9"}
    )
    assert renamed.json()["name"] == "ACTIVO CORRIENTE"
    assert renamed.json()["code"] == "1"


async def test_only_the_leaves_take_entries(auth_client: AsyncClient) -> None:
    """A heading never takes entries: its balance is the sum of its children."""
    await seed_branch(auth_client)

    postable = await auth_client.get(BASE, params={"only_postable": True})

    # 1 > 11 > 1105 > 110505: only the deepest one takes entries, even though it
    # is a six-digit subaccount rather than an auxiliary.
    assert [a["code"] for a in postable.json()["items"]] == ["110505"]


async def test_the_tree_nests_the_branch_and_max_depth_bounds_it(
    auth_client: AsyncClient,
) -> None:
    await seed_branch(auth_client)

    tree = (await auth_client.get(f"{BASE}/tree")).json()
    assert len(tree) == 1
    klass = tree[0]
    assert klass["code"] == "1"
    group = klass["children"][0]
    assert group["code"] == "11"
    assert group["children"][0]["code"] == "1105"
    assert group["children"][0]["children"][0]["code"] == "110505"

    shallow = (await auth_client.get(f"{BASE}/tree", params={"max_depth": 1})).json()
    assert [child["code"] for child in shallow[0]["children"]] == ["11"]
    assert shallow[0]["children"][0]["children"] == []


async def test_a_deleted_account_keeps_its_row_and_protects_its_parent(
    auth_client: AsyncClient,
) -> None:
    await seed_branch(auth_client)

    # A parent with live children cannot go.
    assert (await auth_client.delete(f"{BASE}/1")).status_code == 409

    deleted = await auth_client.delete(f"{BASE}/110505")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None

    # Gone from the normal view, still there when asked for explicitly: an
    # account named in an old voucher must stay readable.
    assert (await auth_client.get(f"{BASE}/110505")).status_code == 404
    kept = await auth_client.get(f"{BASE}/110505", params={"include_deleted": True})
    assert kept.json()["name"] == "CAJA GENERAL"

    # Creating the same code back revives the row rather than colliding with it.
    recreated = await auth_client.post(
        BASE, json={**SUBACCOUNT, "name": "CAJA GENERAL NUEVA"}
    )
    assert recreated.status_code == 201
    assert recreated.json()["deleted_at"] is None
    assert recreated.json()["name"] == "CAJA GENERAL NUEVA"


# --- the import --------------------------------------------------------------

#: One spreadsheet row, as openpyxl writes it.
CellValues = tuple[str | int | None, ...]

HEADER = ("Codigo", "Nombre", "Tipo", "Naturaleza")
BRANCH: list[CellValues] = [
    (1, "ACTIVOS", "Clase", "Debito"),
    (11, "DISPONIBLE", "Grupo", "Debito"),
    (1105, "CAJA", "Cuenta", "Debito"),
    (110505, "CAJA GENERAL", "Subcuenta", "Debito"),
]


def spreadsheet(rows: Sequence[CellValues]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(list(HEADER))
    for row in rows:
        sheet.append(list(row))

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def upload(
    auth_client: AsyncClient, rows: Sequence[CellValues], **params: str
) -> Any:
    response = await auth_client.post(
        f"{BASE}/import",
        files={"file": ("puc.xlsx", spreadsheet(rows), "application/vnd.ms-excel")},
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_import_links_parents_in_any_order_and_reports_what_failed(
    auth_client: AsyncClient,
) -> None:
    # Upside down: a child arrives before the parent it hangs off, which is
    # ordinary in a file somebody sorted by hand.
    orphan: CellValues = (4444, "HUÉRFANA", "Cuenta", "Debito")
    result = await upload(auth_client, [*reversed(BRANCH), orphan])

    assert result["created"] == 4
    assert (await auth_client.get(f"{BASE}/110505")).json()["parent_code"] == "1105"

    # The one bad row is named and the good ones stay: an import that rolled
    # back 2.446 accounts over one typo would be unusable.
    assert [error["code"] for error in result["errors"]] == ["4444"]

    # Running it again changes nothing unless asked to update.
    again = await upload(auth_client, BRANCH)
    assert (again["created"], again["skipped"]) == (0, 4)

    updated = await upload(
        auth_client, [(1, "ACTIVOS RENAMED", "Clase", "Debito")], on_existing="update"
    )
    assert updated["updated"] == 1
    assert (await auth_client.get(f"{BASE}/1")).json()["name"] == "ACTIVOS RENAMED"


async def test_a_large_import_lands_in_one_transaction(
    auth_client: AsyncClient,
) -> None:
    """More rows than the chunk size, so the old code would have committed
    several times along the way — leaving half a chart behind on failure."""
    rows: list[CellValues] = [(1, "ACTIVOS", "Clase", "Debito")]
    rows += [
        (f"1{group:01d}", f"GROUP {group}", "Grupo", "Debito") for group in range(9)
    ]
    rows += [
        (f"10{account:02d}", f"ACCOUNT {account}", "Cuenta", "Debito")
        for account in range(10, 100)
    ]

    result = await upload(auth_client, rows)

    assert result["created"] == len(rows)
    listed = await auth_client.get(BASE, params={"limit": 500})
    assert listed.json()["total"] == len(rows)
