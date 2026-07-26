from httpx import AsyncClient


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


async def test_health_needs_no_token(client: AsyncClient) -> None:
    """Probes run before anything can authenticate."""
    assert (await client.get("/api/v1/health")).status_code == 200
