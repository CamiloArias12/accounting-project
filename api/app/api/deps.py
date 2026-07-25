from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import get_redis
from app.db.session import get_session
from app.repositories.account import AccountRepository
from app.services.account import AccountService
from app.services.puc_import import PucImporter

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_account_repository(session: SessionDep) -> AccountRepository:
    return AccountRepository(session)


AccountRepositoryDep = Annotated[AccountRepository, Depends(get_account_repository)]


def get_account_service(repository: AccountRepositoryDep) -> AccountService:
    return AccountService(repository)


def get_puc_importer(repository: AccountRepositoryDep) -> PucImporter:
    return PucImporter(repository)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
PucImporterDep = Annotated[PucImporter, Depends(get_puc_importer)]
