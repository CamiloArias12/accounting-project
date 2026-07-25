"""Wire format. Lives in the web adapter because JSON shape is a delivery
concern, not a business one — the entity must not change because a client wants
a different field name."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.accounts.application.queries import ImportOutcome
from app.modules.accounts.domain.account import Account, AccountNode
from app.modules.accounts.domain.puc import (
    AccountLevel,
    InvalidAccountCode,
    Nature,
    validate_code,
)


class AccountCreateRequest(BaseModel):
    code: str = Field(examples=["110505"])
    name: str = Field(min_length=1, max_length=255, examples=["CAJA GENERAL"])
    nature: Nature = Field(examples=[Nature.DEBIT])
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def code_must_follow_puc(cls, value: str) -> str:
        try:
            return validate_code(value)
        except InvalidAccountCode as exc:
            raise ValueError(str(exc)) from exc


class AccountUpdateRequest(BaseModel):
    """The code is immutable: it defines the account's level and parent."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    nature: Nature | None = None
    is_active: bool | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    nature: Nature
    level: AccountLevel
    parent_code: str | None
    is_active: bool
    deleted_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def of(cls, account: Account) -> AccountResponse:
        return cls.model_validate(account)


class AccountNodeResponse(AccountResponse):
    children: list[AccountNodeResponse] = Field(default_factory=list)

    @classmethod
    def of_node(cls, node: AccountNode) -> AccountNodeResponse:
        return cls(
            **AccountResponse.of(node.account).model_dump(),
            children=[cls.of_node(child) for child in node.children],
        )


class RowErrorResponse(BaseModel):
    row: int = Field(description="Row number in the sheet, 1-indexed")
    code: str | None
    message: str


class ImportResponse(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[RowErrorResponse] = Field(default_factory=list)

    @classmethod
    def of(cls, outcome: ImportOutcome) -> ImportResponse:
        return cls(
            created=outcome.created,
            updated=outcome.updated,
            skipped=outcome.skipped,
            errors=[
                RowErrorResponse(row=e.row, code=e.code, message=e.message)
                for e in outcome.errors
            ],
        )
