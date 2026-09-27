"""
Phase 2 smoke: connect an in-memory client to the FastMCP server and exercise the tools
end to end (registration -> schema -> call -> result), no network or deploy required.

Run from repo root:  python tests/server_test.py

ISOLATED FROM PRODUCTION DATA, and the isolation is load-bearing. A Codespace carries an
HF_TOKEN secret; the palette store reads HF_TOKEN at construction, hydrates from the
production Dataset and pushes every save back over it. Before 2026-09-27 this script
inherited that token and would have written its "Spring line" test palette into the
live store. The environment is now set before `server` (and so `api`) is imported --
the same two lines tests/conftest.py uses: a throwaway store path, and no token.
RNV_AUTH is cleared too, because the in-memory transport cannot carry a bearer token
and this is an auth-off smoke.

The setup runs only under __main__. pytest's default glob matches *_test.py, so this
module is IMPORTED at collection (it defines no tests); mutating the environment at
import time would rebuild the server auth-off under the suite and break test_auth and
test_scopes. Imports that depend on the environment therefore live inside main().
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# A second, hand-kept copy of the contract (practices §3.2.1a): equality below fails
# when a tool is added or removed and this set is not updated on purpose.
EXPECTED_TOOLS = {
    "mix_colors", "convert_color", "place_lightness", "generate_harmony",
    "color_difference", "contrast_check", "transform_text",
    "save_palette", "list_palettes", "get_palette",
}


def _isolate_from_production() -> str:
    store = os.path.join(tempfile.mkdtemp(prefix="rnv-smoke-"), "palettes.json")
    os.environ["RNV_PALETTE_STORE"] = store
    os.environ.pop("HF_TOKEN", None)
    os.environ.pop("RNV_AUTH", None)
    return store


def _text(result):
    """Pull the first text/content payload out of a CallToolResult."""
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None):
        return result.structured_content
    return result.content


async def main() -> None:
    from fastmcp import Client
    from server import mcp
    import api

    assert not api._store.hf_token, "smoke run is holding an HF token; refusing to touch the Dataset"

    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        print(f"tools registered ({len(names)}): {sorted(names)}")
        assert names == EXPECTED_TOOLS, f"tool set mismatch: {names ^ EXPECTED_TOOLS}"

        # a name-based mix, all the way through the server
        r = await client.call_tool("mix_colors", {"colors": ["red", "yellow"], "mode": "rgb"})
        print("mix_colors(red, yellow, rgb) ->", _text(r))

        # paint mode through the server (should darken)
        r = await client.call_tool(
            "mix_colors", {"colors": ["brand gold", "near-black"], "mode": "paint"}
        )
        print("mix_colors(brand gold, near-black, paint) ->", _text(r))

        # placement: the register's blue pair, rebuilt from its mix
        r = await client.call_tool(
            "place_lightness", {"color": "#5c82a9", "lightness": [60.16, 44.17]}
        )
        hexes = [p["hex"] for p in _text(r)["placements"]]
        print("place_lightness(#5c82a9, [60.16, 44.17]) ->", hexes)
        assert hexes == ["#6f94bc", "#456c91"], hexes

        # harmony off a brand name
        r = await client.call_tool(
            "generate_harmony", {"base": "brand gold", "scheme": "complementary"}
        )
        print("generate_harmony(brand gold, complementary) ->", _text(r))

        # delta-e between two brand colors
        r = await client.call_tool(
            "color_difference", {"color1": "brand gold", "color2": "dark gold"}
        )
        print("color_difference(brand gold, dark gold) ->", _text(r))

        # contrast check: gold text on near-black
        r = await client.call_tool(
            "contrast_check", {"foreground": "brand gold", "background": "near-black"}
        )
        print("contrast_check(brand gold on near-black) ->", _text(r))

        # text transform
        r = await client.call_tool(
            "transform_text", {"text": "the honest machine", "operation": "snake_case"}
        )
        print("transform_text(snake_case) ->", _text(r))

        # palette save -> get round-trip via the client, into the throwaway store
        r = await client.call_tool(
            "save_palette",
            {"name": "Spring line", "colors": ["#0a0a0f", "brand gold"], "notes": "launch"},
        )
        saved = _text(r)
        print("save_palette(Spring line) ->", saved)
        r = await client.call_tool("get_palette", {"name": "Spring line"})
        print("get_palette(Spring line) ->", _text(r))
        r = await client.call_tool("list_palettes", {})
        print("list_palettes() ->", _text(r))

    print(f"\nOK: client sees all {len(EXPECTED_TOOLS)} tools and gets results through FastMCP.")


if __name__ == "__main__":
    store = _isolate_from_production()
    print(f"palette store for this run: {store} (no HF token)\n")
    asyncio.run(main())
