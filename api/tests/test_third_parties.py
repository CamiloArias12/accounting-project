from datetime import date

import pytest
from sqlalchemy import select
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
    PersonType,
    TaxRegime,
)
from app.modules.third_parties.errors import IncompleteThirdParty
from app.modules.third_parties.models import ThirdParty


async def seed_place(session: AsyncSession) -> tuple[int, int, int]:
    """One country, department and city, to hang the foreign keys off."""
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


async def test_a_natural_person_is_stored_as_one(session: AsyncSession) -> None:
    country_id, _, city_id = await seed_place(session)

    person = a_natural_person(country_id=country_id, city_id=city_id)
    session.add(person)
    await session.flush()

    assert person.person_type is PersonType.NATURAL
    assert person.legal_name is None
    assert person.check_digit is None


async def test_a_legal_entity_is_always_a_nit(session: AsyncSession) -> None:
    country_id, _, _ = await seed_place(session)

    company = a_legal_entity(country_id=country_id)

    assert company.person_type is PersonType.LEGAL
    assert company.document_type is DocumentType.NIT
    assert company.first_name is None


async def test_the_check_digit_is_derived_when_it_is_not_given(
    session: AsyncSession,
) -> None:
    country_id, _, _ = await seed_place(session)

    company = a_legal_entity(country_id=country_id)

    assert company.check_digit == 4
    assert company.formatted_document == "800197268-4"


async def test_a_wrong_check_digit_is_refused(session: AsyncSession) -> None:
    country_id, _, _ = await seed_place(session)

    with pytest.raises(InvalidDocument, match="is 4, not 9"):
        a_legal_entity(country_id=country_id, check_digit=9)


async def test_a_check_digit_on_a_document_that_has_none_is_refused(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)

    with pytest.raises(IncompleteThirdParty, match="has no check digit"):
        a_natural_person(country_id=country_id, city_id=city_id, check_digit=3)


async def test_a_natural_person_without_a_surname_is_refused(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)

    with pytest.raises(IncompleteThirdParty, match="first_surname is required"):
        a_natural_person(country_id=country_id, city_id=city_id, first_surname="  ")


async def test_the_document_number_is_normalized_on_the_way_in(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)

    person = a_natural_person(
        country_id=country_id, city_id=city_id, document_number=" 1.020.304.050 "
    )

    assert person.document_number == "1020304050"


async def test_full_name_joins_the_parts_that_are_there(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)

    person = a_natural_person(
        country_id=country_id,
        city_id=city_id,
        middle_name="María",
        second_surname="Gómez",
    )
    assert person.full_name == "Ana María Restrepo Gómez"

    without_middle = a_natural_person(
        country_id=country_id, city_id=city_id, document_number="999"
    )
    assert without_middle.full_name == "Ana Restrepo"


async def test_full_name_of_a_company_is_its_legal_name(
    session: AsyncSession,
) -> None:
    country_id, _, _ = await seed_place(session)

    assert (
        a_legal_entity(country_id=country_id).full_name
        == "Comercializadora del Norte S.A.S."
    )


async def test_the_same_document_cannot_be_registered_twice(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)

    session.add(a_natural_person(country_id=country_id, city_id=city_id))
    await session.flush()

    session.add(a_natural_person(country_id=country_id, city_id=city_id))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_the_same_number_under_another_document_type_is_allowed(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)

    session.add(a_natural_person(country_id=country_id, city_id=city_id))
    session.add(
        a_natural_person(
            country_id=country_id,
            city_id=city_id,
            document_type=DocumentType.FOREIGNER_ID,
        )
    )
    await session.flush()

    stored = await session.execute(select(ThirdParty))
    assert len(stored.scalars().all()) == 2


async def test_deleting_keeps_the_row_and_restoring_clears_the_mark(
    session: AsyncSession,
) -> None:
    country_id, _, city_id = await seed_place(session)
    person = a_natural_person(country_id=country_id, city_id=city_id)
    session.add(person)
    await session.flush()

    person.mark_deleted()
    await session.flush()
    assert person.is_deleted

    person.restore()
    await session.flush()
    assert not person.is_deleted
    assert person.deleted_at is None


async def test_a_deleted_third_party_still_blocks_its_document(
    session: AsyncSession,
) -> None:
    # A document already named in an accounting entry must not be reused by
    # someone else, so the unique constraint covers deleted rows too.
    country_id, _, city_id = await seed_place(session)
    person = a_natural_person(country_id=country_id, city_id=city_id)
    session.add(person)
    await session.flush()
    person.mark_deleted()
    await session.flush()

    session.add(a_natural_person(country_id=country_id, city_id=city_id))
    with pytest.raises(IntegrityError):
        await session.flush()
