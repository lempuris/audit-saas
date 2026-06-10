import pytest
from httpx import ASGITransport, AsyncClient

from database.session import get_db
from main import app


class FakeResult:
    def scalar_one(self) -> int:
        return 1


class FakeSession:
    async def execute(self, _query: object) -> FakeResult:
        return FakeResult()


@pytest.mark.unit
async def test_health_returns_ok_when_database_reachable() -> None:
    app.dependency_overrides[get_db] = lambda: FakeSession()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


@pytest.mark.integration
async def test_health_against_real_database() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
