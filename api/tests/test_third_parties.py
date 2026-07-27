from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.locations.models import City, Country, Department
from app.modules.third_parties.documents import (
    CompanyType,
    DocumentType,
    EducationLevel,
    Gender,
    HousingType,
    InvalidDocument,
    MaritalStatus,
    TaxRegime,
    compute_check_digit,
    normalize_document,
)
from app.modules.third_parties.models import ThirdParty


async def seed_place(session: AsyncSession) -> tuple[int, int, int]:
    colombia = Country(iso_code="CO", name="Colombia")
    session.add(colombia)
    await session.flush()

    antioquia = Department(country_id=colombia.id, dane_code="05", name="Antioquia")
    session.add(antioquia)
    await session.flush()

    medellin = City(department_id=antioquia.id, dane_code="05001", name="Medellín")
    session.add(medellin)
    await session.flush()

    return colombia.id, antioquia.id, medellin.id


def a_natural_person(
    *, country_id: int, city_id: int, **overrides: object
) -> ThirdParty:
    fields: dict[str, object] = {
        "document_type": DocumentType.CITIZEN_ID,
        "document_number": "1020304050",
        "first_name": "Ana",
        "first_surname": "Restrepo",
        "issue_date": date(2010, 5, 4),
        "issue_city_id": city_id,
        "birth_date": date(1992, 3, 18),
        "birth_country_id": country_id,
        "gender": Gender.FEMALE,
        "marital_status": MaritalStatus.SINGLE,
        "address": "Calle 10 # 40-20",
        "country_id": country_id,
        "housing_type": HousingType.RENTED,
        "education_level": EducationLevel.UNIVERSITY,
        "profession": "Contadora",
        "mobile_phone": "3001234567",
        "email": "ana@example.com",
        "tax_regime": TaxRegime.NOT_VAT_RESPONSIBLE,
    }
    fields.update(overrides)
    return ThirdParty.natural(**fields)  # type: ignore[arg-type]


def a_legal_entity(*, country_id: int, **overrides: object) -> ThirdParty:
    fields: dict[str, object] = {
        "document_number": "800197268",
        "legal_name": "Comercializadora del Norte S.A.S.",
        "company_type": CompanyType.SIMPLIFIED_JOINT_STOCK,
        "company_nature": "Privada",
        "legal_rep_document_type": DocumentType.CITIZEN_ID,
        "legal_rep_document_number": "71234567",
        "legal_rep_name": "Carlos Mejía",
        "address": "Carrera 43 # 1-50",
        "country_id": country_id,
        "mobile_phone": "3009876543",
        "email": "contacto@example.com",
        "tax_regime": TaxRegime.VAT_RESPONSIBLE,
    }
    fields.update(overrides)
    return ThirdParty.legal(**fields)  # type: ignore[arg-type]


async def test_the_check_digit_is_derived_and_verified(session: AsyncSession) -> None:
    assert compute_check_digit("800197268") == 4
    assert compute_check_digit("890903938") == 8

    country_id, _, _ = await seed_place(session)
    company = a_legal_entity(country_id=country_id)
    assert company.document_type is DocumentType.NIT
    assert company.check_digit == 4
    assert company.formatted_document == "800197268-4"

    with pytest.raises(InvalidDocument, match="is 4, not 9"):
        a_legal_entity(country_id=country_id, check_digit=9)


async def test_the_document_identifies_the_person_for_good(
    session: AsyncSession,
) -> None:
    assert normalize_document("  1.020.304  ", DocumentType.CITIZEN_ID) == "1020304"
    with pytest.raises(InvalidDocument, match="digits only"):
        normalize_document("AB123456", DocumentType.CITIZEN_ID)
    with pytest.raises(InvalidDocument, match="must not include the check digit"):
        normalize_document("900123456-7", DocumentType.NIT)

    country_id, _, city_id = await seed_place(session)
    person = a_natural_person(
        country_id=country_id, city_id=city_id, document_number=" 1.020.304.050 "
    )
    assert person.document_number == "1020304050"

    session.add(person)
    await session.flush()
    person.mark_deleted()
    await session.flush()

    session.add(a_natural_person(country_id=country_id, city_id=city_id))
    with pytest.raises(IntegrityError):
        await session.flush()
