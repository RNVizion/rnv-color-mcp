# rnv-color-mcp

A remote MCP server exposing the RNV color workflow: compute color, remember palettes,
transform text. The logic is lifted, Qt-free, from the RNV desktop suite
([color-mixer](https://github.com/RNVizion/rnv-color-mixer),
[palette-manager](https://github.com/RNVizion/rnv-color-palette-manager),
[text-transformer](https://github.com/RNVizion/rnv-text-transformer)). The GUIs stay GUIs;
this exposes the engine that was always behind them, so an LLM (and, later, the fashion
design app) can call it directly.

## Status

Phase 1 complete: engine extracted, palette store built, all seven tools verified Qt-free.
Phase 2 (the FastMCP server) is next. See `RNV_MCP_Color_Server_RUNBOOK.md`.

## Tools

Every color input accepts a hex, a CSS name (`red`), an RNV brand name (`brand gold`,
`near-black`), or a saved-palette reference (`Spring line`, `Spring line:2`).

**Color** — `mix_colors` (modes: rgb, hsv, lab, paint, ryb, cmy), `convert_color`,
`generate_harmony` (complementary, analogous, triadic, split-complementary, tetradic/square,
monochromatic, compound)
**Text** — `transform_text` (11 case operations)
**Palette memory** — `save_palette`, `list_palettes`, `get_palette`

## Layout

```
engine/            Qt-free logic (verbatim lift + new store)
  color_math.py        mix + convert  (from palette-manager: modern Py 3.13 copy)
  color_harmony.py     harmony engine (from color-mixer: the complete dispatcher)
  text_transform.py    case operations (from text-transformer)
  palette_metadata.py  palette schema (from palette-manager)
  palette_store.py     NEW: single-file JSON store, app-compatible schema
  resolve.py           NEW: color name resolution (RNV brand + palettes + CSS names)
api.py             the 7 tools as plain functions (the seam the server decorates)
server.py          FastMCP server: registers the 7 tools, Streamable HTTP
tests/smoke_test.py   proves the engine + store run standalone
```

## Run the smoke test

```bash
python tests/smoke_test.py
```

Engine, store, and resolver are standard-library only; the server needs `fastmcp`.

## Run the server

```bash
pip install -r requirements.txt
python server.py   # Streamable HTTP on PORT (default 7860)
```

Set `RNV_PALETTE_STORE` to a persistent path (e.g. `/data/palettes.json` on a Space) so saved palettes survive restarts.
