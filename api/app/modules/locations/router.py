from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.locations.models import City, Country, Department
from app.modules.locations.schemas import CityRead, CountryRead, DepartmentRead
from app.modules.locations.service import LocationService
from app.shared.database import get_session

# Read-only: the catalogs are seeded by migration, so there is nothing to POST.
router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_service(session: SessionDep) -> LocationService:
    return LocationService(session)


ServiceDep = Annotated[LocationService, Depends(get_service)]
Search = Annotated[str | None, Query(description="Match name or code")]


@router.get("/countries", response_model=list[CountryRead])
async def list_countries(
    service: ServiceDep,
    search: Search = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=300)] = 300,
) -> list[Country]:
    return list(await service.countries(search=search, skip=skip, limit=limit))


@router.get("/departments", response_model=list[DepartmentRead])
async def list_departments(
    service: ServiceDep,
    country_id: Annotated[int | None, Query()] = None,
    search: Search = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Department]:
    return list(
        await service.departments(
            country_id=country_id, search=search, skip=skip, limit=limit
        )
    )


@router.get("/cities", response_model=list[CityRead])
async def list_cities(
    service: ServiceDep,
    department_id: Annotated[int | None, Query()] = None,
    search: Search = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[City]:
    """Municipalities, always paged.

    There are 1122 of them, so a picker filters by department or searches by
    name; the endpoint never returns the whole catalog at once.
    """
    return list(
        await service.cities(
            department_id=department_id, search=search, skip=skip, limit=limit
        )
    )


@router.get("/cities/{city_id}", response_model=CityRead)
async def get_city(city_id: int, service: ServiceDep) -> City:
    """One municipality, to resolve which department a stored id belongs to.

    A third party keeps the city its document was issued in, but not the
    department, so an edit form has nothing to preselect its cascade with.
    """
    return await service.get_city(city_id)
