from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.periods.period import MAX_PERIOD_YEAR, MIN_PERIOD_YEAR
from app.modules.vouchers.posting import ZERO, VoucherStatus


class CompanyRead(BaseModel):
    """The company the books belong to, read back from configuration."""

    nit: str = Field(examples=["900123456-7"])
    legal_name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class VoucherLineInput(BaseModel):
    account_code: str = Field(min_length=1, max_length=20, examples=["110505"])
    third_party_id: int | None = Field(
        default=None,
        description="Required on accounts flagged `requires_third_party`",
    )
    debit: Decimal = Field(default=ZERO, ge=0, decimal_places=2, examples=["150000.00"])
    credit: Decimal = Field(default=ZERO, ge=0, decimal_places=2, examples=["0.00"])
    description: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def one_column_only(self) -> VoucherLineInput:
        if self.debit == ZERO and self.credit == ZERO:
            raise ValueError("A line must carry either a debit or a credit")
        if self.debit != ZERO and self.credit != ZERO:
            raise ValueError("A line cannot be both a debit and a credit")
        return self


class VoucherCreate(BaseModel):
    date: dt.date
    description: str = Field(min_length=1, max_length=255)
    period_year: int | None = Field(
        default=None, ge=MIN_PERIOD_YEAR, le=MAX_PERIOD_YEAR
    )
    period_month: int | None = Field(default=None, ge=1, le=12)
    lines: list[VoucherLineInput] = Field(min_length=1)

    @model_validator(mode="after")
    def period_is_whole_or_absent(self) -> VoucherCreate:
        if (self.period_year is None) != (self.period_month is None):
            raise ValueError("A period needs both its year and its month")
        return self


class VoucherUpdate(BaseModel):
    """Only a draft can be updated, and `lines` replaces the whole entry."""

    date: dt.date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=255)
    period_year: int | None = Field(
        default=None, ge=MIN_PERIOD_YEAR, le=MAX_PERIOD_YEAR
    )
    period_month: int | None = Field(default=None, ge=1, le=12)
    lines: list[VoucherLineInput] | None = Field(default=None, min_length=1)


class VoucherReverse(BaseModel):
    """What to write on the reversing entry."""

    date: dt.date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=255)


class VoucherLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_number: int
    account_code: str
    third_party_id: int | None
    debit: Decimal
    credit: Decimal
    description: str | None


class VoucherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int | None
    date: dt.date
    period_year: int
    period_month: int
    description: str
    status: VoucherStatus
    posted_at: dt.datetime | None
    created_by_user_id: int | None
    posted_by_user_id: int | None
    reverses_voucher_id: int | None
    is_reversal: bool
    is_reversed: bool
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    lines: list[VoucherLineRead]
    created_at: dt.datetime
    updated_at: dt.datetime
