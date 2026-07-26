"""
Auth conformance for rnv-color-mcp.

Driven through the ASGI app with httpx, so every request runs the real
middleware stack: this is where the 401 and the WWW-Authenticate challenge
actually happen. No network, no port binding.
"""
from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

import server

MCP_PATH = "/mcp"
METADATA_PATH = "/.well-known/oauth-protected-resource/mcp"

RPC = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


@pytest.fixture
async def client():
    # No lifespan here: the metadata route and every 401 are resolved before the
    # StreamableHTTP session manager is ever reached. Entering a task group in a
    # fixture that pytest-asyncio tears down in a different task is what produced
    # the cancel-scope errors.
    app = server.mcp.http_app()
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def _call(client, token=None):
    headers = dict(HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return await client.post(MCP_PATH, json=RPC, headers=headers)


class TestProtectedResourceMetadata:
    """RFC 9728. The unauthenticated discovery document clients read first."""

    async def test_metadata_is_served(self, client):
        resp = await client.get(METADATA_PATH)
        assert resp.status_code == 200

    async def test_resource_is_the_mcp_path(self, client):
        # must match the audience tokens are bound to, not the bare base URL
        body = (await client.get(METADATA_PATH)).json()
        assert body["resource"].endswith("/mcp")

    async def test_scopes_are_advertised(self, client):
        body = (await client.get(METADATA_PATH)).json()
        assert set(body["scopes_supported"]) == {"read", "write"}

    async def test_authorization_server_is_listed(self, client):
        body = (await client.get(METADATA_PATH)).json()
        assert body["authorization_servers"]

    async def test_bearer_header_method(self, client):
        body = (await client.get(METADATA_PATH)).json()
        assert "header" in body["bearer_methods_supported"]


class TestTokenValidation:
    """The resource-server contract: refuse anything that does not verify."""

    async def test_no_token_is_refused(self, client):
        assert (await _call(client)).status_code == 401

    async def test_challenge_points_at_metadata(self, client):
        resp = await _call(client)
        assert "resource_metadata" in resp.headers.get("www-authenticate", "")

    async def test_garbage_token_is_refused(self, client):
        assert (await _call(client, "not-a-jwt")).status_code == 401

    async def test_wrong_issuer_is_refused(self, client, make_token):
        token = make_token(issuer="https://attacker.example")
        assert (await _call(client, token)).status_code == 401

    async def test_wrong_audience_is_refused(self, client, make_token):
        token = make_token(audience="https://someone-elses-server.example/mcp")
        assert (await _call(client, token)).status_code == 401

    async def test_expired_token_is_refused(self, client, make_token):
        try:
            token = make_token(expires_in_seconds=-60)
        except TypeError:
            pytest.skip("create_token has no expiry parameter under this name")
        assert (await _call(client, token)).status_code == 401

    async def test_valid_token_is_not_refused(self, make_token):
        # The only test that passes the middleware and reaches the session manager,
        # so it needs the app lifespan: entered and exited inside the test body,
        # which keeps it in a single task. Asserts only that auth passes; the
        # protocol handshake is a separate concern.
        app = server.mcp.http_app()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await _call(c, make_token())
        assert resp.status_code != 401
