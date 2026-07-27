from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import City, Country, Department

BASE = "/api/v1/third-parties"


async def seed_places(session: AsyncSession) -> dict[str, int]:
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


async def test_registering_verifies_the_nit_and_the_places(
    auth_client: AsyncClient, session: AsyncSession
) -> None:
    places = await seed_places(session)

    company = await auth_client.post(BASE, json=legal_payload(places))
    assert company.status_code == 201, company.text
    assert company.json()["document_type"] == "NIT"
    assert company.json()["check_digit"] == 4
    assert company.json()["formatted_document"] == "800197268-4"

    person = await auth_client.post(BASE, json=natural_payload(places))
    assert person.status_code == 201
    assert person.json()["full_name"] == "Ana Restrepo"
    assert person.json()["check_digit"] is None

    twice = await auth_client.post(BASE, json=natural_payload(places))
    assert twice.status_code == 409

    wrong_department = await auth_client.post(
        BASE,
        json=natural_payload(
            places, document_number="999", department_id=places["cundinamarca"]
        ),
    )
    assert wrong_department.status_code == 422
    assert "does not belong to that department" in wrong_department.json()["detail"]

    wrong_country = await auth_client.post(
        BASE,
        json=natural_payload(places, document_number="999", country_id=places["peru"]),
    )
    assert wrong_country.status_code == 422
    assert "does not belong to that country" in wrong_country.json()["detail"]
