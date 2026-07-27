from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base, TimestampMixin

DEPARTMENT_CODE_LENGTH = 2
CITY_CODE_LENGTH = 5


class Country(Base, TimestampMixin):
    """The location catalogs: country, department and municipality."""
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
        UniqueConstraint("country_id", "dane_code", name="uq_departments_country_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
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
    dane_code: Mapped[str] = mapped_column(
        String(CITY_CODE_LENGTH), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), index=True)

    department: Mapped[Department] = relationship(back_populates="cities")

    def __repr__(self) -> str:
        return f"<City {self.dane_code} {self.name}>"
