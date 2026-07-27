from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.uvt.models import RunStatus, UvtSource
from app.modules.uvt.provider import MAX_YEAR, MIN_YEAR


class UvtValueRead(BaseModel):
    """Pydantic at the edge: what the UVT looks like over HTTP."""
    model_config = ConfigDict(from_attributes=True)

    year: int
    value: Decimal
    source: UvtSource
    provider: str | None
    fetched_at: dt.datetime | None


class UvtValueSet(BaseModel):
    """A value typed in by hand, for a year the source does not carry yet."""

    value: Decimal = Field(gt=0, decimal_places=2, examples=["49799.00"])


class UvtRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    status: RunStatus
    provider: str
    attempts: int
    value: Decimal | None
    detail: str | None
    started_at: dt.datetime
    finished_at: dt.datetime
    duration_ms: int


class UvtRefreshRequest(BaseModel):
    year: int = Field(ge=MIN_YEAR, le=MAX_YEAR)


class UvtRefreshAccepted(BaseModel):
    """Answered before the work starts; `runs` is where the outcome shows up."""

    year: int
    accepted: bool = True
