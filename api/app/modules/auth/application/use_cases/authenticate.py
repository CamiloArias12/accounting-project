from __future__ import annotations

from dataclasses import dataclass

from app.modules.auth.application.ports import (
    PasswordHasher,
    TokenIssuer,
    UserRepository,
)
from app.modules.auth.domain.errors import (
    EmailAlreadyRegistered,
    InactiveUser,
    InvalidCredentials,
    InvalidToken,
)
from app.modules.auth.domain.user import User


@dataclass(frozen=True, slots=True)
class Credentials:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class Registration:
    email: str
    password: str
    full_name: str


@dataclass(frozen=True, slots=True)
class AccessToken:
    access_token: str
    token_type: str = "bearer"


class RegisterUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def __call__(self, request: Registration) -> User:
        email = request.email.strip().lower()
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegistered(email)

        return await self._users.add(
            User.register(
                email=email,
                hashed_password=self._hasher.hash(request.password),
                full_name=request.full_name,
            )
        )


class LogIn:
    def __init__(
        self, users: UserRepository, hasher: PasswordHasher, tokens: TokenIssuer
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def __call__(self, credentials: Credentials) -> AccessToken:
        user = await self._users.get_by_email(credentials.email.strip().lower())

        # The hash is verified even when the user is missing, so the response
        # time does not reveal which emails exist.
        hashed = user.hashed_password if user else self._hasher.hash("no-such-user")
        matches = self._hasher.verify(credentials.password, hashed)

        if user is None or not matches:
            raise InvalidCredentials
        if not user.is_active:
            raise InactiveUser(user.email)

        return AccessToken(access_token=self._tokens.issue(user.email))


class IdentifyUser:
    """Resolves the bearer token of a request into the user behind it."""

    def __init__(self, users: UserRepository, tokens: TokenIssuer) -> None:
        self._users = users
        self._tokens = tokens

    async def __call__(self, token: str) -> User:
        email = self._tokens.subject_of(token)
        user = await self._users.get_by_email(email)

        if user is None:
            raise InvalidToken
        if not user.is_active:
            raise InactiveUser(user.email)

        return user
