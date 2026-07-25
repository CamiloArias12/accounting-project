import io
from collections.abc import Sequence
from typing import Any

from httpx import AsyncClient
from openpyxl import Workbook

# One spreadsheet row, as openpyxl writes it.
CellValues = tuple[str | int | None, ...]

HEADER = ("Codigo", "Nombre", "Tipo", "Naturaleza")
BRANCH: list[CellValues] = [
    (1, "ACTIVOS", "Clase", "Debito"),
    (11, "DISPONIBLE", "Grupo", "Debito"),
    (1105, "CAJA", "Cuenta", "Debito"),
    (110505, "CAJA GENERAL", "Subcuenta", "Debito"),
]


def spreadsheet(rows: Sequence[CellValues], *, header: bool = True) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    if header:
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
        "/api/v1/accounts/import",
        files={"file": ("puc.xlsx", spreadsheet(rows), "application/vnd.ms-excel")},
        params=params,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_import_creates_the_whole_branch(auth_client: AsyncClient) -> None:
    result = await upload(auth_client, BRANCH)

    assert result["created"] == 4
    assert result["errors"] == []

    tree = (await auth_client.get("/api/v1/accounts/tree")).json()
    assert tree[0]["children"][0]["children"][0]["children"][0]["code"] == "110505"


async def test_import_links_parents_regardless_of_row_order(
    auth_client: AsyncClient,
) -> None:
    result = await upload(auth_client, list(reversed(BRANCH)))

    assert result["created"] == 4
    assert result["errors"] == []

    subaccount = (await auth_client.get("/api/v1/accounts/110505")).json()
    assert subaccount["parent_code"] == "1105"


async def test_import_reports_missing_parent(auth_client: AsyncClient) -> None:
    result = await upload(auth_client, [(1105, "CAJA", "Cuenta", "Debito")])

    assert result["created"] == 0
    assert result["errors"][0]["code"] == "1105"
    assert "11" in result["errors"][0]["message"]


async def test_import_skips_existing_by_default(auth_client: AsyncClient) -> None:
    await upload(auth_client, BRANCH)
    result = await upload(auth_client, BRANCH)

    assert result["created"] == 0
    assert result["skipped"] == 4


async def test_import_can_update_existing(auth_client: AsyncClient) -> None:
    await upload(auth_client, BRANCH)
    result = await upload(
        auth_client,
        [(1, "ACTIVOS RENAMED", "Clase", "Debito")],
        on_existing="update",
    )

    assert result["updated"] == 1
    assert (await auth_client.get("/api/v1/accounts/1")).json()[
        "name"
    ] == "ACTIVOS RENAMED"


async def test_import_accepts_nature_without_accent(auth_client: AsyncClient) -> None:
    result = await upload(
        auth_client,
        [(2, "PASIVOS", "Clase", "Credito"), (3, "PATRIMONIO", "Clase", "CRÉDITO")],
    )

    assert result["created"] == 2
    assert (await auth_client.get("/api/v1/accounts/2")).json()["nature"] == "Crédito"


async def test_import_reports_unknown_nature(auth_client: AsyncClient) -> None:
    result = await upload(auth_client, [(1, "ACTIVOS", "Clase", "Ninguna")])

    assert result["created"] == 0
    assert "nature" in result["errors"][0]["message"].lower()


async def test_import_reports_type_contradicting_the_code(
    auth_client: AsyncClient,
) -> None:
    result = await upload(auth_client, [(1, "ACTIVOS", "Grupo", "Debito")])

    assert result["created"] == 0
    assert "does not match" in result["errors"][0]["message"]


async def test_import_reports_duplicate_rows(auth_client: AsyncClient) -> None:
    result = await upload(
        auth_client, [*BRANCH, (1, "ACTIVOS AGAIN", "Clase", "Debito")]
    )

    assert result["created"] == 4
    assert "Duplicate" in result["errors"][0]["message"]


async def test_import_ignores_blank_rows(auth_client: AsyncClient) -> None:
    result = await upload(auth_client, [BRANCH[0], (None, None, None, None), BRANCH[1]])

    assert result["created"] == 2
    assert result["errors"] == []


async def test_import_reports_missing_name(auth_client: AsyncClient) -> None:
    result = await upload(auth_client, [(1, "", "Clase", "Debito")])

    assert result["created"] == 0
    assert "name" in result["errors"][0]["message"].lower()


async def test_import_rejects_a_file_that_is_not_excel(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/accounts/import",
        files={"file": ("puc.xlsx", b"not a spreadsheet", "application/vnd.ms-excel")},
    )

    assert response.status_code == 400


async def test_import_partial_success_keeps_valid_rows(
    auth_client: AsyncClient,
) -> None:
    result = await upload(
        auth_client,
        [*BRANCH, (4444, "NO PARENT", "Cuenta", "Debito")],
    )

    assert result["created"] == 4
    assert len(result["errors"]) == 1
    assert result["errors"][0]["code"] == "4444"
