"""
RNV Color MCP - server

Thin FastMCP wrapper over api.py. The tools are registered with descriptions written
for the model: the description is what an LLM reads to decide whether and how to call a tool,
so each one is a capability statement, not a label.

Run locally / in a Codespace:
    pip install -r requirements.txt
    python server.py                      # Streamable HTTP on PORT (default 7860)

Transport is Streamable HTTP ("http"); connect by URL. Set RNV_PALETTE_STORE to a persistent
path (e.g. /data/palettes.json on a Space with persistent storage) so saved palettes survive
restarts.
"""
from __future__ import annotations

import os

from fastmcp import FastMCP
from starlette.responses import JSONResponse

import api

mcp = FastMCP(
    name="rnv-color",
    instructions=(
        "Color workflow for RNVizion: mix colors (digital and physical/paint models), "
        "convert formats, generate harmonies, transform text case, and remember named "
        "palettes. Color inputs accept hex, CSS names, RNV brand names (brand gold, "
        "near-black), or saved-palette references."
    ),
)


# ---- glama ownership claim ----------------------------------------------
# Served at https://rnvizion-rnv-color-mcp.hf.space/.well-known/glama.json so Glama can
# verify ownership of this connector. The email must match the Glama account email.
@mcp.custom_route("/.well-known/glama.json", methods=["GET"])
async def glama_claim(request):
    return JSONResponse(
        {
            "$schema": "https://glama.ai/mcp/schemas/connector.json",
            "maintainers": [{"email": "vizionaryfx@yahoo.com"}],
        }
    )


# ---- color engine -------------------------------------------------------
mcp.tool(
    api.mix_colors,
    description=(
        "Blend up to 12 colors into one. Each color may be a hex (#d2bc93), a CSS name "
        "(red), an RNV brand name (brand gold, near-black), or a saved-palette reference "
        "(Spring line, or 'Spring line:2' for its 2nd swatch). Optional integer weights "
        "bias the blend (defaults to equal). mode selects the model: rgb/hsv/lab are "
        "digital blends (lab is perceptual and the default); paint mixes pigments via "
        "Kubelka-Munk physics (colors darken like real paint); ryb is the artist's color "
        "wheel; cmy is subtractive like printer inks. Returns hex and rgb."
    ),
)

mcp.tool(
    api.convert_color,
    description=(
        "Convert a color between formats. Input accepts a hex, CSS name, RNV brand name, "
        "or saved-palette reference. With `to` set to one of hex/rgb/hsv/hsl/lab, returns "
        "just that format; otherwise returns all of them."
    ),
)

mcp.tool(
    api.generate_harmony,
    description=(
        "Generate a color harmony from a base color. base accepts a hex, CSS name, RNV "
        "brand name, or saved-palette reference (e.g. 'Spring line:2'). scheme is one of: "
        "complementary, analogous, triadic, split-complementary, tetradic (a.k.a. square), "
        "monochromatic, compound. Returns a list of hex colors."
    ),
)

mcp.tool(
    api.color_difference,
    description=(
        "Perceptual difference (Delta-E) between two colors. color1 and color2 accept a hex, "
        "CSS name, RNV brand name, or saved-palette reference. method is 'ciede2000' (default, "
        "modern standard) or 'cie76'. A value near 1.0 is the threshold the eye can just notice; "
        "larger means more different. Returns the value and a plain-language interpretation."
    ),
)

mcp.tool(
    api.contrast_check,
    description=(
        "WCAG contrast ratio between a foreground and background color, for accessibility. "
        "Both accept a hex, CSS name, RNV brand name, or saved-palette reference. Returns the "
        "ratio (1.0-21.0) plus pass/fail for AA and AAA at normal and large text sizes and for "
        "UI components. Use this to check if text will be readable on a background."
    ),
)

# ---- text ---------------------------------------------------------------
mcp.tool(
    api.transform_text,
    description=(
        "Apply an exact, deterministic text transformation. operation is one of: "
        "UPPERCASE, lowercase, 'Title Case', 'Sentence case', camelCase, PascalCase, "
        "snake_case, CONSTANT_CASE, kebab-case, dot.case, 'iNVERTED cASE'. Use this rather "
        "than converting case by hand."
    ),
)

# ---- palette memory -----------------------------------------------------
mcp.tool(
    api.save_palette,
    description=(
        "Persist a named color palette for later retrieval with get_palette or list_palettes. "
        "Use when the user wants to keep a set of colors under a name for reuse across sessions, "
        "such as a brand or launch palette. colors is a list of hex values; reusing an existing "
        "name overwrites that palette (upsert). Optional notes are stored as the palette's "
        "description. The saved name can then be referenced by other tools (mix_colors, "
        "convert_color, generate_harmony) as a palette reference. Author is recorded as RNVizion."
    ),
)

mcp.tool(
    api.list_palettes,
    description="List every saved palette as name + colors.",
)

mcp.tool(
    api.get_palette,
    description=(
        "Retrieve one saved palette by name, returning its colors and metadata. Returns "
        "null if no palette by that name exists."
    ),
)


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7860)),
    )
