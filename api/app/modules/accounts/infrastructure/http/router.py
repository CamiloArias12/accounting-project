"""HTTP delivery for accounts.

Deliberately thin: parse, call one use case, shape the response. Any `if` that
encodes a business rule belongs in the application layer instead.
"""

from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.modules.accounts.application.queries import (
    MAX_PAGE_SIZE,
    AccountChanges,
    AccountFilters,
    NewAccount,
    TreeQuery,
)
from app.modules.accounts.application.use_cases.import_accounts import ExistingAccounts
from app.modules.accounts.domain.puc import AccountLevel
from app.modules.accounts.infrastructure.http.dependencies import (
    CreateAccountDep,
    DeleteAccountDep,
    GetAccountDep,
    GetAccountTreeDep,
    ImportAccountsDep,
    ListAccountsDep,
    RestoreAccountDep,
    UpdateAccountDep,
)
from app.modules.accounts.infrastructure.http.schemas import (
    AccountCreateRequest,
    AccountNodeResponse,
    AccountResponse,
    AccountUpdateRequest,
    ImportResponse,
)
from app.modules.auth.infrastructure.http.dependencies import CurrentUserDep

router = APIRouter(prefix="/accounts", tags=["accounts"])

LevelFilter = Annotated[AccountLevel | None, Query(description="Filter by level")]
ParentFilter = Annotated[str | None, Query(description="Children of this account")]
SearchFilter = Annotated[str | None, Query(description="Match code or name")]
ActiveFilter = Annotated[bool | None, Query(description="Filter by active flag")]
IncludeDeleted = Annotated[bool, Query(description="Include soft-deleted accounts")]
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
RootCode = Annotated[str | None, Query(description="Start the tree at this account")]
MaxDepth = Annotated[int | None, Query(ge=0, description="Levels below the root")]


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    use_case: ListAccountsDep,
    level: LevelFilter = None,
    parent_code: ParentFilter = None,
    search: SearchFilter = None,
    only_active: ActiveFilter = None,
    include_deleted: IncludeDeleted = False,
    skip: Skip = 0,
    limit: Limit = 100,
) -> list[AccountResponse]:
    accounts = await use_case(
        AccountFilters(
            level=level,
            parent_code=parent_code,
            search=search,
            only_active=only_active,
            include_deleted=include_deleted,
            skip=skip,
            limit=limit,
        )
    )
    return [AccountResponse.of(account) for account in accounts]


@router.get("/tree", response_model=list[AccountNodeResponse])
async def account_tree(
    use_case: GetAccountTreeDep,
    root_code: RootCode = None,
    max_depth: MaxDepth = None,
    include_deleted: IncludeDeleted = False,
) -> list[AccountNodeResponse]:
    """The chart of accounts, or one branch of it.

    `root_code` and `max_depth` exist so a caller that only renders the top
    levels does not download the whole chart.
    """
    nodes = await use_case(
        TreeQuery(
            root_code=root_code,
            max_depth=max_depth,
            include_deleted=include_deleted,
        )
    )
    return [AccountNodeResponse.of_node(node) for node in nodes]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreateRequest,
    use_case: CreateAccountDep,
    _: CurrentUserDep,
) -> AccountResponse:
    account = await use_case(
        NewAccount(
            code=payload.code,
            name=payload.name,
            nature=payload.nature,
            is_active=payload.is_active,
        )
    )
    return AccountResponse.of(account)


@router.post("/import", response_model=ImportResponse)
async def import_accounts(
    use_case: ImportAccountsDep,
    _: CurrentUserDep,
    file: Annotated[
        UploadFile,
        File(description="PUC spreadsheet: Codigo, Nombre, Tipo, Naturaleza"),
    ],
    on_existing: Annotated[
        ExistingAccounts,
        Query(description="What to do with accounts that already exist"),
    ] = ExistingAccounts.SKIP,
) -> ImportResponse:
    outcome = await use_case(file.file, on_existing=on_existing)
    return ImportResponse.of(outcome)


@router.get("/{code}", response_model=AccountResponse)
async def get_account(
    code: str,
    use_case: GetAccountDep,
    include_deleted: IncludeDeleted = False,
) -> AccountResponse:
    account = await use_case(code, include_deleted=include_deleted)
    return AccountResponse.of(account)


@router.patch("/{code}", response_model=AccountResponse)
async def update_account(
    code: str,
    payload: AccountUpdateRequest,
    use_case: UpdateAccountDep,
    _: CurrentUserDep,
) -> AccountResponse:
    account = await use_case(
        code,
        AccountChanges(
            name=payload.name,
            nature=payload.nature,
            is_active=payload.is_active,
        ),
    )
    return AccountResponse.of(account)


@router.delete("/{code}", response_model=AccountResponse)
async def delete_account(
    code: str, use_case: DeleteAccountDep, _: CurrentUserDep
) -> AccountResponse:
    """Soft delete: the row is kept and stamped with `deleted_at`."""
    account = await use_case(code)
    return AccountResponse.of(account)


@router.post("/{code}/restore", response_model=AccountResponse)
async def restore_account(
    code: str, use_case: RestoreAccountDep, _: CurrentUserDep
) -> AccountResponse:
    account = await use_case(code)
    return AccountResponse.of(account)
