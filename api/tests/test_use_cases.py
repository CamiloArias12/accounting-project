"""Business rules driven directly, with no database, HTTP or Redis.

This is what the ports buy: the rules are exercised through their real code
paths in milliseconds, against in-memory doubles.
"""

from collections.abc import Sequence
from datetime import datetime
from io import BytesIO
from typing import Any

import pytest

from app.modules.accounts.application.queries import (
    AccountChanges,
    ImportOutcome,
    NewAccount,
    TreeQuery,
)
from app.modules.accounts.application.use_cases.import_accounts import (
    ExistingAccounts,
    ImportAccounts,
)
from app.modules.accounts.application.use_cases.read_accounts import GetAccountTree
from app.modules.accounts.application.use_cases.write_accounts import (
    CreateAccount,
    DeleteAccount,
    RestoreAccount,
    UpdateAccount,
)
from app.modules.accounts.domain.account import Account
from app.modules.accounts.domain.errors import (
    AccountAlreadyExists,
    AccountHasChildren,
    AccountNotDeleted,
    AccountNotFound,
    ParentAccountDeleted,
    ParentAccountMissing,
)
from app.modules.accounts.domain.puc import AccountLevel, Nature
from tests.fakes import FrozenClock, InMemoryAccountRepository, ListSpreadsheetReader

NOW = datetime(2026, 7, 25, 12, 0, 0)


def account(code: str, name: str = "X", nature: Nature = Nature.DEBIT) -> Account:
    return Account.open(code=code, name=name, nature=nature)


def branch() -> InMemoryAccountRepository:
    return InMemoryAccountRepository(
        [
            account("1", "ACTIVOS"),
            account("11", "DISPONIBLE"),
            account("1105", "CAJA"),
            account("110505", "CAJA GENERAL"),
        ]
    )


# --- create ---------------------------------------------------------------


async def test_create_derives_level_and_parent() -> None:
    repository = InMemoryAccountRepository([account("1")])

    created = await CreateAccount(repository)(
        NewAccount(code="11", name="DISPONIBLE", nature=Nature.DEBIT)
    )

    assert created.level is AccountLevel.GROUP
    assert created.parent_code == "1"


async def test_create_requires_the_parent() -> None:
    with pytest.raises(ParentAccountMissing):
        await CreateAccount(InMemoryAccountRepository())(
            NewAccount(code="11", name="DISPONIBLE", nature=Nature.DEBIT)
        )


async def test_create_rejects_a_live_duplicate() -> None:
    with pytest.raises(AccountAlreadyExists):
        await CreateAccount(branch())(
            NewAccount(code="1", name="ACTIVOS", nature=Nature.DEBIT)
        )


async def test_create_revives_a_deleted_code() -> None:
    repository = branch()
    await DeleteAccount(repository, FrozenClock(NOW))("110505")

    revived = await CreateAccount(repository)(
        NewAccount(code="110505", name="CAJA NUEVA", nature=Nature.DEBIT)
    )

    assert revived.is_deleted is False
    assert revived.name == "CAJA NUEVA"


# --- update / delete / restore -------------------------------------------


async def test_update_applies_only_what_was_given() -> None:
    repository = branch()

    updated = await UpdateAccount(repository)("1", AccountChanges(name="RENAMED"))

    assert updated.name == "RENAMED"
    assert updated.nature is Nature.DEBIT


async def test_update_of_a_missing_account() -> None:
    with pytest.raises(AccountNotFound):
        await UpdateAccount(branch())("9", AccountChanges(name="X"))


async def test_delete_stamps_the_clock() -> None:
    deleted = await DeleteAccount(branch(), FrozenClock(NOW))("110505")

    assert deleted.deleted_at == NOW


async def test_delete_is_blocked_by_live_children() -> None:
    with pytest.raises(AccountHasChildren):
        await DeleteAccount(branch(), FrozenClock(NOW))("1")


async def test_deleting_the_child_unblocks_the_parent() -> None:
    repository = branch()
    delete = DeleteAccount(repository, FrozenClock(NOW))

    await delete("110505")
    assert (await delete("1105")).is_deleted


async def test_restore_requires_it_to_be_deleted() -> None:
    with pytest.raises(AccountNotDeleted):
        await RestoreAccount(branch())("1")


