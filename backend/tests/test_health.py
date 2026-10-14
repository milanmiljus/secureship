from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app


def test_health_returns_200():
    """GET /health returns 200 with the expected structure."""
    with (
        patch("main.AsyncSessionLocal") as mock_session_local,
        patch("main.httpx.AsyncClient") as mock_http_client,
    ):
        # Mock DB session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_http_client.return_value = mock_client

        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "db_reachable" in body
    assert "ollama_reachable" in body
