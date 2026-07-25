from __future__ import annotations

from typing import Protocol

from app.modules.auth.domain.user import User


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_id(self, user_id: int) -> User | None: ...

    async def add(self, user: User) -> User: ...


class PasswordHasher(Protocol):
    """Hashing is a detail: the algorithm changes without touching a use case."""

    def hash(self, plain: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> bool: ...


class TokenIssuer(Protocol):
    def issue(self, subject: str) -> str: ...

    def subject_of(self, token: str) -> str:
        """The subject the token was issued for, or raises if it is not valid."""
        ...
