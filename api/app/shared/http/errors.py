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
from app.modules.exogena.errors import GenerationNotFound, ThresholdNeedsUvt
from app.modules.exogena.report import ExogenaError
from app.modules.locations.errors import (
    CityNotFound,
    CountryNotFound,
    DepartmentNotFound,
    InconsistentPlace,
)
from app.modules.periods.errors import (
    PeriodAlreadyClosed,
    PeriodAlreadyOpen,
    PeriodClosed,
)
from app.modules.periods.period import InvalidPeriod
from app.modules.third_parties.documents import InvalidDocument
from app.modules.third_parties.errors import (
    IncompleteThirdParty,
    ThirdPartyAlreadyExists,
    ThirdPartyNotDeleted,
    ThirdPartyNotFound,
)
from app.modules.uvt.errors import UvtValueNotFound
from app.modules.vouchers.errors import (
    AccountNotPostable,
    ThirdPartyRequired,
    UnknownThirdParty,
    VoucherAlreadyPosted,
    VoucherAlreadyReversed,
    VoucherIsReversal,
    VoucherNotEditable,
    VoucherNotFound,
    VoucherNotPosted,
)
from app.modules.vouchers.posting import PostingError

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
    # third parties
    ThirdPartyNotFound: status.HTTP_404_NOT_FOUND,
    ThirdPartyAlreadyExists: status.HTTP_409_CONFLICT,
    ThirdPartyNotDeleted: status.HTTP_409_CONFLICT,
    IncompleteThirdParty: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # Not a Pydantic error: the check digit and the format of a document depend
    # on its type, which only the domain knows.
    InvalidDocument: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # vouchers
    VoucherNotFound: status.HTTP_404_NOT_FOUND,
    VoucherNotEditable: status.HTTP_409_CONFLICT,
    VoucherAlreadyPosted: status.HTTP_409_CONFLICT,
    VoucherNotPosted: status.HTTP_409_CONFLICT,
    VoucherAlreadyReversed: status.HTTP_409_CONFLICT,
    VoucherIsReversal: status.HTTP_409_CONFLICT,
    AccountNotPostable: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ThirdPartyRequired: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UnknownThirdParty: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # Not a Pydantic error: whether an entry balances is a property of the
    # whole voucher, which no field validator can see.
    PostingError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # accounting periods
    PeriodClosed: status.HTTP_409_CONFLICT,
    PeriodAlreadyClosed: status.HTTP_409_CONFLICT,
    PeriodAlreadyOpen: status.HTTP_409_CONFLICT,
    InvalidPeriod: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # exógena
    GenerationNotFound: status.HTTP_404_NOT_FOUND,
    ThresholdNeedsUvt: status.HTTP_409_CONFLICT,
    UvtValueNotFound: status.HTTP_404_NOT_FOUND,
    # Not a Pydantic error: whether the informante's own NIT checks out is a
    # rule about the document, which no field validator knows.
    ExogenaError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # locations
    CountryNotFound: status.HTTP_404_NOT_FOUND,
    DepartmentNotFound: status.HTTP_404_NOT_FOUND,
    CityNotFound: status.HTTP_404_NOT_FOUND,
    InconsistentPlace: status.HTTP_422_UNPROCESSABLE_CONTENT,
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
