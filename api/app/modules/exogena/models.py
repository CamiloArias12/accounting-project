from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin

MONEY = Numeric(18, 2)


class ExogenaGeneration(Base, TimestampMixin):
    """One run, kept with the file it produced."""

    __tablename__ = "exogena_generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True)

    threshold_uvt: Mapped[Decimal] = mapped_column(MONEY)
    uvt_value: Mapped[Decimal | None] = mapped_column(MONEY, default=None)
    threshold_pesos: Mapped[Decimal] = mapped_column(MONEY, default=Decimal(0))

    filer_nit: Mapped[str] = mapped_column(String(20), default="")
    filer_name: Mapped[str] = mapped_column(String(150), default="")

    record_count: Mapped[int] = mapped_column(default=0)
    total_gross: Mapped[Decimal] = mapped_column(MONEY, default=Decimal(0))
    total_withheld: Mapped[Decimal] = mapped_column(MONEY, default=Decimal(0))
    excluded_count: Mapped[int] = mapped_column(default=0)

    xml: Mapped[str] = mapped_column(Text)

    generated_at: Mapped[dt.datetime] = mapped_column(index=True)
    generated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), default=None
    )

    @property
    def filename(self) -> str:
        return f"exogena-{self.year}-{self.id}.xml"

    def __repr__(self) -> str:
        return f"<ExogenaGeneration {self.year} #{self.id}>"
