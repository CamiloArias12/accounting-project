from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.third_parties.documents import (
    CompanyType,
    DocumentType,
    EducationLevel,
    Gender,
    HousingType,
    MaritalStatus,
    PersonType,
    TaxRegime,
)


class _Contact(BaseModel):
    """What both kinds of person carry."""

    address: str = Field(min_length=1, max_length=120)
    country_id: int
    department_id: int | None = None
    city_id: int | None = None
    mobile_phone: str = Field(min_length=1, max_length=20)
    landline: str | None = Field(default=None, max_length=20)
    email: EmailStr
    tax_regime: TaxRegime
    trade_name: str | None = Field(default=None, max_length=150)
    foreign_operations: bool = False
    public_resources: bool = False
    public_recognition: bool = False
    public_power: bool = False
    is_active: bool = True


class NaturalPersonCreate(_Contact):
    person_type: Literal[PersonType.NATURAL]

    document_type: DocumentType = Field(examples=[DocumentType.CITIZEN_ID])
    document_number: str = Field(min_length=1, max_length=20, examples=["1020304050"])
    check_digit: int | None = Field(default=None, ge=0, le=9)

    first_name: str = Field(min_length=1, max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    first_surname: str = Field(min_length=1, max_length=50)
    second_surname: str | None = Field(default=None, max_length=50)

    issue_date: date
    issue_city_id: int
    birth_date: date
    birth_country_id: int
    birth_department_id: int | None = None
    birth_city_id: int | None = None

    gender: Gender
    marital_status: MaritalStatus
    housing_type: HousingType
    education_level: EducationLevel
    profession: str = Field(min_length=1, max_length=80)


class LegalEntityCreate(_Contact):
    person_type: Literal[PersonType.LEGAL]

    document_number: str = Field(min_length=1, max_length=15, examples=["800197268"])
    check_digit: int | None = Field(default=None, ge=0, le=9)

    legal_name: str = Field(min_length=1, max_length=150)
    company_type: CompanyType
    company_nature: str = Field(min_length=1, max_length=120)
    legal_rep_document_type: DocumentType
    legal_rep_document_number: str = Field(min_length=1, max_length=20)
    legal_rep_name: str = Field(min_length=1, max_length=150)


ThirdPartyCreate = Annotated[
    NaturalPersonCreate | LegalEntityCreate, Field(discriminator="person_type")
]


class ThirdPartyUpdate(BaseModel):
    """Everything editable, all optional."""

    document_type: DocumentType | None = None
    document_number: str | None = Field(default=None, min_length=1, max_length=20)
    check_digit: int | None = Field(default=None, ge=0, le=9)

    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    first_surname: str | None = Field(default=None, min_length=1, max_length=50)
    second_surname: str | None = Field(default=None, max_length=50)
    issue_date: date | None = None
    issue_city_id: int | None = None
    birth_date: date | None = None
    birth_country_id: int | None = None
    birth_department_id: int | None = None
    birth_city_id: int | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    housing_type: HousingType | None = None
    education_level: EducationLevel | None = None
    profession: str | None = Field(default=None, max_length=80)

    legal_name: str | None = Field(default=None, min_length=1, max_length=150)
    company_type: CompanyType | None = None
    company_nature: str | None = Field(default=None, max_length=120)
    legal_rep_document_type: DocumentType | None = None
    legal_rep_document_number: str | None = Field(default=None, max_length=20)
    legal_rep_name: str | None = Field(default=None, max_length=150)

    trade_name: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, min_length=1, max_length=120)
    country_id: int | None = None
    department_id: int | None = None
    city_id: int | None = None
    mobile_phone: str | None = Field(default=None, min_length=1, max_length=20)
    landline: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    tax_regime: TaxRegime | None = None
    foreign_operations: bool | None = None
    public_resources: bool | None = None
    public_recognition: bool | None = None
    public_power: bool | None = None
    is_active: bool | None = None


class ThirdPartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_type: PersonType
    document_type: DocumentType
    document_number: str
    check_digit: int | None
    formatted_document: str
    full_name: str

    first_name: str | None
    middle_name: str | None
    first_surname: str | None
    second_surname: str | None
    issue_date: date | None
    issue_city_id: int | None
    birth_date: date | None
    birth_country_id: int | None
    birth_department_id: int | None
    birth_city_id: int | None
    gender: Gender | None
    marital_status: MaritalStatus | None
    housing_type: HousingType | None
    education_level: EducationLevel | None
    profession: str | None

    legal_name: str | None
    company_type: CompanyType | None
    company_nature: str | None
    legal_rep_document_type: DocumentType | None
    legal_rep_document_number: str | None
    legal_rep_name: str | None

    trade_name: str | None
    address: str | None
    country_id: int | None
    department_id: int | None
    city_id: int | None
    mobile_phone: str | None
    landline: str | None
    email: str | None
    tax_regime: TaxRegime

    foreign_operations: bool
    public_resources: bool
    public_recognition: bool
    public_power: bool

    is_active: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
