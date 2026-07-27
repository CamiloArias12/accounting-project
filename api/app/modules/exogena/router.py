from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
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


def _as_download(
    generation: ExogenaGeneration, *, status_code: int = status.HTTP_200_OK
) -> Response:
    return Response(
        content=generation.xml,
        media_type="application/xml",
        status_code=status_code,
        headers={
            "Content-Disposition": f'attachment; filename="{generation.filename}"'
        },
    )


@router.post(
    "/generate",
    response_model=GenerationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "content": {"application/xml": {}},
            "description": "The record, or the file itself with `download=true`",
        }
    },
)
async def generate(
    payload: GenerateRequest,
    service: ServiceDep,
    user: CurrentUser,
    download: Annotated[
        bool,
        Query(description="Answer with the XML as an attachment instead"),
    ] = False,
) -> ExogenaGeneration | Response:
    generation = await service.generate(
        payload,
        nit=settings.COMPANY_NIT,
        legal_name=settings.COMPANY_LEGAL_NAME,
        user_id=user.id,
    )
    if download:
        return _as_download(generation, status_code=status.HTTP_201_CREATED)
    return generation


@router.get("/history", response_model=list[GenerationRead])
async def history(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ExogenaGeneration]:
    return list(await service.history(limit=limit))


@router.get("/history/{generation_id}/file")
async def download(generation_id: int, service: ServiceDep) -> Response:
    return _as_download(await service.get(generation_id))


@router.get("/history/{generation_id}", response_model=GenerationRead)
async def read_generation(generation_id: int, service: ServiceDep) -> ExogenaGeneration:
    return await service.get(generation_id)
