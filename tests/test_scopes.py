"""
Per-tool scope enforcement for rnv-color-mcp.

The twelve tests in test_auth.py prove the server refuses a token it cannot
verify. These prove the harder thing: that a token it *does* verify is still
refused on a tool its scopes do not cover.

Driven over real HTTP against a real server, because the in-memory transport
refuses auth outright (FastMCPTransport._set_auth raises "This transport does
not support auth"). FastMCP's run_server_async binds a free port and yields the
URL, so the client speaks the actual protocol through the actual middleware.

Scoping is load-bearing here, not a style choice. server.mcp is a module-level
singleton and carries an asyncio.Event that binds to whichever event loop starts
it first, so only one server start per process is possible: a function-scoped
fixture starts a second server on a second loop and dies on the stale Event.
Hence one module-scoped server on one module-scoped loop.

TestPositiveControl is the diagnostic. If it fails, the harness is wrong, not the
server: tokens are not reaching the auth context and every other assertion here
is passing or failing for the wrong reason. Read it first.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from fastmcp import Client

try:
    from fastmcp.utilities.tests import run_server_async
except ImportError:  # pragma: no cover
    run_server_async = None

try:
    from fastmcp.client.auth import BearerAuth
except ImportError:  # pragma: no cover - import path fallback
    from fastmcp.client.auth.bearer import BearerAuth

import server

pytestmark = [
    pytest.mark.skipif(
        run_server_async is None,
        reason="fastmcp.utilities.tests.run_server_async unavailable in this version",
    ),
    pytest.mark.asyncio(loop_scope="module"),
]

WRITE_TOOL = "save_palette"
READ_TOOLS = {
    "mix_colors",
    "convert_color",
    "generate_harmony",
    "color_difference",
    "contrast_check",
    "transform_text",
    "list_palettes",
    "get_palette",
}

PALETTE = {"name": "scope-test", "colors": ["#0a0a0f", "#d2bc93"]}


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def url():
    """One real server, one port, one loop, for the whole module."""
    async with run_server_async(server.mcp) as running_url:
        yield running_url


@pytest.fixture(scope="module")
def read_token(keypair):
    return keypair.create_token(
        subject="rnv-test-read",
        issuer="https://rnvizion.dev",
        audience="https://rnvizion-rnv-color-mcp.hf.space/mcp",
        scopes=["read"],
    )


@pytest.fixture(scope="module")
def write_token(keypair):
    return keypair.create_token(
        subject="rnv-test-write",
        issuer="https://rnvizion.dev",
        audience="https://rnvizion-rnv-color-mcp.hf.space/mcp",
        scopes=["read", "write"],
    )


class TestPositiveControl:
    """If this class fails, stop: tokens are not reaching the auth context."""

    async def test_read_token_can_still_read(self, url, read_token):
        async with Client(url, auth=BearerAuth(read_token)) as c:
            result = await c.call_tool("convert_color", {"color": "#d2bc93"})
        assert result is not None

    async def test_write_token_can_write(self, url, write_token):
        async with Client(url, auth=BearerAuth(write_token)) as c:
            result = await c.call_tool(WRITE_TOOL, PALETTE)
        assert result is not None


class TestVisibility:
    """Component auth filters the tool list, not only the call."""

    async def test_read_token_does_not_see_the_write_tool(self, url, read_token):
        async with Client(url, auth=BearerAuth(read_token)) as c:
            names = {t.name for t in await c.list_tools()}
        assert WRITE_TOOL not in names

    async def test_read_token_sees_every_read_tool(self, url, read_token):
        async with Client(url, auth=BearerAuth(read_token)) as c:
            names = {t.name for t in await c.list_tools()}
        assert READ_TOOLS <= names

    async def test_write_token_sees_all_nine(self, url, write_token):
        async with Client(url, auth=BearerAuth(write_token)) as c:
            names = {t.name for t in await c.list_tools()}
        assert len(names) == 9
        assert WRITE_TOOL in names


class TestEnforcement:
    """The one that matters: a verified token, refused on scope."""

    async def test_read_token_is_refused_on_the_write_tool(self, url, read_token):
        with pytest.raises(Exception) as excinfo:
            async with Client(url, auth=BearerAuth(read_token)) as c:
                await c.call_tool(WRITE_TOOL, PALETTE)
        message = str(excinfo.value).lower()
        # Component auth hides rather than 403s: an out-of-scope tool is filtered
        # out of the caller's surface entirely, so the refusal surfaces as
        # "Unknown tool" rather than "insufficient scope". That is the stronger
        # outcome, and it is why "unknown tool" counts as an authorization refusal.
        assert any(
            phrase in message
            for phrase in (
                "unknown tool",
                "not found",
                "scope",
                "auth",
                "permit",
                "denied",
                "forbidden",
            )
        ), f"refused, but not recognisably on authorization grounds: {excinfo.value}"
