"""Composition root for the accounts module.

The only place that knows which concrete adapters back the ports. Swapping the
cache or the storage is a change here and nowhere else.
"""

from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.application.ports import AccountRepository
from app.modules.accounts.application.use_cases.import_accounts import ImportAccounts
from app.modules.accounts.application.use_cases.read_accounts import (
    GetAccount,
    GetAccountTree,
    ListAccounts,
)
from app.modules.accounts.application.use_cases.write_accounts import (
    CreateAccount,
    DeleteAccount,
    RestoreAccount,
    UpdateAccount,
)
from app.modules.accounts.infrastructure.cache import CachedAccountRepository
from app.modules.accounts.infrastructure.repository import SqlAlchemyAccountRepository
from app.modules.accounts.infrastructure.spreadsheet import OpenpyxlSpreadsheetReader
from app.shared.clock import SystemClock
from app.shared.config import settings
from app.shared.database import get_session
from app.shared.redis import get_redis

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_repository(session: SessionDep, redis: RedisDep) -> AccountRepository:
    return CachedAccountRepository(
        SqlAlchemyAccountRepository(session),
        redis,
        ttl=settings.CACHE_TTL_SECONDS,
    )


RepositoryDep = Annotated[AccountRepository, Depends(get_repository)]


def create_account(repository: RepositoryDep) -> CreateAccount:
    return CreateAccount(repository)


def update_account(repository: RepositoryDep) -> UpdateAccount:
    return UpdateAccount(repository)


def delete_account(repository: RepositoryDep) -> DeleteAccount:
    return DeleteAccount(repository, SystemClock())


def restore_account(repository: RepositoryDep) -> RestoreAccount:
    return RestoreAccount(repository)


def get_account(repository: RepositoryDep) -> GetAccount:
    return GetAccount(repository)


def list_accounts(repository: RepositoryDep) -> ListAccounts:
    return ListAccounts(repository)


def get_account_tree(repository: RepositoryDep) -> GetAccountTree:
    return GetAccountTree(repository)


def import_accounts(repository: RepositoryDep) -> ImportAccounts:
    return ImportAccounts(repository, OpenpyxlSpreadsheetReader())


CreateAccountDep = Annotated[CreateAccount, Depends(create_account)]
UpdateAccountDep = Annotated[UpdateAccount, Depends(update_account)]
DeleteAccountDep = Annotated[DeleteAccount, Depends(delete_account)]
RestoreAccountDep = Annotated[RestoreAccount, Depends(restore_account)]
GetAccountDep = Annotated[GetAccount, Depends(get_account)]
ListAccountsDep = Annotated[ListAccounts, Depends(list_accounts)]
GetAccountTreeDep = Annotated[GetAccountTree, Depends(get_account_tree)]
ImportAccountsDep = Annotated[ImportAccounts, Depends(import_accounts)]
