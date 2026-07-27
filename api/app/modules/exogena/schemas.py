from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.uvt.provider import MAX_YEAR, MIN_YEAR


class GenerateRequest(BaseModel):
    """Pydantic at the edge: what exógena looks like over HTTP."""
    year: int = Field(ge=MIN_YEAR, le=MAX_YEAR, examples=[2025])

    threshold_uvt: Decimal = Field(
        default=Decimal(0), ge=0, decimal_places=2, examples=["100.00"]
    )


class GenerationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    threshold_uvt: Decimal
    uvt_value: Decimal | None
    threshold_pesos: Decimal
    filer_nit: str
    filer_name: str
    record_count: int
    total_gross: Decimal
    total_withheld: Decimal
    excluded_count: int
    filename: str
    generated_at: dt.datetime
    generated_by_user_id: int | None
