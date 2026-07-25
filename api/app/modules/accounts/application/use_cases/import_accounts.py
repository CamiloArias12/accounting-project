"""Import of the chart of accounts from a spreadsheet.

The file holds one row per account with the columns `Codigo, Nombre, Tipo,
Naturaleza`. `Tipo` is redundant — the level is derived from the code — so it is
only used to flag inconsistencies, never as the source of truth.

Reading the file is delegated to a `SpreadsheetReader` port, so this use case
never imports openpyxl and can be tested with a list of tuples.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import IO, Final

from app.modules.accounts.application.ports import AccountRepository, SpreadsheetReader
from app.modules.accounts.application.queries import ImportOutcome, RowFailure
from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.puc import (
    AccountLevel,
    InvalidAccountCode,
    Nature,
    depth_of,
    level_of,
    parent_code_of,
    validate_code,
)

#: Rows per database round trip. Bounds both the parameter count of the
#: existence lookup and how many entities are held at once.
BATCH_SIZE: Final = 500


class ExistingAccounts(enum.StrEnum):
    """What to do with accounts that are already stored."""

    SKIP = "skip"
    UPDATE = "update"


@dataclass(frozen=True, slots=True)
class ParsedRow:
    number: int
    code: str
    name: str
    nature: Nature


class ImportAccounts:
    def __init__(
        self, repository: AccountRepository, reader: SpreadsheetReader
    ) -> None:
        self._repository = repository
        self._reader = reader

    async def __call__(
        self,
        file: IO[bytes],
        *,
        on_existing: ExistingAccounts = ExistingAccounts.SKIP,
    ) -> ImportOutcome:
        rows, errors = self._parse(file)

        # Shallowest first, so a parent always lands before its children
        # whatever order the file happens to use.
        rows.sort(key=lambda row: (depth_of(row.code), row.code))

        incoming = {row.code for row in rows}
        created = updated = skipped = 0

        for batch in _batched(rows, BATCH_SIZE):
            # Soft-deleted rows still hold the primary key, so they count as known.
            known = await self._repository.existing_codes(
                (row.code for row in batch), include_deleted=True
            )
            pending: list[Account] = []

            for row in batch:
                parent_code = parent_code_of(row.code)
                missing_parent = (
                    parent_code is not None
                    and parent_code not in incoming
                    and not await self._repository.exists(parent_code)
                )
                if missing_parent:
                    errors.append(
                        RowFailure(
                            row=row.number,
                            code=row.code,
                            message=f"Missing parent account {parent_code}",
                        )
                    )
                    continue

                if row.code in known:
                    if on_existing is ExistingAccounts.SKIP:
                        skipped += 1
                        continue
                    if await self._update(row):
                        updated += 1
                    continue

                pending.append(
                    Account.open(code=row.code, name=row.name, nature=row.nature)
                )

            created += await self._repository.add_many(pending)

        return ImportOutcome(
            created=created, updated=updated, skipped=skipped, errors=errors
        )

    async def _update(self, row: ParsedRow) -> bool:
        account = await self._repository.get(row.code, include_deleted=True)
        if account is None:
            return False

        account.rename(row.name)
        account.change_nature(row.nature)
        # Re-importing an account restores it: the file is the authority on
        # which accounts the chart contains.
        account.restore()
        await self._repository.save(account)
        return True

    def _parse(self, file: IO[bytes]) -> tuple[list[ParsedRow], list[RowFailure]]:
        rows: list[ParsedRow] = []
        errors: list[RowFailure] = []
        seen: set[str] = set()

        for row in self._reader.rows(file):
            raw_code, raw_name, raw_type, raw_nature = row.values

            if raw_code is None or str(raw_code).strip() == "":
                continue

            code = str(raw_code).strip()
            try:
                code = validate_code(code)
            except InvalidAccountCode as exc:
                errors.append(RowFailure(row=row.number, code=code, message=str(exc)))
                continue

            if code in seen:
                errors.append(
                    RowFailure(
                        row=row.number, code=code, message="Duplicate code in the file"
                    )
                )
                continue

            name = str(raw_name).strip() if raw_name is not None else ""
            if not name:
                errors.append(
                    RowFailure(row=row.number, code=code, message="Missing name")
                )
                continue

            nature = _parse_nature(raw_nature)
            if nature is None:
                errors.append(
                    RowFailure(
                        row=row.number,
                        code=code,
                        message=f"Unrecognized nature: {raw_nature!r}",
                    )
                )
                continue

            if (mismatch := _level_mismatch(code, raw_type)) is not None:
                errors.append(RowFailure(row=row.number, code=code, message=mismatch))
                continue

            seen.add(code)
            rows.append(
                ParsedRow(number=row.number, code=code, name=name, nature=nature)
            )

        return rows, errors


def _batched(rows: list[ParsedRow], size: int) -> list[list[ParsedRow]]:
    return [rows[start : start + size] for start in range(0, len(rows), size)]


def _parse_nature(raw: object) -> Nature | None:
    if raw is None:
        return None

    # The file ships "Debito" and "Crédito"; any accent or casing is accepted so
    # hand-edited sheets keep working.
    normalized = str(raw).strip().lower().replace("é", "e").replace("í", "i")

    if normalized.startswith("deb"):
        return Nature.DEBIT
    if normalized.startswith("cred"):
        return Nature.CREDIT
    return None


def _level_mismatch(code: str, raw_type: object) -> str | None:
    """Flag a `Tipo` column that contradicts the code, which is authoritative."""
    if raw_type is None or str(raw_type).strip() == "":
        return None

    declared = str(raw_type).strip().lower()
    actual = level_of(code)
    if declared == actual.value.lower():
        return None

    if declared not in {level.value.lower() for level in AccountLevel}:
        return f"Unrecognized type: {raw_type!r}"

    return (
        f"Declared type ({raw_type}) does not match the one implied by a "
        f"{len(code)}-digit code ({actual.value})"
    )
