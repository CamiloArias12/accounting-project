"""The location catalogs: country, department and municipality.

Three tables rather than one generic lookup, because the three levels do not
have the same shape. A country is identified by its ISO code, a department by a
two-digit DANE code, and a municipality by a five-digit one whose first two
digits are its department's. Only separate tables can express that a
municipality belongs to a department, and that the codes are unique per level.

The DANE codes are not decoration: DIAN's `medios magnéticos` reports identify
cities by code, so storing the name alone would mean mapping them by hand later.

Place names are kept in Spanish. They are proper nouns, not translatable labels.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base, TimestampMixin

#: Length of a DANE department code, and the prefix every municipality in it
#: shares.
DEPARTMENT_CODE_LENGTH = 2
#: Length of a DANE municipality code: the department's two digits plus three.
CITY_CODE_LENGTH = 5


class Country(Base, TimestampMixin):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    iso_code: Mapped[str] = mapped_column(String(2), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)

    departments: Mapped[list[Department]] = relationship(
        back_populates="country", order_by="Department.name"
    )

    def __repr__(self) -> str:
        return f"<Country {self.iso_code} {self.name}>"


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (
        # Unique per country, not globally: the DANE numbering only applies to
        # Colombia, and another country's subdivisions may reuse the digits.
        UniqueConstraint("country_id", "dane_code", name="uq_departments_country_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        # RESTRICT everywhere in this module: a catalog row referenced by a
        # third party must not disappear under it.
        ForeignKey("countries.id", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
    )
    dane_code: Mapped[str] = mapped_column(String(DEPARTMENT_CODE_LENGTH))
    name: Mapped[str] = mapped_column(String(100), index=True)

    country: Mapped[Country] = relationship(back_populates="departments")
    cities: Mapped[list[City]] = relationship(
        back_populates="department", order_by="City.name"
    )

    def __repr__(self) -> str:
        return f"<Department {self.dane_code} {self.name}>"


class City(Base, TimestampMixin):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT", onupdate="CASCADE"),
        index=True,
    )
    #: Globally unique, unlike a department's: the five digits already carry the
    #: department in their prefix.
    dane_code: Mapped[str] = mapped_column(
        String(CITY_CODE_LENGTH), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), index=True)

    department: Mapped[Department] = relationship(back_populates="cities")

    def __repr__(self) -> str:
        return f"<City {self.dane_code} {self.name}>"
