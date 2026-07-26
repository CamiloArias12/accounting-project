"""Rules about who a third party is: document types, closed lists, and the NIT
check digit.

The innermost layer, like `accounts.puc`: no database, no HTTP, no framework.

The closed lists are Python enums rather than a lookup table because the code
branches on them — the check digit rule has to know a document *is* a NIT, which
an id looked up by name cannot guarantee.
"""

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
    """VAT standing. It applies to both kinds of person: a natural person who
    trades is just as much a `responsable del IVA` as a company is.
    """

    NOT_VAT_RESPONSIBLE = "Not VAT responsible"
    VAT_RESPONSIBLE = "VAT responsible"
    SIMPLIFIED = "Simplified"
    SUBSIDIZED = "Subsidized"


class CompanyType(enum.StrEnum):
    """Legal form of an organization. Only meaningful for a legal entity."""

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


#: DIAN's own codes for document types, which is what a fiscal file carries.
#: Our member names are for the code to read; these two digits are what the
#: DIAN parses, and printing "Citizen ID" in an exógena file would be rejected.
DIAN_CODES: Final[dict[DocumentType, str]] = {}


#: The only type allowed to hold letters; every other one is numeric.
_ALPHANUMERIC_DOCUMENTS: Final = frozenset({DocumentType.PASSPORT})

MAX_DOCUMENT_LENGTH: Final = 20
#: Beyond this the weight table runs out, and no real NIT comes close.
MAX_NIT_LENGTH: Final = 15

#: DIAN weights, applied to the NIT's digits from right to left.
_DV_WEIGHTS: Final = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)

_DIGITS = re.compile(r"^\d+$")
_ALPHANUMERIC = re.compile(r"^[A-Z0-9]+$")
#: Removed on input: thousands separators and spacing people paste in.
_NOISE = re.compile(r"[.\s]")


class InvalidDocument(ValueError):
    """The document does not follow the rules of its type."""


def normalize_document(number: str, document_type: DocumentType) -> str:
    """Clean up a document number and check it against the rules of its type."""
    normalized = _NOISE.sub("", number).strip().upper()

    if not normalized:
        raise InvalidDocument("The document number cannot be empty")

    if "-" in normalized:
        # Splitting it here would quietly turn "900123456-7" into a number and a
        # check digit the caller never asked for. The check digit has its own
        # field.
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
    """The DIAN check digit of a NIT.

    Each digit is weighted from right to left; the remainder modulo 11 is the
    digit itself when it is 0 or 1, and 11 minus it otherwise.
    """
    normalized = normalize_document(nit, DocumentType.NIT)

    total = sum(
        int(digit) * weight
        for digit, weight in zip(reversed(normalized), _DV_WEIGHTS, strict=False)
    )
    remainder = total % 11

    return remainder if remainder < 2 else 11 - remainder


def validate_check_digit(nit: str, check_digit: int) -> int:
    """Check a check digit, returning it so callers can assign the result."""
    expected = compute_check_digit(nit)
    if check_digit != expected:
        raise InvalidDocument(
            f"The check digit of NIT {nit} is {expected}, not {check_digit}"
        )
    return check_digit


def requires_check_digit(document_type: DocumentType) -> bool:
    """Only the NIT carries a check digit."""
    return document_type is DocumentType.NIT


# Filled after the class so the enum members exist. The codes come from the
# DIAN's resolution: 11 registro civil, 12 tarjeta de identidad, 13 cédula de
# ciudadanía, 22 cédula de extranjería, 31 NIT, 41 pasaporte.
DIAN_CODES.update(
    {
        DocumentType.BIRTH_CERTIFICATE: "11",
        DocumentType.MINOR_ID: "12",
        DocumentType.CITIZEN_ID: "13",
        # The NUIP is the number printed on a citizen's own document, so it
        # reports under the same code rather than one of its own.
        DocumentType.NUIP: "13",
        DocumentType.FOREIGNER_ID: "22",
        DocumentType.NIT: "31",
        DocumentType.PASSPORT: "41",
    }
)


def dian_code(document_type: DocumentType) -> str:
    """The two digits the DIAN expects for a document type."""
    return DIAN_CODES[document_type]
