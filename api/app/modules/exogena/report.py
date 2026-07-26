"""The exógena report: what goes in it, and the XML it becomes.

The innermost layer, like `accounts.puc` and `vouchers.posting`: no database,
no HTTP, no framework. Given the rows and the filer, this builds the
document and nothing else — which is what makes the totals easy to prove.

Amounts are whole pesos. The DIAN takes no cents, and rounding each row before
adding them is what keeps the control totals equal to the sum of the rows that
were actually written: rounding the sum instead can differ by a peso or two,
and a file whose totals do not reconcile is rejected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from xml.etree import ElementTree as ET

from app.modules.third_parties.documents import (
    DocumentType,
    compute_check_digit,
    normalize_document,
)

VERSION = "1.0"
PESO = Decimal("1")


class ExogenaError(ValueError):
    """The report cannot be built as asked."""


class InvalidFiler(ExogenaError):
    """The reporting company's own NIT does not check out.

    Refused before anything is written: a file filed under a mistyped NIT is
    filed against somebody else.
    """


@dataclass(frozen=True, slots=True)
class Filer:
    """Whose report this is."""

    nit: str
    check_digit: int
    legal_name: str
    year: int

    @classmethod
    def of(cls, *, nit: str, legal_name: str, year: int) -> Filer:
        """Build it from the configured NIT, verifying the check digit.

        The NIT may be configured as `900123456-7`, which is how people write
        it; the digit after the dash is checked rather than trusted.
        """
        raw, _, given = nit.partition("-")

        try:
            number = normalize_document(raw, DocumentType.NIT)
            expected = compute_check_digit(number)
        except ValueError as exc:
            raise InvalidFiler(str(exc)) from exc

        if given and int(given) != expected:
            raise InvalidFiler(
                f"The check digit of the filer's NIT {number} is "
                f"{expected}, not {given}"
            )

        return cls(
            nit=number,
            check_digit=expected,
            legal_name=legal_name.strip(),
            year=year,
        )


@dataclass(frozen=True, slots=True)
class Row:
    """One third party under one concept."""

    document_type: str
    document_number: str
    name: str
    concept: str
    gross: Decimal
    withheld: Decimal

    @property
    def rounded_gross(self) -> Decimal:
        return _pesos(self.gross)

    @property
    def rounded_withheld(self) -> Decimal:
        return _pesos(self.withheld)


@dataclass(frozen=True, slots=True)
class Totals:
    count: int
    gross: Decimal
    withheld: Decimal


@dataclass(slots=True)
class Report:
    filer: Filer
    rows: list[Row] = field(default_factory=list)

    @property
    def totals(self) -> Totals:
        """Added from the rounded rows, so the file reconciles with itself."""
        return Totals(
            count=len(self.rows),
            gross=sum((row.rounded_gross for row in self.rows), Decimal(0)),
            withheld=sum((row.rounded_withheld for row in self.rows), Decimal(0)),
        )

    def to_xml(self) -> str:
        """The document, with the tag names the DIAN mandates.

        Those are Spanish and stay Spanish: `InformacionExogena`, `Informante`,
        `valorBruto` and the rest are the file format, not a naming choice.
        Everything on this side of the boundary — `Filer`, `Row`, `gross`,
        `withheld` — reads like the rest of the codebase.
        """
        root = ET.Element("InformacionExogena", {"version": VERSION})

        ET.SubElement(
            root,
            "Informante",
            {
                "nit": self.filer.nit,
                "dv": str(self.filer.check_digit),
                "razonSocial": self.filer.legal_name,
                "anioGravable": str(self.filer.year),
            },
        )

        registros = ET.SubElement(root, "Registros")
        for row in self.rows:
            ET.SubElement(
                registros,
                "Registro",
                {
                    "tipoDoc": row.document_type,
                    "numDoc": row.document_number,
                    "nombre": row.name,
                    "concepto": row.concept,
                    "valorBruto": _plain(row.rounded_gross),
                    "valorRetencion": _plain(row.rounded_withheld),
                },
            )

        totals = self.totals
        ET.SubElement(
            root,
            "Totales",
            {
                "registros": str(totals.count),
                "totalValorBruto": _plain(totals.gross),
                "totalRetencion": _plain(totals.withheld),
            },
        )

        ET.indent(root, space="  ")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            + ET.tostring(root, encoding="unicode")
            + "\n"
        )


def _pesos(value: Decimal) -> Decimal:
    """Whole pesos, rounded half up. The DIAN takes no cents."""
    return value.quantize(PESO, rounding=ROUND_HALF_UP)


def _plain(value: Decimal) -> str:
    """No exponent and no decimal point, whatever the Decimal is carrying."""
    return str(int(value))
