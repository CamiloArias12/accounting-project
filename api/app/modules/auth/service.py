"""Registration and sign-in."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.errors import (
    EmailAlreadyRegistered,
    InactiveUser,
    InvalidCredentials,
    InvalidToken,
)
from app.modules.auth.models import User
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.security import hash_password, issue_token, verify_password


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, payload: RegisterRequest) -> User:
        email = payload.email.strip().lower()

        if await self._by_email(email) is not None:
            raise EmailAlreadyRegistered(email)

        user = User(
            email=email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def log_in(self, email: str, password: str) -> str:
        user = await self._by_email(email.strip().lower())

        # The hash is verified even when the user is missing, so the response
        # time does not reveal which emails exist.
        stored = user.hashed_password if user else hash_password("no-such-user")
        matches = verify_password(password, stored)

        if user is None or not matches:
            raise InvalidCredentials
        if not user.is_active:
            raise InactiveUser(user.email)

        return issue_token(user.email)

    async def identify(self, email: str) -> User:
        """Resolves a token's subject into the user behind it."""
        user = await self._by_email(email)

        if user is None:
            raise InvalidToken
        if not user.is_active:
            raise InactiveUser(user.email)

        return user

    async def _by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
