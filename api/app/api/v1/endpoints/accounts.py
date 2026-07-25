from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.deps import AccountServiceDep, PucImporterDep
from app.domain.puc import AccountLevel
from app.models.account import Account
from app.schemas.account import (
    AccountCreate,
    AccountNode,
    AccountRead,
    AccountUpdate,
    ImportResult,
)
from app.services.puc_import import ExistingAccounts

router = APIRouter(prefix="/accounts", tags=["accounts"])

LevelFilter = Annotated[AccountLevel | None, Query(description="Filter by level")]
ParentFilter = Annotated[str | None, Query(description="Children of this account")]
SearchFilter = Annotated[str | None, Query(description="Match code or name")]
ActiveFilter = Annotated[bool | None, Query(description="Filter by active flag")]
IncludeDeleted = Annotated[bool, Query(description="Include soft-deleted accounts")]
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    service: AccountServiceDep,
    level: LevelFilter = None,
    parent_code: ParentFilter = None,
    search: SearchFilter = None,
    only_active: ActiveFilter = None,
    include_deleted: IncludeDeleted = False,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Sequence[Account]:
    return await service.find_many(
        level=level,
        parent_code=parent_code,
        search=search,
        only_active=only_active,
        include_deleted=include_deleted,
        skip=skip,
        limit=limit,
    )


@router.get("/tree", response_model=list[AccountNode])
async def account_tree(
    service: AccountServiceDep,
    include_deleted: IncludeDeleted = False,
) -> list[AccountNode]:
    """The whole chart of accounts, nested from the classes down."""
    return await service.tree(include_deleted=include_deleted)


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, service: AccountServiceDep) -> Account:
    return await service.create(payload)


@router.post("/import", response_model=ImportResult)
async def import_accounts(
    importer: PucImporterDep,
    file: Annotated[
        UploadFile,
        File(description="PUC spreadsheet: Codigo, Nombre, Tipo, Naturaleza"),
    ],
    on_existing: Annotated[
        ExistingAccounts,
        Query(description="What to do with accounts that already exist"),
    ] = ExistingAccounts.SKIP,
) -> ImportResult:
    return await importer.import_from_file(file.file, on_existing=on_existing)


@router.get("/{code}", response_model=AccountRead)
async def get_account(
    code: str,
    service: AccountServiceDep,
    include_deleted: IncludeDeleted = False,
) -> Account:
    return await service.get(code, include_deleted=include_deleted)


@router.patch("/{code}", response_model=AccountRead)
async def update_account(
    code: str, payload: AccountUpdate, service: AccountServiceDep
) -> Account:
    return await service.update(code, payload)


@router.delete("/{code}", response_model=AccountRead)
async def delete_account(code: str, service: AccountServiceDep) -> Account:
    """Soft delete: the row is kept and stamped with `deleted_at`."""
    return await service.delete(code)


@router.post("/{code}/restore", response_model=AccountRead)
async def restore_account(code: str, service: AccountServiceDep) -> Account:
    return await service.restore(code)
