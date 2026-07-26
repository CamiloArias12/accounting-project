from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.third_parties.documents import DocumentType, PersonType
from app.modules.third_parties.models import ThirdParty
from app.modules.third_parties.schemas import (
    ThirdPartyCreate,
    ThirdPartyRead,
    ThirdPartyUpdate,
)
from app.modules.third_parties.service import ThirdPartyService
from app.shared.database import get_session
from app.shared.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page

# Applied to the whole router: an endpoint added later is protected by being
# here, instead of by remembering to annotate it.
router = APIRouter(
    prefix="/third-parties",
    tags=["third parties"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_service(session: SessionDep) -> ThirdPartyService:
    return ThirdPartyService(session)


ServiceDep = Annotated[ThirdPartyService, Depends(get_service)]
IncludeDeleted = Annotated[bool, Query(description="Include soft-deleted rows")]


@router.get("", response_model=Page[ThirdPartyRead])
async def list_third_parties(
    service: ServiceDep,
    person_type: Annotated[PersonType | None, Query()] = None,
    document_type: Annotated[DocumentType | None, Query()] = None,
    search: Annotated[
        str | None, Query(description="Match document number, names or legal name")
    ] = None,
    only_active: Annotated[bool | None, Query()] = None,
    include_deleted: IncludeDeleted = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> Page[ThirdPartyRead]:
    items, total = await service.find_many(
        person_type=person_type,
        document_type=document_type,
        search=search,
        only_active=only_active,
        include_deleted=include_deleted,
        skip=skip,
        limit=limit,
    )
    return Page[ThirdPartyRead](items=list(items), total=total, skip=skip, limit=limit)


@router.post("", response_model=ThirdPartyRead, status_code=status.HTTP_201_CREATED)
async def create_third_party(
    payload: Annotated[ThirdPartyCreate, Body()], service: ServiceDep
) -> ThirdParty:
    """Register a third party.

    The body is one of two shapes, chosen by `person_type`: a natural person
    carries names and a birthplace, a legal entity a legal name and its
    representative.
    """
    return await service.create(payload)


@router.get("/{third_party_id}", response_model=ThirdPartyRead)
async def get_third_party(
    third_party_id: int, service: ServiceDep, include_deleted: IncludeDeleted = False
) -> ThirdParty:
    return await service.get(third_party_id, include_deleted=include_deleted)


@router.patch("/{third_party_id}", response_model=ThirdPartyRead)
async def update_third_party(
    third_party_id: int, payload: ThirdPartyUpdate, service: ServiceDep
) -> ThirdParty:
    return await service.update(third_party_id, payload)


@router.delete("/{third_party_id}", response_model=ThirdPartyRead)
async def delete_third_party(third_party_id: int, service: ServiceDep) -> ThirdParty:
    """Soft delete: the row is kept and stamped with `deleted_at`."""
    return await service.delete(third_party_id)


@router.post("/{third_party_id}/restore", response_model=ThirdPartyRead)
async def restore_third_party(third_party_id: int, service: ServiceDep) -> ThirdParty:
    return await service.restore(third_party_id)
