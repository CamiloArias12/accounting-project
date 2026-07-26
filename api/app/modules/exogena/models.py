"""The record of every generation, and the file it produced."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin

MONEY = Numeric(18, 2)


class ExogenaGeneration(Base, TimestampMixin):
    """One run, kept with the file it produced.

    The XML is stored rather than regenerated on demand. A filed document has
    to come back byte for byte: the vouchers behind it can change afterwards —
    a reversal, a correction — and rebuilding it later would hand back a
    different file under the same identifier.
    """

    __tablename__ = "exogena_generations"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True)

    #: The parameters, kept so a past run can be explained without guessing.
    threshold_uvt: Mapped[Decimal] = mapped_column(MONEY)
    uvt_value: Mapped[Decimal | None] = mapped_column(MONEY, default=None)
    threshold_pesos: Mapped[Decimal] = mapped_column(MONEY, default=Decimal(0))

    #: The filer as it stood that day. Settings change; a filed report
    #: does not.
    filer_nit: Mapped[str] = mapped_column(String(20), default="")
    filer_name: Mapped[str] = mapped_column(String(150), default="")

    record_count: Mapped[int] = mapped_column(default=0)
    total_gross: Mapped[Decimal] = mapped_column(MONEY, default=Decimal(0))
    total_withheld: Mapped[Decimal] = mapped_column(MONEY, default=Decimal(0))
    #: How many third parties fell below the threshold, so the number that did
    #: not make the file is visible without reading the log.
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
