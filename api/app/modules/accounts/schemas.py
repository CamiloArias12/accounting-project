"""Pydantic at the edge: what comes in and what goes out over HTTP."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.accounts.puc import (
    AccountLevel,
    InvalidAccountCode,
    Nature,
    validate_code,
)


class AccountCreate(BaseModel):
    code: str = Field(examples=["110505"])
    name: str = Field(min_length=1, max_length=255, examples=["CAJA GENERAL"])
    nature: Nature = Field(examples=[Nature.DEBIT])
    is_active: bool = True
    requires_third_party: bool = Field(
        default=False,
        description="Whether every entry on this account must name a third party",
    )
    dian_concept: str | None = Field(
        default=None,
        max_length=10,
        description="DIAN concept for información exógena; null means not reportable",
        examples=["5002"],
    )
    is_withholding: bool = Field(
        default=False,
        description="Whether amounts here are the withholding, not the payment",
    )

    @field_validator("code")
    @classmethod
    def code_must_follow_puc(cls, value: str) -> str:
        try:
            return validate_code(value)
        except InvalidAccountCode as exc:
            raise ValueError(str(exc)) from exc


class AccountUpdate(BaseModel):
    """The code is immutable: it defines the account's level and parent."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    nature: Nature | None = None
    is_active: bool | None = None
    requires_third_party: bool | None = None
    dian_concept: str | None = Field(default=None, max_length=10)
    is_withholding: bool | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    nature: Nature
    level: AccountLevel
    parent_code: str | None
    is_active: bool
    requires_third_party: bool
    dian_concept: str | None
    is_withholding: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AccountNode(AccountRead):
    """An account with its descendants, for the tree endpoint."""

    children: list[AccountNode] = Field(default_factory=list)


class RowError(BaseModel):
    row: int = Field(description="Row number in the sheet, 1-indexed")
    code: str | None
    message: str


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[RowError] = Field(default_factory=list)
