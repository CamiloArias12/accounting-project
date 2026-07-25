"""Composition root for the auth module."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.ports import UserRepository
from app.modules.auth.application.use_cases.authenticate import (
    IdentifyUser,
    LogIn,
    RegisterUser,
)
from app.modules.auth.domain.user import User
from app.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from app.modules.auth.infrastructure.security import (
    Argon2PasswordHasher,
    JwtTokenIssuer,
)
from app.shared.config import settings
from app.shared.database import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


def get_users(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)


UsersDep = Annotated[UserRepository, Depends(get_users)]


def register_user(users: UsersDep) -> RegisterUser:
    return RegisterUser(users, Argon2PasswordHasher())


def log_in(users: UsersDep) -> LogIn:
    return LogIn(users, Argon2PasswordHasher(), JwtTokenIssuer())


def identify_user(users: UsersDep) -> IdentifyUser:
    return IdentifyUser(users, JwtTokenIssuer())


RegisterUserDep = Annotated[RegisterUser, Depends(register_user)]
LogInDep = Annotated[LogIn, Depends(log_in)]
IdentifyUserDep = Annotated[IdentifyUser, Depends(identify_user)]


async def current_user(token: TokenDep, identify: IdentifyUserDep) -> User:
    return await identify(token)


#: Declared on an endpoint to require a valid bearer token.
CurrentUserDep = Annotated[User, Depends(current_user)]
