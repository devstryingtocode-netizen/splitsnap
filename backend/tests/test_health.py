import httpx
import pytest

from app.main import app


@pytest.mark.anyio
async def test_health_check_returns_ok() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_http_errors_use_structured_response() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "http_error", "message": "Not Found"}
    }
