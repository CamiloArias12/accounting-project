from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import current_user
from app.modules.auth.models import User
from app.modules.exogena.models import ExogenaGeneration
from app.modules.exogena.schemas import GenerateRequest, GenerationRead
from app.modules.exogena.service import ExogenaService
from app.shared.config import settings
from app.shared.database import get_session

router = APIRouter(
    prefix="/exogena",
    tags=["exogena"],
    dependencies=[Depends(current_user)],
    responses={401: {"description": "Missing or invalid token"}},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(current_user)]


def get_service(session: SessionDep) -> ExogenaService:
    return ExogenaService(session)


ServiceDep = Annotated[ExogenaService, Depends(get_service)]


#: The file is XML, and browsers will render it inline unless told otherwise.
def _as_download(generation: ExogenaGeneration) -> Response:
    return Response(
        content=generation.xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{generation.filename}"'
        },
    )


@router.post("/generate")
async def generate(
    payload: GenerateRequest, service: ServiceDep, user: CurrentUser
) -> Response:
    """Build the report for a taxable year and hand it back as a download.

    The generation is recorded first and the bytes are kept with it, so the
    same file can be fetched again later — `/history/{id}/file` returns
    what was filed, not what the books would produce today.
    """
    generation = await service.generate(
        payload,
        nit=settings.COMPANY_NIT,
        legal_name=settings.COMPANY_LEGAL_NAME,
        user_id=user.id,
    )
    return _as_download(generation)


@router.get("/history", response_model=list[GenerationRead])
async def history(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ExogenaGeneration]:
    """Every generation, with the parameters it ran with."""
    return list(await service.history(limit=limit))


@router.get("/history/{generation_id}/file")
async def download(generation_id: int, service: ServiceDep) -> Response:
    """The file exactly as it was generated.

    Not rebuilt: the vouchers behind it may have moved since — a reversal, a
    correction — and a filed document has to come back byte for byte.
    """
    return _as_download(await service.get(generation_id))


@router.get("/history/{generation_id}", response_model=GenerationRead)
async def read_generation(generation_id: int, service: ServiceDep) -> ExogenaGeneration:
    return await service.get(generation_id)
