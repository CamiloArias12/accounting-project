from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.modules.locations.errors import (
    CityNotFound,
    CountryNotFound,
    DepartmentNotFound,
)
from app.modules.locations.models import City, Country, Department


class LocationService:
    """Reads over the location catalogs."""
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def countries(
        self, *, search: str | None = None, skip: int = 0, limit: int = 300
    ) -> Sequence[Country]:
        query = _matching(select(Country), Country.name, Country.iso_code, search)
        result = await self._session.execute(
            query.order_by(Country.name).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def departments(
        self,
        *,
        country_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Department]:
        query = _matching(
            select(Department), Department.name, Department.dane_code, search
        )
        if country_id is not None:
            query = query.where(Department.country_id == country_id)

        result = await self._session.execute(
            query.order_by(Department.name).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def cities(
        self,
        *,
        department_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[City]:
        query = _matching(select(City), City.name, City.dane_code, search)
        if department_id is not None:
            query = query.where(City.department_id == department_id)

        result = await self._session.execute(
            query.order_by(City.name).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_country(self, country_id: int) -> Country:
        country = await self._session.get(Country, country_id)
        if country is None:
            raise CountryNotFound(country_id)
        return country

    async def get_department(self, department_id: int) -> Department:
        department = await self._session.get(Department, department_id)
        if department is None:
            raise DepartmentNotFound(department_id)
        return department

    async def get_city(self, city_id: int) -> City:
        city = await self._session.get(City, city_id)
        if city is None:
            raise CityNotFound(city_id)
        return city


def _matching[T](
    query: Select[tuple[T]],
    name: InstrumentedAttribute[str],
    code: InstrumentedAttribute[str],
    search: str | None,
) -> Select[tuple[T]]:
    if not search:
        return query

    pattern = f"%{search.strip()}%"
    return query.where(name.ilike(pattern) | code.ilike(pattern))
