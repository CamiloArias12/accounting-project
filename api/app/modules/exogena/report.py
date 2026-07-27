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
    """The reporting company's own NIT does not check out."""


@dataclass(frozen=True, slots=True)
class Filer:
    """Whose report this is."""

    nit: str
    check_digit: int
    legal_name: str
    year: int

    @classmethod
    def of(cls, *, nit: str, legal_name: str, year: int) -> Filer:
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
        return Totals(
            count=len(self.rows),
            gross=sum((row.rounded_gross for row in self.rows), Decimal(0)),
            withheld=sum((row.rounded_withheld for row in self.rows), Decimal(0)),
        )

    def to_xml(self) -> str:
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
    return value.quantize(PESO, rounding=ROUND_HALF_UP)


def _plain(value: Decimal) -> str:
    return str(int(value))
