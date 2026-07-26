from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.uvt.models import UvtFetchRun, UvtValue
from app.modules.uvt.provider import (
    MAX_YEAR,
    MIN_YEAR,
    HttpUvtProvider,
    SimulatedUvtProvider,
    UvtProvider,
)
from app.modules.uvt.schemas import (
    UvtRefreshAccepted,
    UvtRefreshRequest,
    UvtRunRead,
    UvtValueRead,
    UvtValueSet,
)
from app.modules.uvt.service import UvtService
from app.shared.config import settings
from app.shared.database import SessionFactory, get_session

router = APIRouter(
    prefix="/uvt",
    tags=["uvt"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
Year = Annotated[int, Path(ge=MIN_YEAR, le=MAX_YEAR)]


def get_provider() -> UvtProvider:
    """The source the refresh talks to, chosen by configuration.

    `http` by default, reading a published table over the network. The DIAN
    itself publishes the UVT only as a resolution — a PDF in the normograma —
    and Datos Abiertos carries no dataset for it, so there is no official
    machine-readable endpoint to point at; see `provider.DEFAULT_SOURCE_URL`.

    `simulated` answers from a hardcoded table and is what the tests use, so a
    suite never depends on somebody else's uptime.
    """
    if settings.UVT_SOURCE == "simulated":
        return SimulatedUvtProvider(
            failure_rate=settings.UVT_SOURCE_FAILURE_RATE,
            latency_seconds=settings.UVT_SOURCE_LATENCY_SECONDS,
        )

    return HttpUvtProvider(
        url=settings.UVT_SOURCE_URL,
        timeout_seconds=settings.UVT_SOURCE_TIMEOUT_SECONDS,
    )


ProviderDep = Annotated[UvtProvider, Depends(get_provider)]


def get_service(session: SessionDep) -> UvtService:
    return UvtService(session)


ServiceDep = Annotated[UvtService, Depends(get_service)]


@router.get("", response_model=list[UvtValueRead])
async def list_values(service: ServiceDep) -> list[UvtValue]:
    return list(await service.all_values())


@router.get("/runs", response_model=list[UvtRunRead])
async def list_runs(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[UvtFetchRun]:
    """Every attempt to refresh, successful or not.

    The failures are the point: a threshold that quietly used a stale UVT
    because a fetch died is what this list makes visible.
    """
    return list(await service.runs(limit=limit))


@router.post(
    "/refresh",
    response_model=UvtRefreshAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh(
    payload: UvtRefreshRequest,
    background: BackgroundTasks,
    provider: ProviderDep,
) -> UvtRefreshAccepted:
    """Ask for a year to be refreshed and answer immediately.

    202, not 200: the source is a third party that may be slow or down, and
    three attempts with backoff is not something a caller should hold a
    connection open for. The outcome shows up under `/uvt/runs`.
    """
    background.add_task(_refresh_in_background, payload.year, provider)
    return UvtRefreshAccepted(year=payload.year)


@router.get("/{year}", response_model=UvtValueRead)
async def read_value(year: Year, service: ServiceDep) -> UvtValue:
    await service.value_for(year)
    stored = [v for v in await service.all_values() if v.year == year]
    return stored[0]


@router.put("/{year}", response_model=UvtValueRead)
async def set_value(year: Year, payload: UvtValueSet, service: ServiceDep) -> UvtValue:
    """Type in a value the source does not carry yet.

    A later refresh will not overwrite it: a figure read off the resolution
    outranks whatever the source makes of it.
    """
    return await service.set_manually(year, payload.value)


async def _refresh_in_background(year: int, provider: UvtProvider) -> None:
    """Runs after the response has gone out, on a session of its own.

    The request's session is closed by then, so this opens another; and it
    swallows nothing — the outcome, including the failure, lands in
    `uvt_fetch_runs`.
    """
    async with SessionFactory() as session:
        await UvtService(session).refresh(year, provider)
