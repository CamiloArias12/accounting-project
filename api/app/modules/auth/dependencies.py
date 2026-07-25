"""The authentication dependency other modules declare.

Authentication is cross-cutting, so `accounts` importing this is expected: in
this style a feature depends on the auth module the same way it depends on the
database session.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.security import subject_of
from app.modules.auth.service import AuthService
from app.shared.config import settings
from app.shared.database import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_service(session: SessionDep) -> AuthService:
    return AuthService(session)


ServiceDep = Annotated[AuthService, Depends(get_service)]


async def current_user(
    token: Annotated[str, Depends(oauth2_scheme)], service: ServiceDep
) -> User:
    """Verifies the token and loads the user.

    The database is hit on purpose rather than trusting the token's claims: a
    deactivated user would otherwise keep access until their token expired.
    """
    return await service.identify(subject_of(token))


#: Declared on an endpoint to require a valid bearer token.
CurrentUser = Annotated[User, Depends(current_user)]
