from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_session
from app.shared.redis import get_redis

router = APIRouter(tags=["health"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


class HealthStatus(BaseModel):
    status: str
    database: str
    redis: str


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthStatus)
async def readiness(session: SessionDep, redis: RedisDep) -> HealthStatus:
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:
        database = f"error: {exc.__class__.__name__}"

    try:
        await redis.ping()
        cache = "ok"
    except Exception as exc:
        cache = f"error: {exc.__class__.__name__}"

    overall = "ok" if database == "ok" and cache == "ok" else "degraded"
    return HealthStatus(status=overall, database=database, redis=cache)
