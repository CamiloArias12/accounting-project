from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.puc import AccountLevel, InvalidAccountCode, Nature, validate_code


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["CAJA GENERAL"])
    nature: Nature = Field(examples=[Nature.DEBIT])
    is_active: bool = True


class AccountCreate(AccountBase):
    code: str = Field(examples=["110505"])

    @field_validator("code")
    @classmethod
    def code_must_follow_puc(cls, value: str) -> str:
        # Level and parent are derived from the code, so a malformed one must
        # never reach the service.
        try:
            return validate_code(value)
        except InvalidAccountCode as exc:
            raise ValueError(str(exc)) from exc


class AccountUpdate(BaseModel):
    """The code is immutable: it defines the account's level and parent."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    nature: Nature | None = None
    is_active: bool | None = None


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    code: str
    level: AccountLevel
    parent_code: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AccountNode(AccountRead):
    """An account plus its descendants, used to render the tree."""

    children: list[AccountNode] = Field(default_factory=list)


class RowError(BaseModel):
    """A single spreadsheet row that could not be imported."""

    row: int = Field(description="Row number in the sheet, 1-indexed")
    code: str | None
    message: str


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[RowError] = Field(default_factory=list)
