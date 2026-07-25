"""Maps business errors to HTTP responses.

The only place in the codebase that knows both a domain error and a status
code. Registering handlers here keeps every endpoint free of try/except blocks
whose sole job is choosing a number.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.modules.accounts.errors import (
    AccountAlreadyExists,
    AccountHasChildren,
    AccountNotDeleted,
    AccountNotFound,
    ParentAccountDeleted,
    ParentAccountMissing,
)
from app.modules.accounts.importer import SpreadsheetError
from app.modules.auth.errors import (
    EmailAlreadyRegistered,
    InactiveUser,
    InvalidCredentials,
    InvalidToken,
)

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    # accounts
    AccountNotFound: status.HTTP_404_NOT_FOUND,
    AccountAlreadyExists: status.HTTP_409_CONFLICT,
    AccountHasChildren: status.HTTP_409_CONFLICT,
    AccountNotDeleted: status.HTTP_409_CONFLICT,
    ParentAccountMissing: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ParentAccountDeleted: status.HTTP_422_UNPROCESSABLE_CONTENT,
    SpreadsheetError: status.HTTP_400_BAD_REQUEST,
    # auth
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    InvalidToken: status.HTTP_401_UNAUTHORIZED,
    InactiveUser: status.HTTP_403_FORBIDDEN,
    EmailAlreadyRegistered: status.HTTP_409_CONFLICT,
}

#: 401s must advertise the scheme, or a client cannot know how to retry.
_AUTH_CHALLENGE = {InvalidCredentials, InvalidToken}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(
            error_type, _handler(status_code, error_type in _AUTH_CHALLENGE)
        )


def _handler(status_code: int, challenge: bool) -> Handler:
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if challenge else None
        return JSONResponse(
            status_code=status_code, content={"detail": str(exc)}, headers=headers
        )

    return handle
