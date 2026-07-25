from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

pool = ConnectionPool.from_url(
    str(settings.REDIS_URL),
    decode_responses=True,
)


def get_redis() -> Redis:
    """Dependencia de FastAPI: cliente Redis sobre el pool compartido."""
    return Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    await pool.aclose()
