---
title: RNV Color MCP
emoji: 🎨
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Color workflow MCP server
---

<!-- mcp-name: io.github.RNVizion/rnv-color-mcp -->

# RNV Color MCP

[![rnv-color-mcp MCP server](https://glama.ai/mcp/servers/RNVizion/rnv-color-mcp/badges/card.svg)](https://glama.ai/mcp/servers/RNVizion/rnv-color-mcp)

A remote [MCP](https://modelcontextprotocol.io) server for a complete color workflow:
mix, convert, harmonize, and remember palettes, called in plain language by Claude (or any
MCP client), and by anything else that speaks MCP.

## Why this exists

The color logic already lived in my [desktop suite](https://github.com/RNVizion): a mixer, a
palette manager, a picker. Instead of rebuilding it for every new project, I lifted the engine
out once and exposed it as a single server. A Claude conversation calls it today; a fashion
design app will call the same backend tomorrow. Build the engine once, let both consume it.

Underneath, it's a small thesis about working with LLMs: a model is great at deciding *what* you
want and terrible at exact arithmetic. So the model picks the tool and the intent, and the tool
owns the precise values. The server resolves or it refuses; it never guesses a color.

## What it does

| Tool | What it does |
|---|---|
| `mix_colors` | Blend up to 12 colors. Modes: `rgb`, `hsv`, `lab` (digital) and `paint` (Kubelka-Munk pigment physics), `ryb` (artist's wheel), `cmy` (subtractive). |
| `convert_color` | Convert between hex, rgb, hsv, hsl, lab. |
| `generate_harmony` | complementary, analogous, triadic, split-complementary, tetradic/square, monochromatic, compound. |
| `color_difference` | Perceptual difference (Delta-E, CIEDE2000 or CIE76) between two colors. |
| `contrast_check` | WCAG contrast ratio plus AA/AAA pass/fail for accessible text. |
| `transform_text` | 11 exact case transforms (UPPERCASE, camelCase, snake_case, …). |
| `save_palette` / `list_palettes` / `get_palette` | Name a palette, recall it later. Persists across restarts. |

Every color input accepts a **hex** (`#d2bc93`), a **CSS name** (`red`), an **RNV brand name**
(`brand gold`, `near-black`), or a **saved-palette reference** (`Spring line`, or `Spring line:2`
for its second swatch). Brand names win over CSS names on collision; `css:gold` forces the
universal one.

## Connect in 30 seconds

This is a hosted server, so there's nothing to install. In Claude: **Settings → Connectors →
Add custom connector**, then paste:

```
https://rnvizion-rnv-color-mcp.hf.space/mcp
```

Leave auth blank, add it, then toggle it on in a chat with the **+** menu.

## Try it

Once connected, just talk:

> "Save a palette named *Spring line*: near-black and brand gold."
> "Pull my Spring line palette and give me three complementary accents for outerwear."
> "Mix paint-red and paint-blue like real pigment."

The first call saves; the second composes `get_palette` → `generate_harmony`; the third runs the
Kubelka-Munk paint model, so the blend darkens the way mixed pigment actually does, not the way
averaged light does.

## Run it yourself

```bash
pip install -r requirements.txt
python server.py          # Streamable HTTP on $PORT (default 7860)
python tests/server_test.py   # exercises all 9 tools in-process
```

Set `HF_TOKEN` to write palettes through to a private Hugging Face Dataset for durable storage.

## Notes

- **One brand source of truth.** Brand colors live in [`engine/brand.py`](engine/brand.py); the
  resolver imports them, so a brand value is defined in exactly one place. See `BRAND_COLORS.md`.
- **Engine is dependency-free.** The color math, harmony, and text logic are pure standard
  library, lifted Qt-free from the desktop apps. Only the server layer needs `fastmcp`.
- **Honest by design.** An unknown color name is refused, not guessed.

## Stack

Python · [FastMCP](https://github.com/jlowin/fastmcp) (Streamable HTTP) · Hugging Face Spaces
(Docker) · `huggingface_hub` for durable palette storage.

---

Built by [Christian "RNVizion" Smith](https://rnvizion.dev).
