from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.modules.accounts.infrastructure.http.dependencies import get_repository
from app.modules.accounts.infrastructure.repository import SqlAlchemyAccountRepository
from app.shared.database import get_session
from app.shared.models import Base
from app.shared.redis import get_redis
from tests.fakes import FakeRedis


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    """An in-memory SQLite session, with the schema rebuilt per test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client against the app, with the test session injected.

    The cache decorator is left out: it is exercised on its own in
    `test_cache.py`, and skipping it keeps every other test reading the
    database it just wrote to.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_repository] = lambda: SqlAlchemyAccountRepository(
        session
    )
    app.dependency_overrides[get_redis] = FakeRedis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """A client carrying a bearer token, for endpoints that require one."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "tester@example.com",
            "password": "sup3r-secret",
            "full_name": "Tester",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "tester@example.com", "password": "sup3r-secret"},
    )
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client
