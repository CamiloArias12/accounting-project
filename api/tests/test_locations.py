import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import (
    CITY_CODE_LENGTH,
    DEPARTMENT_CODE_LENGTH,
    City,
    Country,
    Department,
)

_VERSIONS = Path(__file__).parents[1] / "alembic" / "versions"


def _seed_migration(name: str) -> ModuleType:
    """Load a migration as a module, to check the rows it is going to insert.

    The catalogs live inside the revisions rather than in the application
    package, so that a replay always produces what it produced the first time.
    That leaves the file itself as the only thing worth asserting against.
    """
    spec = importlib.util.spec_from_file_location(name, _VERSIONS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_top = _seed_migration("7355399db43d_seed_countries_and_colombian_departments")
_municipalities = _seed_migration("d204a471ea58_seed_colombian_municipalities")

COLOMBIA: str = _top._COLOMBIA
COUNTRIES: tuple[tuple[str, str], ...] = _top._COUNTRIES
DEPARTMENTS: tuple[tuple[str, str], ...] = _top._DEPARTMENTS
MUNICIPALITIES: tuple[tuple[str, str], ...] = _municipalities._MUNICIPALITIES


def test_every_country_has_a_two_letter_iso_code() -> None:
    assert all(len(iso_code) == 2 for iso_code, _ in COUNTRIES)


def test_country_iso_codes_are_unique() -> None:
    codes = [iso_code for iso_code, _ in COUNTRIES]
    assert len(codes) == len(set(codes))


def test_colombia_is_in_the_catalog() -> None:
    assert COLOMBIA in {iso_code for iso_code, _ in COUNTRIES}


def test_the_thirty_two_departments_and_the_capital_district_are_listed() -> None:
    assert len(DEPARTMENTS) == 33


def test_every_department_code_has_the_dane_length() -> None:
    assert all(len(code) == DEPARTMENT_CODE_LENGTH for code, _ in DEPARTMENTS)
    assert all(code.isdigit() for code, _ in DEPARTMENTS)


def test_department_codes_are_unique() -> None:
    codes = [code for code, _ in DEPARTMENTS]
    assert len(codes) == len(set(codes))


def test_the_divipola_ships_one_thousand_one_hundred_and_twenty_two_rows() -> None:
    assert len(MUNICIPALITIES) == 1122


def test_municipality_codes_are_unique() -> None:
    codes = [code for code, _ in MUNICIPALITIES]
    assert len(codes) == len(set(codes))


def test_every_municipality_code_has_the_dane_length() -> None:
    assert all(len(code) == CITY_CODE_LENGTH for code, _ in MUNICIPALITIES)
    assert all(code.isdigit() for code, _ in MUNICIPALITIES)


def test_every_municipality_belongs_to_a_seeded_department() -> None:
    # The seed migration reads the department off this prefix, so an unknown one
    # would attach a municipality to the wrong place, or to nothing.
    departments = {code for code, _ in DEPARTMENTS}
    prefixes = {code[:DEPARTMENT_CODE_LENGTH] for code, _ in MUNICIPALITIES}
    assert prefixes <= departments


def test_every_department_has_at_least_one_municipality() -> None:
    prefixes = {code[:DEPARTMENT_CODE_LENGTH] for code, _ in MUNICIPALITIES}
    assert {code for code, _ in DEPARTMENTS} <= prefixes


def test_municipality_names_are_not_shouted() -> None:
    # The DANE ships them upper case; they are stored title-cased.
    assert not [name for _, name in MUNICIPALITIES if name.isupper()]


async def test_two_countries_cannot_share_an_iso_code(session: AsyncSession) -> None:
    session.add(Country(iso_code="CO", name="Colombia"))
    await session.flush()

    session.add(Country(iso_code="CO", name="Duplicada"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_a_department_code_is_unique_within_its_country(
    session: AsyncSession,
) -> None:
    colombia = Country(iso_code="CO", name="Colombia")
    peru = Country(iso_code="PE", name="Perú")
    session.add_all([colombia, peru])
    await session.flush()

    session.add(Department(country_id=colombia.id, dane_code="05", name="Antioquia"))
    await session.flush()

    # Free in another country: the DANE numbering only applies to Colombia.
    session.add(Department(country_id=peru.id, dane_code="05", name="Otro"))
    await session.flush()

    session.add(Department(country_id=colombia.id, dane_code="05", name="Repetido"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_a_city_code_is_unique_everywhere(session: AsyncSession) -> None:
    colombia = Country(iso_code="CO", name="Colombia")
    session.add(colombia)
    await session.flush()

    antioquia = Department(country_id=colombia.id, dane_code="05", name="Antioquia")
    caldas = Department(country_id=colombia.id, dane_code="17", name="Caldas")
    session.add_all([antioquia, caldas])
    await session.flush()

    session.add(City(department_id=antioquia.id, dane_code="05001", name="Medellín"))
    await session.flush()

    # The five digits already carry the department, so they cannot repeat even
    # under a different one.
    session.add(City(department_id=caldas.id, dane_code="05001", name="Repetida"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_a_city_code_starts_with_its_department_code(
    session: AsyncSession,
) -> None:
    colombia = Country(iso_code="CO", name="Colombia")
    session.add(colombia)
    await session.flush()

    antioquia = Department(country_id=colombia.id, dane_code="05", name="Antioquia")
    session.add(antioquia)
    await session.flush()

    medellin = City(department_id=antioquia.id, dane_code="05001", name="Medellín")
    session.add(medellin)
    await session.flush()

    assert len(medellin.dane_code) == CITY_CODE_LENGTH
    assert medellin.dane_code.startswith(antioquia.dane_code)


async def test_the_catalog_starts_empty_in_tests(session: AsyncSession) -> None:
    # The seed lives in a migration, not in the metadata, so tests that need a
    # country have to create it.
    count = await session.execute(select(func.count()).select_from(Country))
    assert count.scalar_one() == 0
