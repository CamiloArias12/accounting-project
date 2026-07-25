"""The import must be all-or-nothing: a chart committed halfway is worse than
one not imported at all."""

import io
from typing import Any

from httpx import AsyncClient
from openpyxl import Workbook

HEADER = ("Codigo", "Nombre", "Tipo", "Naturaleza")


def spreadsheet(rows: list[tuple[Any, ...]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(list(HEADER))
    for row in rows:
        sheet.append(list(row))

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


async def upload(client: AsyncClient, rows: list[tuple[Any, ...]]) -> Any:
    response = await client.post(
        "/api/v1/accounts/import",
        files={"file": ("puc.xlsx", spreadsheet(rows), "application/vnd.ms-excel")},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_large_file_lands_in_one_transaction(
    auth_client: AsyncClient,
) -> None:
    """More rows than the chunk size, so the old code would have committed
    several times along the way."""
    rows: list[tuple[Any, ...]] = [(1, "ACTIVOS", "Clase", "Debito")]
    rows += [
        (f"1{group:01d}", f"GROUP {group}", "Grupo", "Debito") for group in range(9)
    ]
    rows += [
        (f"10{account:02d}", f"ACCOUNT {account}", "Cuenta", "Debito")
        for account in range(10, 100)
    ]

    result = await upload(auth_client, rows)

    assert result["created"] == len(rows)
    listed = await auth_client.get("/api/v1/accounts", params={"limit": 500})
    assert len(listed.json()) == len(rows)


async def test_rows_that_fail_do_not_stop_the_rest(auth_client: AsyncClient) -> None:
    result = await upload(
        auth_client,
        [
            (1, "ACTIVOS", "Clase", "Debito"),
            (4444, "NO PARENT", "Cuenta", "Debito"),
            (11, "DISPONIBLE", "Grupo", "Debito"),
        ],
    )

    assert result["created"] == 2
    assert [error["code"] for error in result["errors"]] == ["4444"]
