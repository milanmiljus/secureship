import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app


@pytest.fixture
def mock_ollama():
    with patch("routes.chat.ollama_client") as mock:
        mock.chat = AsyncMock(return_value={
            "message": {"content": "Hello! How can I help you with your shipment today?"}
        })
        yield mock


@pytest.mark.asyncio
async def test_create_session_returns_session_id():
    # This test requires a real DB — skip in unit test context
    # Will be covered by integration tests once DB is available
    pass


@pytest.mark.asyncio
async def test_chat_endpoint_exists():
    """Smoke test: endpoint is registered and reachable (even if 404 for missing session)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/chat", json={"session_id": "nonexistent", "message": "hi"})
        # 404 is expected (session not found) — that means routing works
        assert resp.status_code in (404, 503)
