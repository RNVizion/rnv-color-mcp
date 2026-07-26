"""
Per-tool scope enforcement for rnv-color-mcp.

The twelve tests in test_auth.py prove the server refuses a token it cannot
verify. These prove the harder thing: that a token it *does* verify is still
refused on a tool its scopes do not cover.

Driven through the in-memory Client, which is where component-level auth checks
run: transport-level rejection (no token, bad token) is test_auth.py's job, and
this file is about differentiating between two authenticated callers.

test_read_token_can_still_read is the positive control. If it fails, the harness
is wrong, not the server: it means the token is not reaching the auth context at
all, and every other assertion here is passing or failing for the wrong reason.
Read that one first.
"""
from __future__ import annotations

import pytest
from fastmcp import Client

try:
    from fastmcp.client.auth import BearerAuth
except ImportError:  # pragma: no cover - import path fallback
    from fastmcp.client.auth.bearer import BearerAuth

import server

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

PALETTE = {
    "name": "scope-test",
    "colors": ["#0a0a0f", "#d2bc93"],
}


@pytest.fixture
def read_client(make_token):
    return Client(server.mcp, auth=BearerAuth(make_token(scopes=["read"])))


@pytest.fixture
def write_client(make_token):
    return Client(server.mcp, auth=BearerAuth(make_token(scopes=["read", "write"])))


class TestPositiveControl:
    """If this class fails, stop: the token is not reaching the auth context."""

    async def test_read_token_can_still_read(self, read_client):
        async with read_client as c:
            result = await c.call_tool("convert_color", {"color": "#d2bc93"})
        assert result is not None

    async def test_write_token_can_write(self, write_client):
        async with write_client as c:
            result = await c.call_tool(WRITE_TOOL, PALETTE)
        assert result is not None


class TestVisibility:
    """Component auth filters the tool list, not just the call."""

    async def test_read_token_does_not_see_the_write_tool(self, read_client):
        async with read_client as c:
            names = {t.name for t in await c.list_tools()}
        assert WRITE_TOOL not in names

    async def test_read_token_sees_every_read_tool(self, read_client):
        async with read_client as c:
            names = {t.name for t in await c.list_tools()}
        assert READ_TOOLS <= names

    async def test_write_token_sees_all_nine(self, write_client):
        async with write_client as c:
            names = {t.name for t in await c.list_tools()}
        assert len(names) == 9
        assert WRITE_TOOL in names


class TestEnforcement:
    """The one that matters: a verified token, refused on scope."""

    async def test_read_token_is_refused_on_the_write_tool(self, read_client):
        with pytest.raises(Exception) as excinfo:
            async with read_client as c:
                await c.call_tool(WRITE_TOOL, PALETTE)
        # the refusal must be about authorization, not a coincidental failure
        message = str(excinfo.value).lower()
        assert any(
            word in message
            for word in ("scope", "auth", "permit", "denied", "forbidden", "not found")
        ), f"refused, but not recognisably on authorization grounds: {excinfo.value}"