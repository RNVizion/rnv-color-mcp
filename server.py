"""
RNV Color MCP - server

Thin FastMCP wrapper over api.py. The tools are registered with descriptions written
for the model: the description is what an LLM reads to decide whether and how to call a tool,
so each one is a capability statement, not a label.

Run locally / in a Codespace:
    pip install -r requirements.txt
    python server.py                      # Streamable HTTP on PORT (default 7860)

Transport is Streamable HTTP ("http"); connect by URL. Durable palette storage is via HF
Dataset write-through: set HF_TOKEN (an HF write token) and optionally RNV_PALETTE_DATASET,
and every save is pushed to a private Dataset that the store re-hydrates on startup, so
palettes survive rebuilds. (RNV_PALETTE_STORE only sets the local working-copy path, which is
ephemeral on a free Space; it is not the durability mechanism.)
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
        "digital blends (lab is perceptual and the default, best for on-screen color); "
        "paint mixes pigments via Kubelka-Munk physics (colors darken like real paint, "
        "use it for physical-media matching); ryb is the artist's color wheel; cmy is "
        "subtractive like printer inks. Returns hex and rgb. "
        "Read-only and deterministic: it computes a result and stores nothing, so it is "
        "safe to call repeatedly with no side effects. "
        "Use to combine multiple colors into a single blend; to convert one color between "
        "formats use convert_color, and to measure how far apart two colors are use "
        "color_difference."
    ),
)

mcp.tool(
    api.convert_color,
    description=(
        "Convert a color between formats. Input accepts a hex, CSS name, RNV brand name, "
        "or saved-palette reference. With `to` set to one of hex/rgb/hsv/hsl/lab, returns "
        "just that format; otherwise returns all of them. "
        "Read-only and deterministic, with no side effects. "
        "Use for format conversion of a single color; to blend several colors into one use "
        "mix_colors, and to compare two colors use color_difference."
    ),
)

mcp.tool(
    api.generate_harmony,
    description=(
        "Generate a color harmony from a base color. base accepts a hex, CSS name, RNV "
        "brand name, or saved-palette reference (e.g. 'Spring line:2'). scheme is one of: "
        "complementary, analogous, triadic, split-complementary, tetradic (a.k.a. square), "
        "monochromatic, compound. Returns a list of hex colors. "
        "Read-only and deterministic: it derives the colors from the base and stores "
        "nothing, so it has no side effects and is safe to call repeatedly. "
        "Use to expand one base color into a related set; to blend existing colors into a "
        "single color use mix_colors, and to persist a set you like use save_palette."
    ),
)

mcp.tool(
    api.color_difference,
    description=(
        "Perceptual difference (Delta-E) between two colors. color1 and color2 accept a hex, "
        "CSS name, RNV brand name, or saved-palette reference. method is 'ciede2000' (default, "
        "modern standard) or 'cie76'. A value near 1.0 is the threshold the eye can just notice; "
        "larger means more different. Returns the value and a plain-language interpretation. "
        "Read-only and deterministic, with no side effects. "
        "Use ciede2000 for accuracy and pick cie76 only to match a legacy system; to test "
        "whether text is legible on a background (not raw difference) use contrast_check instead."
    ),
)

mcp.tool(
    api.contrast_check,
    description=(
        "WCAG contrast ratio between a foreground and background color, for accessibility. "
        "Both accept a hex, CSS name, RNV brand name, or saved-palette reference. Returns the "
        "ratio (1.0-21.0) plus pass/fail for AA and AAA at normal and large text sizes and for "
        "UI components. "
        "Read-only and deterministic, with no side effects. "
        "Use this for legibility and accessibility checks; to measure raw perceptual "
        "difference between two colors rather than readability use color_difference instead."
    ),
)

# ---- text ---------------------------------------------------------------
mcp.tool(
    api.transform_text,
    description=(
        "Apply an exact, deterministic text transformation. operation is one of: "
        "UPPERCASE, lowercase, 'Title Case', 'Sentence case', camelCase, PascalCase, "
        "snake_case, CONSTANT_CASE, kebab-case, dot.case, 'iNVERTED cASE'. "
        "Read-only and deterministic: it returns the transformed string and changes nothing, "
        "safe to call repeatedly. "
        "Use whenever exact, reproducible case formatting matters rather than rewriting the "
        "text by hand or guessing the casing."
    ),
)

# ---- palette memory -----------------------------------------------------
mcp.tool(
    api.save_palette,
    description=(
        "Persist a named color palette for later retrieval with get_palette or list_palettes. "
        "colors is a list of hex values; optional notes are stored as the palette's description. "
        "Author is recorded as RNVizion. "
        "This WRITES to the palette store and is the only tool here that does. Reusing an "
        "existing name overwrites that palette: save and update are the same call (an upsert), "
        "there is no separate update operation. "
        "Returns a `durable` flag: true if the palette reached durable storage (the HF Dataset) "
        "and will survive a restart, false if it saved to the local working copy only (which is "
        "lost on rebuild, e.g. when the Space HF_TOKEN is missing or lacks write scope). "
        "Use when the user wants to keep a set of colors under a name for reuse across sessions, "
        "such as a brand or launch palette; to read a palette back use get_palette, and to see "
        "what already exists use list_palettes. The saved name can then be passed to mix_colors, "
        "convert_color, and generate_harmony as a palette reference."
    ),
)

mcp.tool(
    api.list_palettes,
    description=(
        "List every saved palette as name + colors. "
        "Read-only; no side effects. "
        "Use to discover what palettes exist or to find a name before calling get_palette; to "
        "fetch one palette's full detail use get_palette, and to create or overwrite one use "
        "save_palette."
    ),
)

mcp.tool(
    api.get_palette,
    description=(
        "Retrieve one saved palette by name, returning its colors and metadata. Returns "
        "null if no palette by that name exists. "
        "Read-only; no side effects. "
        "Use when you already know the palette name; to list available names first use "
        "list_palettes, and to create or update a palette use save_palette."
    ),
)


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 7860)),
    )
