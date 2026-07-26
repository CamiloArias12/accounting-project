"""The third party table: whoever the books can point at.

One table for both kinds of person, discriminated by `person_type`. The
alternative — a table per kind — is what the reference project does, and it
forces every accounting record to carry two nullable foreign keys and branch on
which one is set. Here a movement points at one `third_party_id` and stops.

The consequence is that the columns of each kind must be nullable, so "a natural
person needs a first name" cannot be a NOT NULL constraint. That rule lives in
the two constructors below, which are the only supported way to build a row.

A third party is not a user: `users.third_party_id` links the two when someone
needs to log in, and most third parties never will.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.locations.models import City, Country, Department
from app.modules.third_parties.documents import (
    CompanyType,
    DocumentType,
    EducationLevel,
    Gender,
    HousingType,
    MaritalStatus,
    PersonType,
    TaxRegime,
    compute_check_digit,
    normalize_document,
    requires_check_digit,
    validate_check_digit,
)
from app.modules.third_parties.errors import IncompleteThirdParty
from app.shared.database import Base, TimestampMixin

#: Every enum is stored as its member name in a checked VARCHAR, the way the
#: accounts module already does it, so the values stay readable in the database
#: and renaming a label never needs a migration.
_NATIVE_ENUM = False


class ThirdParty(Base, TimestampMixin):
    __tablename__ = "third_parties"
    __table_args__ = (
        # Soft-deleted rows are included on purpose: a document that is already
        # referenced by an accounting entry must not be reused by someone else.
        UniqueConstraint(
            "document_type", "document_number", name="uq_third_parties_document"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- Identity -----------------------------------------------------------
    person_type: Mapped[PersonType] = mapped_column(
        Enum(
            PersonType,
            name="third_party_person_type",
            native_enum=_NATIVE_ENUM,
            length=20,
        ),
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(
            DocumentType,
            name="third_party_document_type",
            native_enum=_NATIVE_ENUM,
            length=30,
        )
    )
    document_number: Mapped[str] = mapped_column(String(20), index=True)
    #: NIT only. Derived from the number, but stored so it can be searched and
    #: printed without recomputing it.
    check_digit: Mapped[int | None] = mapped_column(default=None)

    # --- Natural person -----------------------------------------------------
    first_name: Mapped[str | None] = mapped_column(String(50), default=None)
    middle_name: Mapped[str | None] = mapped_column(String(50), default=None)
    first_surname: Mapped[str | None] = mapped_column(String(50), default=None)
    second_surname: Mapped[str | None] = mapped_column(String(50), default=None)
    issue_date: Mapped[date | None] = mapped_column(Date, default=None)
    issue_city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), default=None
    )
    birth_date: Mapped[date | None] = mapped_column(Date, default=None)
    birth_country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), default=None
    )
    #: Null outside Colombia: the DANE catalog does not cover other countries,
    #: so a foreign birthplace stops at the country.
    birth_department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), default=None
    )
    birth_city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), default=None
    )
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="third_party_gender", native_enum=_NATIVE_ENUM, length=20),
        default=None,
    )
    marital_status: Mapped[MaritalStatus | None] = mapped_column(
        Enum(
            MaritalStatus,
            name="third_party_marital_status",
            native_enum=_NATIVE_ENUM,
            length=30,
        ),
        default=None,
    )
    housing_type: Mapped[HousingType | None] = mapped_column(
        Enum(
            HousingType,
            name="third_party_housing_type",
            native_enum=_NATIVE_ENUM,
            length=20,
        ),
        default=None,
    )
    education_level: Mapped[EducationLevel | None] = mapped_column(
        Enum(
            EducationLevel,
            name="third_party_education_level",
            native_enum=_NATIVE_ENUM,
            length=20,
        ),
        default=None,
    )
    profession: Mapped[str | None] = mapped_column(String(80), default=None)

    # --- Legal entity -------------------------------------------------------
    legal_name: Mapped[str | None] = mapped_column(String(150), default=None)
    company_type: Mapped[CompanyType | None] = mapped_column(
        Enum(
            CompanyType,
            name="third_party_company_type",
            native_enum=_NATIVE_ENUM,
            length=40,
        ),
        default=None,
    )
    company_nature: Mapped[str | None] = mapped_column(String(120), default=None)
    legal_rep_document_type: Mapped[DocumentType | None] = mapped_column(
        Enum(
            DocumentType,
            name="third_party_legal_rep_document_type",
            native_enum=_NATIVE_ENUM,
            length=30,
        ),
        default=None,
    )
    legal_rep_document_number: Mapped[str | None] = mapped_column(
        String(20), default=None
    )
    legal_rep_name: Mapped[str | None] = mapped_column(String(150), default=None)

    # --- Common -------------------------------------------------------------
    #: The name the third party trades under, when it differs from the legal one.
    trade_name: Mapped[str | None] = mapped_column(String(150), default=None)
    #: Residence for a person, registered address for a company.
    address: Mapped[str | None] = mapped_column(String(120), default=None)
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), default=None
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), default=None
    )
    city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), default=None
    )
    mobile_phone: Mapped[str | None] = mapped_column(String(20), default=None)
    landline: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(120), default=None)
    tax_regime: Mapped[TaxRegime] = mapped_column(
        Enum(
            TaxRegime,
            name="third_party_tax_regime",
            native_enum=_NATIVE_ENUM,
            length=30,
        ),
        default=TaxRegime.NOT_VAT_RESPONSIBLE,
    )

    # --- SARLAFT declarations -----------------------------------------------
    foreign_operations: Mapped[bool] = mapped_column(default=False)
    public_resources: Mapped[bool] = mapped_column(default=False)
    public_recognition: Mapped[bool] = mapped_column(default=False)
    public_power: Mapped[bool] = mapped_column(default=False)

    # --- State --------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(default=True)
    #: Soft delete marker. Rows are never removed: a third party named in an
    #: accounting entry must stay resolvable for as long as the entry exists.
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)

    issue_city: Mapped[City | None] = relationship(foreign_keys=[issue_city_id])
    birth_country: Mapped[Country | None] = relationship(
        foreign_keys=[birth_country_id]
    )
    birth_department: Mapped[Department | None] = relationship(
        foreign_keys=[birth_department_id]
    )
    birth_city: Mapped[City | None] = relationship(foreign_keys=[birth_city_id])
    country: Mapped[Country | None] = relationship(foreign_keys=[country_id])
    department: Mapped[Department | None] = relationship(foreign_keys=[department_id])
    city: Mapped[City | None] = relationship(foreign_keys=[city_id])

    @classmethod
    def natural(
        cls,
        *,
        document_type: DocumentType,
        document_number: str,
        first_name: str,
        first_surname: str,
        issue_date: date,
        issue_city_id: int,
        birth_date: date,
        birth_country_id: int,
        gender: Gender,
        marital_status: MaritalStatus,
        address: str,
        country_id: int,
        housing_type: HousingType,
        education_level: EducationLevel,
        profession: str,
        mobile_phone: str,
        email: str,
        tax_regime: TaxRegime,
        check_digit: int | None = None,
        middle_name: str | None = None,
        second_surname: str | None = None,
        birth_department_id: int | None = None,
        birth_city_id: int | None = None,
        department_id: int | None = None,
        city_id: int | None = None,
        landline: str | None = None,
        trade_name: str | None = None,
        foreign_operations: bool = False,
        public_resources: bool = False,
        public_recognition: bool = False,
        public_power: bool = False,
        is_active: bool = True,
    ) -> ThirdParty:
        """Register a human being.

        Every field the reference project asks for is required here too; only
        the second given name, the second surname and the landline are optional,
        along with the birthplace below country level, which does not exist
        outside Colombia.
        """
        number = normalize_document(document_number, document_type)

        return cls(
            person_type=PersonType.NATURAL,
            document_type=document_type,
            document_number=number,
            check_digit=_resolve_check_digit(number, document_type, check_digit),
            first_name=_required(first_name, "first_name"),
            middle_name=_optional(middle_name),
            first_surname=_required(first_surname, "first_surname"),
            second_surname=_optional(second_surname),
            issue_date=issue_date,
            issue_city_id=issue_city_id,
            birth_date=birth_date,
            birth_country_id=birth_country_id,
            birth_department_id=birth_department_id,
            birth_city_id=birth_city_id,
            gender=gender,
            marital_status=marital_status,
            housing_type=housing_type,
            education_level=education_level,
            profession=_required(profession, "profession"),
            trade_name=_optional(trade_name),
            address=_required(address, "address"),
            country_id=country_id,
            department_id=department_id,
            city_id=city_id,
            mobile_phone=_required(mobile_phone, "mobile_phone"),
            landline=_optional(landline),
            email=_required(email, "email"),
            tax_regime=tax_regime,
            foreign_operations=foreign_operations,
            public_resources=public_resources,
            public_recognition=public_recognition,
            public_power=public_power,
            is_active=is_active,
        )

    @classmethod
    def legal(
        cls,
        *,
        document_number: str,
        legal_name: str,
        company_type: CompanyType,
        company_nature: str,
        legal_rep_document_type: DocumentType,
        legal_rep_document_number: str,
        legal_rep_name: str,
        address: str,
        country_id: int,
        mobile_phone: str,
        email: str,
        tax_regime: TaxRegime,
        check_digit: int | None = None,
        department_id: int | None = None,
        city_id: int | None = None,
        landline: str | None = None,
        trade_name: str | None = None,
        foreign_operations: bool = False,
        public_resources: bool = False,
        public_recognition: bool = False,
        public_power: bool = False,
        is_active: bool = True,
    ) -> ThirdParty:
        """Register an organization.

        The document type is not a parameter: a legal entity registered in
        Colombia is identified by its NIT, and accepting anything else would
        make the check digit optional for rows that must have one.
        """
        number = normalize_document(document_number, DocumentType.NIT)

        return cls(
            person_type=PersonType.LEGAL,
            document_type=DocumentType.NIT,
            document_number=number,
            check_digit=_resolve_check_digit(number, DocumentType.NIT, check_digit),
            legal_name=_required(legal_name, "legal_name"),
            company_type=company_type,
            company_nature=_required(company_nature, "company_nature"),
            legal_rep_document_type=legal_rep_document_type,
            legal_rep_document_number=normalize_document(
                legal_rep_document_number, legal_rep_document_type
            ),
            legal_rep_name=_required(legal_rep_name, "legal_rep_name"),
            trade_name=_optional(trade_name),
            address=_required(address, "address"),
            country_id=country_id,
            department_id=department_id,
            city_id=city_id,
            mobile_phone=_required(mobile_phone, "mobile_phone"),
            landline=_optional(landline),
            email=_required(email, "email"),
            tax_regime=tax_regime,
            foreign_operations=foreign_operations,
            public_resources=public_resources,
            public_recognition=public_recognition,
            public_power=public_power,
            is_active=is_active,
        )

    @property
    def full_name(self) -> str:
        """What to show in a list or print on a document."""
        if self.person_type is PersonType.LEGAL:
            return self.legal_name or ""

        parts = (
            self.first_name,
            self.middle_name,
            self.first_surname,
            self.second_surname,
        )
        return " ".join(part for part in parts if part)

    @property
    def formatted_document(self) -> str:
        """The number as people write it, check digit included."""
        if self.check_digit is None:
            return self.document_number
        return f"{self.document_number}-{self.check_digit}"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_deleted(self) -> None:
        # Naive, to match the other timestamp columns.
        self.deleted_at = datetime.now(UTC).replace(tzinfo=None)

    def restore(self) -> None:
        self.deleted_at = None

    def __repr__(self) -> str:
        return f"<ThirdParty {self.formatted_document} {self.full_name}>"


def _resolve_check_digit(
    number: str, document_type: DocumentType, given: int | None
) -> int | None:
    """Validate the check digit when it was supplied, derive it otherwise."""
    if not requires_check_digit(document_type):
        if given is not None:
            raise IncompleteThirdParty(f"A {document_type.value} has no check digit")
        return None

    if given is None:
        return compute_check_digit(number)
    return validate_check_digit(number, given)


def _required(value: str, field: str) -> str:
    stripped = value.strip() if value else ""
    if not stripped:
        raise IncompleteThirdParty(f"{field} is required")
    return stripped


def _optional(value: str | None) -> str | None:
    stripped = value.strip() if value else ""
    return stripped or None
