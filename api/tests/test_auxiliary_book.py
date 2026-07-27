"""The auxiliary book: what the spreadsheet actually contains.

Read back with openpyxl rather than asserted on the bytes, because the point of
the file is that a spreadsheet application can open it — a test that checks a
byte string proves the builder repeats itself, not that it produced a workbook.
"""

from io import BytesIO
from typing import Any

from httpx import AsyncClient
from openpyxl import load_workbook

from tests.test_ledger import sale, seed_chart_without_third_party
from tests.test_vouchers import a_posted_voucher

BASE = "/api/v1/ledger/export"

#: Where the column headings sit; the masthead is above them.
HEADER_ROW = 5


async def test_the_book_is_a_workbook_that_adds_up(auth_client: AsyncClient) -> None:
    await seed_chart_without_third_party(auth_client)
    await a_posted_voucher(auth_client, **sale())
    await a_posted_voucher(auth_client, **sale(date="2026-07-11"))

    response = await auth_client.get(BASE)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers["content-disposition"]

    # Opening it is the assertion: a corrupt workbook raises here.
    sheet = load_workbook(BytesIO(response.content)).active
    assert sheet is not None
    rows: list[tuple[Any, ...]] = [
        tuple(row) for row in sheet.iter_rows(min_row=HEADER_ROW + 1, values_only=True)
    ]

    # Not the line's own amount — the account's balance after it. The reference
    # project prints the signed line value, which says nothing the two columns
    # beside it do not.
    cash = [row for row in rows if row[3] == "110505" and row[0] is not None]
    assert [row[9] for row in cash] == [150000.0, 300000.0]
    # Numbers, not text: a book whose amounts are strings cannot be summed in
    # the spreadsheet it was exported for.
    assert all(isinstance(row[7], int | float) for row in cash)

    # Signed balances sum to zero when every voucher behind them balanced.
    grand = next(row for row in rows if row[6] == "Total general")
    assert (grand[7], grand[8], grand[9]) == (300000.0, 300000.0, 0)
