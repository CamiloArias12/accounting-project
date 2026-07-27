from __future__ import annotations

import enum
import re
from typing import Final


class Nature(enum.StrEnum):
    """Accounting nature: the side the account increases on."""

    DEBIT = "Debito"
    CREDIT = "Crédito"


class AccountLevel(enum.StrEnum):
    """Level within the chart of accounts hierarchy."""

    CLASS = "Clase"
    GROUP = "Grupo"
    ACCOUNT = "Cuenta"
    SUBACCOUNT = "Subcuenta"
    AUXILIARY = "Auxiliar"


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
    validate_code(code)
    return _LENGTH_TO_LEVEL.get(len(code), AccountLevel.AUXILIARY)


def parent_code_of(code: str) -> str | None:
    level = level_of(code)

    if level is AccountLevel.CLASS:
        return None
    if level is AccountLevel.AUXILIARY:
        return code[:_SUBACCOUNT_LENGTH]

    return code[: _parent_length_of(level)]


def _parent_length_of(level: AccountLevel) -> int:
    lengths = sorted(_LENGTH_TO_LEVEL)
    current = lengths.index(_length_of(level))
    return lengths[current - 1]


def _length_of(level: AccountLevel) -> int:
    for length, candidate in _LENGTH_TO_LEVEL.items():
        if candidate is level:
            return length
    raise ValueError(f"Level {level} has no fixed length")


def ancestors_of(code: str) -> list[str]:
    chain: list[str] = []
    current = parent_code_of(code)

    while current is not None:
        chain.append(current)
        current = parent_code_of(current)

    return list(reversed(chain))


def depth_of(code: str) -> int:
    return len(ancestors_of(code))


def code_lengths_up_to(max_depth: int) -> list[int]:
    fixed = sorted(_LENGTH_TO_LEVEL)
    if max_depth < len(fixed):
        return fixed[: max_depth + 1]

    return [*fixed, *range(_SUBACCOUNT_LENGTH + 1, MAX_CODE_LENGTH + 1)]
