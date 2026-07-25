from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import RedisDep, SessionDep

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str
    database: str
    redis: str


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Liveness: answers without touching external dependencies."""
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthStatus)
async def readiness(session: SessionDep, redis: RedisDep) -> HealthStatus:
    """Readiness: checks Postgres and Redis."""
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
