from __future__ import annotations

import enum
import re
from typing import Final


class PersonType(enum.StrEnum):
    """Whether the third party is a human being or an organization."""

    NATURAL = "Natural person"
    LEGAL = "Legal entity"


class DocumentType(enum.StrEnum):
    CITIZEN_ID = "Citizen ID"
    FOREIGNER_ID = "Foreigner ID"
    NIT = "NIT"
    MINOR_ID = "Minor ID"
    PASSPORT = "Passport"
    BIRTH_CERTIFICATE = "Birth certificate"
    NUIP = "NUIP"


class Gender(enum.StrEnum):
    MALE = "Male"
    FEMALE = "Female"


class MaritalStatus(enum.StrEnum):
    SINGLE = "Single"
    MARRIED = "Married"
    DOMESTIC_PARTNERSHIP = "Domestic partnership"
    FEMALE_HEAD_OF_HOUSEHOLD = "Female head of household"
    OTHER = "Other"


class HousingType(enum.StrEnum):
    OWNED = "Owned"
    RENTED = "Rented"
    FAMILY = "Family owned"
    OTHER = "Other"


class EducationLevel(enum.StrEnum):
    PRIMARY = "Primary"
    SECONDARY = "Secondary"
    TECHNICAL = "Technical"
    UNIVERSITY = "University"
    POSTGRADUATE = "Postgraduate"


class TaxRegime(enum.StrEnum):
    """VAT standing."""

    NOT_VAT_RESPONSIBLE = "Not VAT responsible"
    VAT_RESPONSIBLE = "VAT responsible"
    SIMPLIFIED = "Simplified"
    SUBSIDIZED = "Subsidized"


class CompanyType(enum.StrEnum):
    """Legal form of an organization."""

    CORPORATION = "Corporation"
    LIMITED_LIABILITY = "Limited liability company"
    SIMPLIFIED_JOINT_STOCK = "Simplified joint-stock company"
    LIMITED_PARTNERSHIP_BY_SHARES = "Limited partnership by shares"
    DE_FACTO_PARTNERSHIP = "De facto partnership"
    SOLE_PROPRIETORSHIP = "Sole proprietorship"
    COOPERATIVE = "Cooperative"
    NONPROFIT = "Nonprofit organization"
    FOUNDATION = "Foundation"
    TRADE_ASSOCIATION = "Trade association"
    CONSORTIUM = "Consortium"
    TEMPORARY_JOINT_VENTURE = "Temporary joint venture"


DIAN_CODES: Final[dict[DocumentType, str]] = {}


_ALPHANUMERIC_DOCUMENTS: Final = frozenset({DocumentType.PASSPORT})

MAX_DOCUMENT_LENGTH: Final = 20
MAX_NIT_LENGTH: Final = 15

_DV_WEIGHTS: Final = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)

_DIGITS = re.compile(r"^\d+$")
_ALPHANUMERIC = re.compile(r"^[A-Z0-9]+$")
_NOISE = re.compile(r"[.\s]")


class InvalidDocument(ValueError):
    """The document does not follow the rules of its type."""


def normalize_document(number: str, document_type: DocumentType) -> str:
    normalized = _NOISE.sub("", number).strip().upper()

    if not normalized:
        raise InvalidDocument("The document number cannot be empty")

    if "-" in normalized:
        raise InvalidDocument(
            f"Document {number!r} must not include the check digit; enter it in "
            "its own field"
        )

    if len(normalized) > MAX_DOCUMENT_LENGTH:
        raise InvalidDocument(
            f"Document {normalized!r} exceeds {MAX_DOCUMENT_LENGTH} characters"
        )

    alphanumeric = document_type in _ALPHANUMERIC_DOCUMENTS
    if not (_ALPHANUMERIC if alphanumeric else _DIGITS).match(normalized):
        expected = "letters and digits" if alphanumeric else "digits only"
        raise InvalidDocument(f"A {document_type.value} must contain {expected}")

    if document_type is DocumentType.NIT and len(normalized) > MAX_NIT_LENGTH:
        raise InvalidDocument(f"A NIT cannot exceed {MAX_NIT_LENGTH} digits")

    return normalized


def compute_check_digit(nit: str) -> int:
    normalized = normalize_document(nit, DocumentType.NIT)

    total = sum(
        int(digit) * weight
        for digit, weight in zip(reversed(normalized), _DV_WEIGHTS, strict=False)
    )
    remainder = total % 11

    return remainder if remainder < 2 else 11 - remainder


def validate_check_digit(nit: str, check_digit: int) -> int:
    expected = compute_check_digit(nit)
    if check_digit != expected:
        raise InvalidDocument(
            f"The check digit of NIT {nit} is {expected}, not {check_digit}"
        )
    return check_digit


def requires_check_digit(document_type: DocumentType) -> bool:
    return document_type is DocumentType.NIT


DIAN_CODES.update(
    {
        DocumentType.BIRTH_CERTIFICATE: "11",
        DocumentType.MINOR_ID: "12",
        DocumentType.CITIZEN_ID: "13",
        DocumentType.NUIP: "13",
        DocumentType.FOREIGNER_ID: "22",
        DocumentType.NIT: "31",
        DocumentType.PASSPORT: "41",
    }
)


def dian_code(document_type: DocumentType) -> str:
    return DIAN_CODES[document_type]
