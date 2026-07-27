from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.cache import AccountTreeCache
from app.modules.accounts.importer import AccountImporter, ExistingAccounts
from app.modules.accounts.models import Account
from app.modules.accounts.puc import AccountLevel
from app.modules.accounts.schemas import (
    AccountCreate,
    AccountNode,
    AccountRead,
    AccountUpdate,
    ImportResult,
)
from app.modules.accounts.service import AccountService
from app.modules.auth.dependencies import current_user
from app.shared.config import settings
from app.shared.database import get_session
from app.shared.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page
from app.shared.redis import get_redis

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_cache(redis: RedisDep) -> AccountTreeCache:
    return AccountTreeCache(redis, ttl=settings.CACHE_TTL_SECONDS)


CacheDep = Annotated[AccountTreeCache, Depends(get_cache)]


def get_service(session: SessionDep, cache: CacheDep) -> AccountService:
    return AccountService(session, cache)


def get_importer(session: SessionDep, cache: CacheDep) -> AccountImporter:
    return AccountImporter(session, cache)


ServiceDep = Annotated[AccountService, Depends(get_service)]
ImporterDep = Annotated[AccountImporter, Depends(get_importer)]

IncludeDeleted = Annotated[bool, Query(description="Include soft-deleted accounts")]


@router.get("", response_model=Page[AccountRead])
async def list_accounts(
    service: ServiceDep,
    level: Annotated[AccountLevel | None, Query()] = None,
    parent_code: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query(description="Match code or name")] = None,
    only_active: Annotated[bool | None, Query()] = None,
    only_postable: Annotated[
        bool, Query(description="Only accounts entries may be posted to")
    ] = False,
    include_deleted: IncludeDeleted = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> Page[AccountRead]:
    items, total = await service.find_many(
        level=level,
        parent_code=parent_code,
        search=search,
        only_active=only_active,
        only_postable=only_postable,
        include_deleted=include_deleted,
        skip=skip,
        limit=limit,
    )
    return Page[AccountRead](items=list(items), total=total, skip=skip, limit=limit)


@router.get("/tree", response_model=list[AccountNode])
async def account_tree(
    service: ServiceDep,
    root_code: Annotated[str | None, Query(description="Start here")] = None,
    max_depth: Annotated[int | None, Query(ge=0, description="Levels below")] = None,
    include_deleted: IncludeDeleted = False,
) -> list[AccountNode]:
    return await service.tree(
        root_code=root_code, max_depth=max_depth, include_deleted=include_deleted
    )


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, service: ServiceDep) -> Account:
    return await service.create(payload)


@router.post("/import", response_model=ImportResult)
async def import_accounts(
    importer: ImporterDep,
    file: Annotated[
        UploadFile,
        File(description="PUC spreadsheet: Codigo, Nombre, Tipo, Naturaleza"),
    ],
    on_existing: Annotated[ExistingAccounts, Query()] = ExistingAccounts.SKIP,
) -> ImportResult:
    return await importer.run(file.file, on_existing=on_existing)


@router.get("/{code}", response_model=AccountRead)
async def get_account(
    code: str, service: ServiceDep, include_deleted: IncludeDeleted = False
) -> Account:
    return await service.get(code, include_deleted=include_deleted)


@router.patch("/{code}", response_model=AccountRead)
async def update_account(
    code: str, payload: AccountUpdate, service: ServiceDep
) -> Account:
    return await service.update(code, payload)


@router.delete("/{code}", response_model=AccountRead)
async def delete_account(code: str, service: ServiceDep) -> Account:
    return await service.delete(code)


@router.post("/{code}/restore", response_model=AccountRead)
async def restore_account(code: str, service: ServiceDep) -> Account:
    return await service.restore(code)