async def test_restore_is_blocked_while_the_parent_is_deleted() -> None:
    repository = branch()
    delete = DeleteAccount(repository, FrozenClock(NOW))
    await delete("110505")
    await delete("1105")

    with pytest.raises(ParentAccountDeleted):
        await RestoreAccount(repository)("110505")


# --- tree -----------------------------------------------------------------


async def test_tree_nests_the_branch() -> None:
    roots = await GetAccountTree(branch())(TreeQuery())

    assert len(roots) == 1
    assert roots[0].children[0].children[0].children[0].account.code == "110505"


async def test_tree_can_start_at_a_branch() -> None:
    roots = await GetAccountTree(branch())(TreeQuery(root_code="1105"))

    assert [r.account.code for r in roots] == ["1105"]
    assert [c.account.code for c in roots[0].children] == ["110505"]


async def test_tree_respects_max_depth() -> None:
    roots = await GetAccountTree(branch())(TreeQuery(max_depth=1))

    assert roots[0].account.code == "1"
    assert [c.account.code for c in roots[0].children] == ["11"]
    assert roots[0].children[0].children == []


async def test_tree_hides_deleted_by_default() -> None:
    repository = branch()
    await DeleteAccount(repository, FrozenClock(NOW))("110505")

    roots = await GetAccountTree(repository)(TreeQuery())
    account_node = roots[0].children[0].children[0]

    assert account_node.children == []


# --- import ---------------------------------------------------------------


ROWS: list[tuple[Any, ...]] = [
    (1, "ACTIVOS", "Clase", "Debito"),
    (11, "DISPONIBLE", "Grupo", "Debito"),
    (1105, "CAJA", "Cuenta", "Debito"),
    (110505, "CAJA GENERAL", "Subcuenta", "Debito"),
]


async def importer(
    rows: Sequence[tuple[Any, ...]],
    repository: InMemoryAccountRepository | None = None,
) -> tuple[ImportOutcome, InMemoryAccountRepository]:
    repo = repository or InMemoryAccountRepository()
    use_case = ImportAccounts(repo, ListSpreadsheetReader(rows))
    return await use_case(BytesIO(b"")), repo


async def test_import_creates_the_branch() -> None:
    outcome, repository = await importer(ROWS)

    assert outcome.created == 4
    assert outcome.errors == []
    assert repository.accounts["110505"].parent_code == "1105"


async def test_import_ignores_file_order() -> None:
    outcome, repository = await importer(list(reversed(ROWS)))

    assert outcome.created == 4
    assert repository.accounts["110505"].parent_code == "1105"


async def test_import_reports_a_missing_parent() -> None:
    outcome, _ = await importer([(1105, "CAJA", "Cuenta", "Debito")])

    assert outcome.created == 0
    assert "11" in outcome.errors[0].message


async def test_import_skips_existing_by_default() -> None:
    _, repository = await importer(ROWS)
    outcome, _ = await importer(ROWS, repository)

    assert outcome.created == 0
    assert outcome.skipped == 4


async def test_import_can_update_existing() -> None:
    _, repository = await importer(ROWS)
    use_case = ImportAccounts(
        repository, ListSpreadsheetReader([(1, "RENAMED", "Clase", "Debito")])
    )

    outcome = await use_case(BytesIO(b""), on_existing=ExistingAccounts.UPDATE)

    assert outcome.updated == 1
    assert repository.accounts["1"].name == "RENAMED"


async def test_import_accepts_nature_without_accent() -> None:
    outcome, repository = await importer(
        [(2, "PASIVOS", "Clase", "Credito"), (3, "PATRIMONIO", "Clase", "CRÉDITO")]
    )

    assert outcome.created == 2
    assert repository.accounts["2"].nature is Nature.CREDIT


async def test_import_flags_a_type_contradicting_the_code() -> None:
    outcome, _ = await importer([(1, "ACTIVOS", "Grupo", "Debito")])

    assert outcome.created == 0
    assert "does not match" in outcome.errors[0].message


async def test_import_keeps_valid_rows_when_one_fails() -> None:
    outcome, _ = await importer([*ROWS, (4444, "NO PARENT", "Cuenta", "Debito")])

    assert outcome.created == 4
    assert [e.code for e in outcome.errors] == ["4444"]
