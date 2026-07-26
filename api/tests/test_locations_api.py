from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.test_third_parties_api import seed_places

BASE = "/api/v1/locations"


async def test_listing_countries(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_places(session)

    listed = await auth_client.get(f"{BASE}/countries")

    assert listed.status_code == 200
    assert [c["iso_code"] for c in listed.json()] == ["CO", "PE"]


async def test_searching_a_country_by_name_or_code(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_places(session)

    by_name = await auth_client.get(f"{BASE}/countries", params={"search": "colom"})
    by_code = await auth_client.get(f"{BASE}/countries", params={"search": "PE"})

    assert [c["name"] for c in by_name.json()] == ["Colombia"]
    assert [c["name"] for c in by_code.json()] == ["Perú"]


async def test_departments_are_filtered_by_country(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    colombian = await auth_client.get(
        f"{BASE}/departments", params={"country_id": places["colombia"]}
    )
    peruvian = await auth_client.get(
        f"{BASE}/departments", params={"country_id": places["peru"]}
    )

    assert [d["name"] for d in colombian.json()] == ["Antioquia", "Cundinamarca"]
    assert peruvian.json() == []


async def test_cities_are_filtered_by_department(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    listed = await auth_client.get(
        f"{BASE}/cities", params={"department_id": places["antioquia"]}
    )

    assert [c["dane_code"] for c in listed.json()] == ["05001"]


async def test_searching_a_city_by_dane_code(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    await seed_places(session)

    found = await auth_client.get(f"{BASE}/cities", params={"search": "25754"})

    assert [c["name"] for c in found.json()] == ["Soacha"]


async def test_the_city_list_is_capped(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    # 1122 municipalities: a picker must never be able to ask for all of them.
    await seed_places(session)

    too_many = await auth_client.get(f"{BASE}/cities", params={"limit": 5000})

    assert too_many.status_code == 422


async def test_fetching_one_city_resolves_its_department(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    city = await auth_client.get(f"{BASE}/cities/{places['medellin']}")

    assert city.status_code == 200
    assert city.json()["department_id"] == places["antioquia"]


async def test_fetching_a_city_that_does_not_exist(auth_client: AsyncClient) -> None:
    assert (await auth_client.get(f"{BASE}/cities/9999")).status_code == 404


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(f"{BASE}/countries")).status_code == 401
