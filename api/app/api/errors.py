"""Mapping of business errors to HTTP responses.

Registering handlers here keeps every endpoint free of try/except blocks whose
only job is turning an exception into a status code.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.errors import (
    AccountAlreadyExists,
    AccountHasChildren,
    AccountNotDeleted,
    AccountNotFound,
    ParentAccountDeleted,
    ParentAccountMissing,
)
from app.services.puc_import import SpreadsheetError

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    AccountNotFound: status.HTTP_404_NOT_FOUND,
    AccountAlreadyExists: status.HTTP_409_CONFLICT,
    AccountHasChildren: status.HTTP_409_CONFLICT,
    AccountNotDeleted: status.HTTP_409_CONFLICT,
    ParentAccountMissing: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ParentAccountDeleted: status.HTTP_422_UNPROCESSABLE_CONTENT,
    SpreadsheetError: status.HTTP_400_BAD_REQUEST,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _handler(status_code))


def _handler(status_code: int) -> Handler:
    async def handle(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handle
