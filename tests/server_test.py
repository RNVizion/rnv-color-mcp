"""
Phase 2 test: connect an in-memory client to the FastMCP server and exercise the tools
end to end (registration -> schema -> call -> result), no network or deploy required.

Run from repo root:  python tests/server_test.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp import Client
from server import mcp

EXPECTED_TOOLS = {
    "mix_colors", "convert_color", "generate_harmony", "transform_text",
    "save_palette", "list_palettes", "get_palette",
}


def _text(result):
    """Pull the first text/content payload out of a CallToolResult."""
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None):
        return result.structured_content
    return result.content


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        print(f"tools registered ({len(names)}): {sorted(names)}")
        assert names == EXPECTED_TOOLS, f"tool set mismatch: {names ^ EXPECTED_TOOLS}"

        # a name-based mix, all the way through the server
        r = await client.call_tool("mix_colors", {"colors": ["red", "blue"], "mode": "rgb"})
        print("mix_colors(red, blue, rgb) ->", _text(r))

        # paint mode through the server (should darken)
        r = await client.call_tool(
            "mix_colors", {"colors": ["brand gold", "near-black"], "mode": "paint"}
        )
        print("mix_colors(brand gold, near-black, paint) ->", _text(r))

        # harmony off a brand name
        r = await client.call_tool(
            "generate_harmony", {"base": "brand gold", "scheme": "complementary"}
        )
        print("generate_harmony(brand gold, complementary) ->", _text(r))

        # text transform
        r = await client.call_tool(
            "transform_text", {"text": "the honest machine", "operation": "snake_case"}
        )
        print("transform_text(snake_case) ->", _text(r))

        # palette save -> get round-trip via the client
        await client.call_tool(
            "save_palette",
            {"name": "Spring line", "colors": ["#0a0a0f", "#d2bc93"], "notes": "launch"},
        )
        r = await client.call_tool("get_palette", {"name": "Spring line"})
        print("get_palette(Spring line) ->", _text(r))

    print("\nPhase 2 OK: client sees all 7 tools and gets correct results through FastMCP.")


if __name__ == "__main__":
    asyncio.run(main())
