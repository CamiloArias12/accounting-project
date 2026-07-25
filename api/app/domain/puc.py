"""Rules of the Colombian chart of accounts (PUC).

Pure logic: no database, no HTTP. Everything that needs I/O lives in
`services/` and `models/`, so these rules stay trivially testable.

An account's level is not declared, it is derived from the length of its code,
and the parent is always its prefix:

    1        Class       ACTIVOS
    11       Group         DISPONIBLE
    1105     Account         CAJA
    110505   Subaccount        CAJA GENERAL
    11050501 Auxiliary           (any longer code)
"""

from __future__ import annotations

import enum
import re
from typing import Final


class Nature(enum.StrEnum):
    """Accounting nature: the side the account increases on.

    The values are Spanish because they are the contract with the source
    spreadsheet, which ships them verbatim.
    """

    DEBIT = "Debito"
    CREDIT = "Crédito"


class AccountLevel(enum.StrEnum):
    """Level within the chart of accounts hierarchy."""

    CLASS = "Clase"
    GROUP = "Grupo"
    ACCOUNT = "Cuenta"
    SUBACCOUNT = "Subcuenta"
    AUXILIARY = "Auxiliar"


# Exact code length of each level. Auxiliary is the open-ended case: any code
# longer than a subaccount.
_LENGTH_TO_LEVEL: Final[dict[int, AccountLevel]] = {
    1: AccountLevel.CLASS,
    2: AccountLevel.GROUP,
    4: AccountLevel.ACCOUNT,
    6: AccountLevel.SUBACCOUNT,
}
_SUBACCOUNT_LENGTH: Final = 6
_LENGTHS_WITH_NO_LEVEL: Final = frozenset({3, 5})
MAX_CODE_LENGTH: Final = 20

_CODE_PATTERN: Final = re.compile(r"^\d+$")


class InvalidAccountCode(ValueError):
    """The code does not follow the PUC format."""


def validate_code(code: str) -> str:
    """Normalize and validate a code, returning it ready to persist."""
    normalized = code.strip()

    if not normalized:
        raise InvalidAccountCode("The code cannot be empty")
    if not _CODE_PATTERN.match(normalized):
        raise InvalidAccountCode(f"Code {normalized!r} must contain digits only")
    if len(normalized) > MAX_CODE_LENGTH:
        raise InvalidAccountCode(
            f"Code {normalized!r} exceeds {MAX_CODE_LENGTH} digits"
        )
    if len(normalized) in _LENGTHS_WITH_NO_LEVEL:
        raise InvalidAccountCode(
            f"Code {normalized!r} has {len(normalized)} digits, which matches no "
            "PUC level (1, 2, 4, 6 or more)"
        )
    return normalized


def level_of(code: str) -> AccountLevel:
    """The level a code belongs to, given its length."""
    validate_code(code)
    return _LENGTH_TO_LEVEL.get(len(code), AccountLevel.AUXILIARY)


def parent_code_of(code: str) -> str | None:
    """The parent's code, or None for a class, which is a root of the tree."""
    level = level_of(code)

    if level is AccountLevel.CLASS:
        return None
    if level is AccountLevel.AUXILIARY:
        return code[:_SUBACCOUNT_LENGTH]

    return code[: _parent_length_of(level)]


def _parent_length_of(level: AccountLevel) -> int:
    """Code length of the parent, for levels that have a fixed length."""
    lengths = sorted(_LENGTH_TO_LEVEL)
    current = lengths.index(_length_of(level))
    return lengths[current - 1]


def _length_of(level: AccountLevel) -> int:
    for length, candidate in _LENGTH_TO_LEVEL.items():
        if candidate is level:
            return length
    raise ValueError(f"Level {level} has no fixed length")


def ancestors_of(code: str) -> list[str]:
    """Codes of every ancestor, from the class down to the direct parent."""
    chain: list[str] = []
    current = parent_code_of(code)

    while current is not None:
        chain.append(current)
        current = parent_code_of(current)

    return list(reversed(chain))


def depth_of(code: str) -> int:
    """Depth in the tree; 0 for classes. Used to order bulk inserts."""
    return len(ancestors_of(code))
