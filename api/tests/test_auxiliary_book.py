"""The auxiliary book: what the spreadsheet actually contains.

Read back with openpyxl rather than asserted on the bytes, because the point of
the file is that a spreadsheet application can open it — a test that checks a
byte string proves the builder repeats itself, not that it produced a workbook.
"""

from io import BytesIO
from typing import Any

from httpx import AsyncClient, Response
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_ledger import sale, seed_chart_without_third_party
from tests.test_vouchers import a_posted_voucher, a_third_party, seed_chart

BASE = "/api/v1/ledger/export"

#: Where the column headings sit; the masthead is above them.
HEADER_ROW = 5


def sheet_of(response: Response) -> Worksheet:
    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook.active
    assert sheet is not None
    return sheet


def rows_of(sheet: Worksheet) -> list[tuple[Any, ...]]:
    """Every row below the headings, as plain tuples."""
    return [
        tuple(row) for row in sheet.iter_rows(min_row=HEADER_ROW + 1, values_only=True)
    ]


def column(sheet: Worksheet, index: int) -> list[Any]:
    return [row[index] for row in rows_of(sheet)]


async def test_the_file_is_a_workbook_a_spreadsheet_can_open(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    response = await auth_client.get(BASE)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers["content-disposition"]
    assert ".xlsx" in response.headers["content-disposition"]

    # Opening it is the assertion: a corrupt workbook raises here.
    assert sheet_of(response).max_row > HEADER_ROW


async def test_the_headings_are_the_columns_a_book_has(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    sheet = sheet_of(await auth_client.get(BASE))
    headings = [cell.value for cell in sheet[HEADER_ROW]]

    assert headings == [
        "FECHA",
        "COMPROBANTE",
        "CONCEPTO",
        "CÓDIGO CUENTA",
        "NOMBRE CUENTA",
        "IDENTIFICACIÓN TERCERO",
        "NOMBRE TERCERO",
        "DÉBITO",
        "CRÉDITO",
        "SALDO",
    ]


async def test_the_headings_follow_the_asked_for_language(
    auth_client: AsyncClient,
) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    sheet = sheet_of(await auth_client.get(BASE, params={"locale": "en"}))

    assert sheet[HEADER_ROW][0].value == "DATE"
    assert sheet.cell(row=1, column=1).value == "Auxiliary ledger"


async def test_the_masthead_says_what_the_book_covers(
    auth_client: AsyncClient,
) -> None:
    """A spreadsheet gets renamed and forwarded; the range has to be on it."""
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    sheet = sheet_of(
        await auth_client.get(
            BASE, params={"date_from": "2026-07-01", "date_to": "2026-07-31"}
        )
    )

    assert sheet.cell(row=1, column=1).value == "Libro auxiliar"
    assert sheet.cell(row=2, column=2).value  # the company
    assert sheet.cell(row=3, column=2).value == "2026-07-01 — 2026-07-31"


async def test_amounts_are_numbers_and_not_text(auth_client: AsyncClient) -> None:
    """A book whose amounts are strings cannot be summed in the spreadsheet
    it was exported for, which is most of the reason to export one."""
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    sheet = sheet_of(await auth_client.get(BASE))
    amounts = [value for value in column(sheet, 7) if value is not None]

    assert amounts
    assert all(isinstance(value, int | float) for value in amounts)


async def test_every_account_carries_its_own_block(auth_client: AsyncClient) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    sheet = sheet_of(await auth_client.get(BASE))
    codes = [value for value in column(sheet, 3) if value]

    # Both sides of the entry, each with an opening row and a movement row.
    assert codes.count("110505") == 2
    assert codes.count("220505") == 2

    labels = [value for value in column(sheet, 6) if value]
    assert labels.count("Saldo anterior") == 2
    assert labels.count("Totales cuenta") == 2
    assert labels.count("Total general") == 1


async def test_the_balance_runs_down_the_account(auth_client: AsyncClient) -> None:
    """Not the line's own amount — the account's balance after it.

    The reference project prints the signed line value in this column, which
    means it says nothing a reader cannot get from the two beside it.
    """
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())
    await a_posted_voucher(auth_client, **sale(date="2026-07-11"))

    sheet = sheet_of(await auth_client.get(BASE))
    cash = [
        row
        for row in rows_of(sheet)
        if row[3] == "110505" and row[0] is not None  # movements, not the opening row
    ]

    assert [row[9] for row in cash] == [150000.0, 300000.0]


async def test_the_book_adds_up_to_nothing(auth_client: AsyncClient) -> None:
    """Signed balances sum to zero when every voucher behind them balanced."""
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())

    sheet = sheet_of(await auth_client.get(BASE))
    grand = next(row for row in rows_of(sheet) if row[6] == "Total general")

    assert grand[7] == 150000.0
    assert grand[8] == 150000.0
    assert grand[9] == 0


async def test_an_opening_balance_is_its_own_row(auth_client: AsyncClient) -> None:
    """An account that only moved before the range still belongs in the book."""
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale(date="2026-06-15"))

    sheet = sheet_of(await auth_client.get(BASE, params={"date_from": "2026-07-01"}))
    cash = [row for row in rows_of(sheet) if row[3] == "110505"]

    # The opening row carries the balance and no movement.
    assert cash[0][6] == "Saldo anterior"
    assert cash[0][9] == 150000.0
    assert cash[0][7] is None


async def test_the_third_party_is_named_and_identified(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    supplier = await a_third_party(auth_client, session)

    await a_posted_voucher(
        auth_client,
        **sale(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {
                    "account_code": "220505",
                    "credit": "150000.00",
                    "third_party_id": supplier,
                },
            ]
        ),
    )

    sheet = sheet_of(await auth_client.get(BASE))
    payable = next(
        row for row in rows_of(sheet) if row[3] == "220505" and row[0] is not None
    )

    # Two people can share a name; the document is what identifies them.
    assert payable[5]
    assert payable[6]


async def test_the_book_can_be_narrowed(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_chart(auth_client)
    supplier = await a_third_party(auth_client, session)

    await a_posted_voucher(
        auth_client,
        **sale(
            lines=[
                {"account_code": "110505", "debit": "150000.00"},
                {
                    "account_code": "220505",
                    "credit": "150000.00",
                    "third_party_id": supplier,
                },
            ]
        ),
    )

    branch = sheet_of(await auth_client.get(BASE, params={"account_code": "2205"}))
    assert {value for value in column(branch, 3) if value} == {"220505"}

    theirs = sheet_of(await auth_client.get(BASE, params={"third_party_id": supplier}))
    assert {value for value in column(theirs, 3) if value} == {"220505"}


async def test_a_book_with_nothing_in_it_is_still_a_workbook(
    auth_client: AsyncClient,
) -> None:
    """An empty file beats a 404: the range simply had no movement."""
    sheet = sheet_of(await auth_client.get(BASE))

    assert (
        sheet.cell(row=HEADER_ROW + 1, column=1).value == "Sin movimientos en el rango."
    )


async def test_export_is_not_read_as_an_account_code(auth_client: AsyncClient) -> None:
    """`/ledger/export` and `/ledger/{code}` share a shape; order decides."""
    response = await auth_client.get(BASE)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd")


async def test_the_export_requires_a_token(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401
