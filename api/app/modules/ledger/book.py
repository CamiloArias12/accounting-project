"""The auxiliary book as a spreadsheet.

The innermost layer, like `exogena.report`: no database, no HTTP, no framework.
Given the accounts and their movements, this builds the workbook and nothing
else.

It is a spreadsheet rather than a PDF because of what people do with it: an
auxiliary book gets filtered, totalled and pasted into a working paper. openpyxl
is already a dependency — the chart of accounts is imported from a workbook —
so this adds no third-party code to the project.

The reference project writes its book to a fixed path on disk and streams it
back, which means two people downloading at once overwrite each other's file.
This returns bytes; nothing is written anywhere.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from io import BytesIO
from typing import Final, Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.modules.ledger.schemas import AccountLedger

Locale = Literal["es", "en"]

#: The columns, in the order the reference project prints them. Two of its
#: columns are dropped: it carries a document *type* the model here does not
#: have (one consecutive series, not one per book), and its "saldo anterior"
#: repeats on every row where it belongs once per account.
HEADERS: Final[dict[Locale, list[str]]] = {
    "es": [
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
    ],
    "en": [
        "DATE",
        "VOUCHER",
        "DESCRIPTION",
        "ACCOUNT CODE",
        "ACCOUNT NAME",
        "THIRD PARTY ID",
        "THIRD PARTY NAME",
        "DEBIT",
        "CREDIT",
        "BALANCE",
    ],
}

LABELS: Final[dict[Locale, dict[str, str]]] = {
    "es": {
        "title": "Libro auxiliar",
        "sheet": "Libro auxiliar",
        "company": "Empresa",
        "range": "Período",
        "generated": "Generado",
        "opening": "Saldo anterior",
        "total": "Totales cuenta",
        "grand_total": "Total general",
        "unbounded": "Sin límite",
        "empty": "Sin movimientos en el rango.",
    },
    "en": {
        "title": "Auxiliary ledger",
        "sheet": "Auxiliary ledger",
        "company": "Company",
        "range": "Period",
        "generated": "Generated",
        "opening": "Opening balance",
        "total": "Account total",
        "grand_total": "Grand total",
        "unbounded": "Unbounded",
        "empty": "No movements in the range.",
    },
}

#: Widths in characters, one per column. A book whose account names are cut off
#: is a book somebody has to widen by hand before reading it.
WIDTHS: Final[list[int]] = [12, 13, 40, 14, 34, 22, 34, 16, 16, 18]

MONEY_FORMAT: Final = "#,##0.00;[Red]-#,##0.00"
DATE_FORMAT: Final = "yyyy-mm-dd"

_HEADER_FILL: Final = PatternFill("solid", fgColor="10417B")
_HEADER_FONT: Final = Font(name="Arial", size=10, bold=True, color="FFFFFF")
_ACCOUNT_FILL: Final = PatternFill("solid", fgColor="EEF2F8")
_THIN: Final = Side(style="thin", color="D6DEE8")


def build_auxiliary_book(
    accounts: list[AccountLedger],
    *,
    company: str,
    date_from: dt.date | None,
    date_to: dt.date | None,
    generated_at: dt.datetime,
    locale: Locale = "es",
) -> bytes:
    """The workbook, as bytes ready to be sent."""
    labels = LABELS[locale]

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = labels["sheet"]

    _write_masthead(
        sheet,
        labels=labels,
        company=company,
        date_from=date_from,
        date_to=date_to,
        generated_at=generated_at,
    )
    _write_header(sheet, HEADERS[locale])

    if not accounts:
        sheet.cell(row=sheet.max_row + 1, column=1, value=labels["empty"])
    else:
        for account in accounts:
            _write_account(sheet, account, labels)
        _write_grand_total(sheet, accounts, labels)

    # The header row stays visible while scrolling a book of a few thousand
    # lines, which is the length these reach.
    sheet.freeze_panes = f"A{_HEADER_ROW + 1}"
    sheet.auto_filter.ref = (
        f"A{_HEADER_ROW}:{get_column_letter(len(WIDTHS))}{sheet.max_row}"
    )

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


#: Row the column headings sit on: four lines of masthead above them.
_HEADER_ROW: Final = 5


def _write_masthead(
    sheet: Worksheet,
    *,
    labels: dict[str, str],
    company: str,
    date_from: dt.date | None,
    date_to: dt.date | None,
    generated_at: dt.datetime,
) -> None:
    """Who the book belongs to and what it covers.

    Printed on the sheet rather than left to the filename: a spreadsheet gets
    renamed, forwarded and pasted into another one, and a book of movements with
    no date range on it cannot be checked against anything.
    """
    title = sheet.cell(row=1, column=1, value=labels["title"])
    title.font = Font(name="Arial", size=14, bold=True)

    since = date_from.isoformat() if date_from else labels["unbounded"]
    until = date_to.isoformat() if date_to else labels["unbounded"]

    for row, (label, value) in enumerate(
        (
            (labels["company"], company),
            (labels["range"], f"{since} — {until}"),
            (labels["generated"], generated_at.strftime("%Y-%m-%d %H:%M")),
        ),
        start=2,
    ):
        sheet.cell(row=row, column=1, value=label).font = Font(bold=True, size=9)
        sheet.cell(row=row, column=2, value=value).font = Font(size=9)


def _write_header(sheet: Worksheet, headers: list[str]) -> None:
    for column, (heading, width) in enumerate(
        zip(headers, WIDTHS, strict=True), start=1
    ):
        cell = sheet.cell(row=_HEADER_ROW, column=column, value=heading)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        sheet.column_dimensions[get_column_letter(column)].width = width


def _write_account(
    sheet: Worksheet, account: AccountLedger, labels: dict[str, str]
) -> None:
    """One account: what it carried in, what moved, where it ended.

    The opening balance is a row of its own at the top of the block, not a
    column repeated on every line. The reference project prints it as a column
    and then writes zero into it on every movement row, which makes the column
    say nothing at all.
    """
    opening = sheet.max_row + 1
    sheet.cell(row=opening, column=4, value=account.code)
    sheet.cell(row=opening, column=5, value=account.name)
    sheet.cell(row=opening, column=7, value=labels["opening"])
    _money_cell(sheet, opening, 10, account.opening_balance)

    for column in range(1, len(WIDTHS) + 1):
        cell = sheet.cell(row=opening, column=column)
        cell.fill = _ACCOUNT_FILL
        cell.font = Font(bold=True, size=10)

    for entry in account.entries:
        row = sheet.max_row + 1
        date = sheet.cell(row=row, column=1, value=entry.date)
        date.number_format = DATE_FORMAT
        # A draft has no number, but a draft is not in the books — so anything
        # reaching here is posted and numbered. The fallback is for the reader,
        # not for a case that happens.
        sheet.cell(row=row, column=2, value=entry.voucher_number or entry.voucher_id)
        sheet.cell(row=row, column=3, value=entry.description)
        sheet.cell(row=row, column=4, value=account.code)
        sheet.cell(row=row, column=5, value=account.name)
        sheet.cell(row=row, column=6, value=entry.third_party_document)
        sheet.cell(row=row, column=7, value=entry.third_party_name)
        _money_cell(sheet, row, 8, entry.debit)
        _money_cell(sheet, row, 9, entry.credit)
        _money_cell(sheet, row, 10, entry.running_balance)

    total = sheet.max_row + 1
    sheet.cell(row=total, column=7, value=labels["total"])
    _money_cell(sheet, total, 8, account.debit)
    _money_cell(sheet, total, 9, account.credit)
    _money_cell(sheet, total, 10, account.closing_balance)

    for column in range(1, len(WIDTHS) + 1):
        cell = sheet.cell(row=total, column=column)
        cell.font = Font(bold=True, size=10)
        cell.border = Border(top=_THIN)


def _write_grand_total(
    sheet: Worksheet, accounts: list[AccountLedger], labels: dict[str, str]
) -> None:
    """The one line that says whether the book is sound.

    Signed balances sum to zero when every voucher behind them balanced, so this
    is the same check the ledger screen makes, carried into the file.
    """
    row = sheet.max_row + 2
    sheet.cell(row=row, column=7, value=labels["grand_total"])
    _money_cell(sheet, row, 8, sum((a.debit for a in accounts), Decimal(0)))
    _money_cell(sheet, row, 9, sum((a.credit for a in accounts), Decimal(0)))
    _money_cell(sheet, row, 10, sum((a.closing_balance for a in accounts), Decimal(0)))

    for column in range(1, len(WIDTHS) + 1):
        sheet.cell(row=row, column=column).font = Font(bold=True, size=11)


def _money_cell(sheet: Worksheet, row: int, column: int, value: Decimal) -> None:
    """Written as a number, never as a formatted string.

    A book whose amounts are text cannot be summed in the spreadsheet it was
    exported for, which is most of the reason to export a spreadsheet.
    """
    cell = sheet.cell(row=row, column=column, value=value)
    cell.number_format = MONEY_FORMAT
