from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import City, Country, Department

BASE = "/api/v1/third-parties"


async def seed_places(session: AsyncSession) -> dict[str, int]:
    """Two departments with a city each, plus a second country.

    Enough to tell "this city is in that department" apart from "this city
    exists", which is the whole point of the consistency check.
    """
    colombia = Country(iso_code="CO", name="Colombia")
    peru = Country(iso_code="PE", name="Perú")
    session.add_all([colombia, peru])
    await session.flush()

    antioquia = Department(country_id=colombia.id, dane_code="05", name="Antioquia")
    cundinamarca = Department(
        country_id=colombia.id, dane_code="25", name="Cundinamarca"
    )
    session.add_all([antioquia, cundinamarca])
    await session.flush()

    medellin = City(department_id=antioquia.id, dane_code="05001", name="Medellín")
    soacha = City(department_id=cundinamarca.id, dane_code="25754", name="Soacha")
    session.add_all([medellin, soacha])
    await session.flush()
    await session.commit()

    return {
        "colombia": colombia.id,
        "peru": peru.id,
        "antioquia": antioquia.id,
        "cundinamarca": cundinamarca.id,
        "medellin": medellin.id,
        "soacha": soacha.id,
    }


def natural_payload(places: dict[str, int], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "person_type": "Natural person",
        "document_type": "Citizen ID",
        "document_number": "1020304050",
        "first_name": "Ana",
        "first_surname": "Restrepo",
        "issue_date": "2010-05-04",
        "issue_city_id": places["medellin"],
        "birth_date": "1992-03-18",
        "birth_country_id": places["colombia"],
        "birth_department_id": places["antioquia"],
        "birth_city_id": places["medellin"],
        "gender": "Female",
        "marital_status": "Single",
        "address": "Calle 10 # 40-20",
        "country_id": places["colombia"],
        "department_id": places["antioquia"],
        "city_id": places["medellin"],
        "housing_type": "Rented",
        "education_level": "University",
        "profession": "Contadora",
        "mobile_phone": "3001234567",
        "email": "ana@example.com",
        "tax_regime": "Not VAT responsible",
    }
    payload.update(overrides)
    return payload


def legal_payload(places: dict[str, int], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "person_type": "Legal entity",
        "document_number": "800197268",
        "legal_name": "Comercializadora del Norte S.A.S.",
        "company_type": "Simplified joint-stock company",
        "company_nature": "Privada",
        "legal_rep_document_type": "Citizen ID",
        "legal_rep_document_number": "71234567",
        "legal_rep_name": "Carlos Mejía",
        "address": "Carrera 43 # 1-50",
        "country_id": places["colombia"],
        "department_id": places["antioquia"],
        "city_id": places["medellin"],
        "mobile_phone": "3009876543",
        "email": "contacto@example.com",
        "tax_regime": "VAT responsible",
    }
    payload.update(overrides)
    return payload


async def test_registering_a_natural_person(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    created = await auth_client.post(BASE, json=natural_payload(places))

    assert created.status_code == 201
    body = created.json()
    assert body["person_type"] == "Natural person"
    assert body["full_name"] == "Ana Restrepo"
    assert body["check_digit"] is None
    assert body["legal_name"] is None


async def test_registering_a_company_derives_its_check_digit(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    created = await auth_client.post(BASE, json=legal_payload(places))

    assert created.status_code == 201
    body = created.json()
    assert body["document_type"] == "NIT"
    assert body["check_digit"] == 4
    assert body["formatted_document"] == "800197268-4"


async def test_a_company_without_its_legal_representative_is_rejected(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    payload = legal_payload(places)
    del payload["legal_rep_name"]

    rejected = await auth_client.post(BASE, json=payload)

    # Caught by the schema, before anything reaches the database.
    assert rejected.status_code == 422


async def test_a_wrong_check_digit_is_rejected(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    rejected = await auth_client.post(BASE, json=legal_payload(places, check_digit=9))

    assert rejected.status_code == 422
    assert "check digit" in rejected.json()["detail"]


async def test_a_city_from_another_department_is_rejected(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    # Medellín is in Antioquia, not Cundinamarca. No foreign key notices this.
    payload = natural_payload(places, department_id=places["cundinamarca"])

    rejected = await auth_client.post(BASE, json=payload)

    assert rejected.status_code == 422
    assert "does not belong to that department" in rejected.json()["detail"]


async def test_a_department_from_another_country_is_rejected(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    payload = natural_payload(places, country_id=places["peru"])

    rejected = await auth_client.post(BASE, json=payload)

    assert rejected.status_code == 422
    assert "does not belong to that country" in rejected.json()["detail"]


async def test_registering_the_same_document_twice_conflicts(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    await auth_client.post(BASE, json=natural_payload(places))

    again = await auth_client.post(BASE, json=natural_payload(places))

    assert again.status_code == 409


async def test_searching_by_document_and_by_name(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    await auth_client.post(BASE, json=natural_payload(places))
    await auth_client.post(BASE, json=legal_payload(places))

    by_document = await auth_client.get(BASE, params={"search": "1020304"})
    assert [t["full_name"] for t in by_document.json()] == ["Ana Restrepo"]

    by_name = await auth_client.get(BASE, params={"search": "comercializadora"})
    assert [t["document_number"] for t in by_name.json()] == ["800197268"]


async def test_filtering_by_person_type(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    await auth_client.post(BASE, json=natural_payload(places))
    await auth_client.post(BASE, json=legal_payload(places))

    companies = await auth_client.get(BASE, params={"person_type": "Legal entity"})

    assert [t["legal_name"] for t in companies.json()] == [
        "Comercializadora del Norte S.A.S."
    ]


async def test_updating_the_document_recomputes_the_check_digit(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    created = await auth_client.post(BASE, json=legal_payload(places))
    third_party_id = created.json()["id"]

    updated = await auth_client.patch(
        f"{BASE}/{third_party_id}", json={"document_number": "890903938"}
    )

    assert updated.status_code == 200
    assert updated.json()["check_digit"] == 8


async def test_deleting_hides_it_and_restoring_brings_it_back(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    created = await auth_client.post(BASE, json=natural_payload(places))
    third_party_id = created.json()["id"]

    deleted = await auth_client.delete(f"{BASE}/{third_party_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None

    assert (await auth_client.get(f"{BASE}/{third_party_id}")).status_code == 404
    kept = await auth_client.get(
        f"{BASE}/{third_party_id}", params={"include_deleted": True}
    )
    assert kept.status_code == 200

    restored = await auth_client.post(f"{BASE}/{third_party_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None


async def test_registering_a_deleted_document_again_revives_the_row(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)
    created = await auth_client.post(BASE, json=natural_payload(places))
    third_party_id = created.json()["id"]
    await auth_client.delete(f"{BASE}/{third_party_id}")

    again = await auth_client.post(
        BASE, json=natural_payload(places, first_name="Ana María")
    )

    assert again.status_code == 201
    # Same row, so anything already pointing at it keeps pointing at a person.
    assert again.json()["id"] == third_party_id
    assert again.json()["full_name"] == "Ana María Restrepo"
    assert again.json()["deleted_at"] is None


async def test_the_endpoints_require_a_token(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401
