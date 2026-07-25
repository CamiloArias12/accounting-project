from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.domain.user import User


class RegisterRequest(BaseModel):
    email: EmailStr
    # Long enough to matter, capped because Argon2 hashes the whole input.
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool

    @classmethod
    def of(cls, user: User) -> UserResponse:
        # `id` is set once the row is persisted; a user reaching the web layer
        # always has one.
        assert user.id is not None
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
        )
