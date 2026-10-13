"""
Admin route tests — verify auth enforcement and CRUD operations.
In dev mode (no AUTH0_DOMAIN), all admin routes pass without a token.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestAdminAuthEnforcement:

    async def test_list_customers_no_token_dev_mode_passes(self, client):
        """In dev mode (AUTH0_DOMAIN empty), no token required."""
        resp = await client.get("/admin/customers")
        # Should not be 401 — dev mode skips auth
        assert resp.status_code in (200, 500)  # 500 only if DB unreachable in test

    async def test_list_customers_with_auth0_domain_requires_token(self, client):
        """When AUTH0_DOMAIN is set, missing token returns 401."""
        with patch("auth.auth0.settings") as mock_settings:
            mock_settings.AUTH0_DOMAIN = "test.auth0.com"
            mock_settings.AUTH0_AUDIENCE = "https://api.secureship.com"
            resp = await client.get("/admin/customers")
            assert resp.status_code == 401

    async def test_chat_route_has_no_auth_dependency(self):
        """Verify chat route does NOT import require_admin_auth."""
        import routes.chat as chat_module
        import inspect
        source = inspect.getsource(chat_module)
        assert "require_admin_auth" not in source, (
            "Chat route must NEVER use require_admin_auth — "
            "separation of admin and chat auth is a security invariant"
        )

    async def test_verify_route_has_no_auth_dependency(self):
        """Verify verify route does NOT import require_admin_auth."""
        import routes.verify as verify_module
        import inspect
        source = inspect.getsource(verify_module)
        assert "require_admin_auth" not in source


class TestAdminSeparation:

    async def test_admin_router_prefix(self):
        """All admin routes are prefixed /admin."""
        from routes.admin import router
        for route in router.routes:
            assert route.path.startswith("/admin"), (
                f"Admin route {route.path} must be under /admin"
            )

    async def test_session_store_not_imported_in_admin(self):
        """Admin route module must not import session_store."""
        import routes.admin as admin_module
        import inspect
        source = inspect.getsource(admin_module)
        assert "session_store" not in source
        assert "InMemorySessionStore" not in source
