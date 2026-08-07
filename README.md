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
[![Mentioned in Awesome MCP Servers](https://awesome.re/mentioned-badge.svg)](https://github.com/punkpeye/awesome-mcp-servers)
[![tests](https://github.com/RNVizion/rnv-color-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/RNVizion/rnv-color-mcp/actions/workflows/tests.yml)

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

## Authentication

The server implements OAuth 2.1 resource-server authentication with enforced per-tool scopes; the
public endpoint runs with it disabled, so connecting by URL works with no setup.

When enabled (`RNV_AUTH=1` plus a key source), the server validates bearer tokens against issuer,
audience, expiry, and signature; serves [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728)
protected resource metadata at `/.well-known/oauth-protected-resource/mcp`; returns a
spec-compliant `WWW-Authenticate` challenge on 401; and enforces two scopes: `read` covers the
eight read-only tools, `write` covers `save_palette`, the only tool that mutates anything. A token
without the `write` scope does not see `save_palette` in its tool list at all; out-of-scope tools
are hidden rather than refused, so nothing leaks about what exists behind a scope you lack.

Enforcement is covered by the test suite, run in CI on every push (status badge at the top of
this file), spanning the token-validation matrix (missing, malformed, wrong issuer, wrong
audience, expired, valid) and end-to-end scope enforcement over real HTTP. The suite mints its
own keys and requires no credentials. The tests cover the auth layer; the color engine itself is
not under automated test.

Moving from the self-issued development key to a real identity provider is configuration, not
code: point `RNV_AUTH_JWKS_URI` at the provider's JWKS endpoint and set the issuer and audience
to match.

| Variable | Purpose |
|---|---|
| `RNV_AUTH` | The switch. `1` / `true` / `yes` / `on` enables auth; unset means off. |
| `RNV_AUTH_JWKS_URI` | A provider's JWKS endpoint. Use this or `RNV_AUTH_PUBLIC_KEY`. |
| `RNV_AUTH_PUBLIC_KEY` | A static PEM public key, for development against a self-issued keypair. |
| `RNV_AUTH_ISSUER` | Expected token issuer; also advertised as the authorization server. |
| `RNV_AUTH_AUDIENCE` | Expected token audience. Bound to the `/mcp` path. |
| `RNV_AUTH_BASE_URL` | Server base URL, without `/mcp`. |

With `RNV_AUTH` on and no key source set, the server refuses to start rather than coming up
unprotected.

## Run it yourself

```bash
pip install -r requirements.txt
python server.py                  # Streamable HTTP on $PORT (default 7860)

pip install -r requirements-dev.txt
python -m pytest                  # auth + scope tests
python tests/server_test.py       # smoke: exercises all 9 tools in-process
```

Set `HF_TOKEN` to write palettes through to a private Hugging Face Dataset for durable storage.

## Running a copy?

The code is MIT-licensed; you're free to rebuild, host, and modify it, and I'd rather you did than
didn't. What a licence can't carry is the environment.

Some capabilities depend on how a deployment is configured, not on the code alone:

- **Palette persistence** needs `HF_TOKEN` and a writable Dataset. Without it, saves land in
  process memory and vanish with the container.
- **Scoped authorization** needs `RNV_AUTH` and a configured issuer. Unset, the server runs open —
  which is correct for a public demo and wrong for anything else.
- **Anything that fetches** needs outbound network access.

A rebuild missing one of those usually doesn't fail loudly; it **returns success and drops the
result.** That is worse than an outage, because an outage tells you.

So: if you're running a copy and something behaves oddly, check the environment before you check
the code, and check against the canonical deployment before you file anything.

**Canonical endpoint:** `https://rnvizion-rnv-color-mcp.hf.space/mcp`
**Canonical source:** `https://github.com/RNVizion/rnv-color-mcp`

A copy served from another URL may be older, modified, or differently configured. That's fine and
allowed; it just isn't this.

The tools resolve or refuse; they don't guess. A copy can only keep that promise if the ground
under it was checked first.

## Notes

- **One brand source of truth.** Brand colors live in [`engine/brand.py`](engine/brand.py); the
  resolver imports them, so a brand value is defined in exactly one place. See `BRAND_COLORS.md`.
- **Engine is dependency-free.** The color math, harmony, and text logic are pure standard
  library, lifted Qt-free from the desktop apps. Only the server layer needs `fastmcp`.
- **Honest by design.** An unknown color name is refused, not guessed. An unverifiable token is
  refused, with a reason. Same principle at both layers.

## Stack

Python · [FastMCP](https://github.com/PrefectHQ/fastmcp) (Streamable HTTP) · Hugging Face Spaces
(Docker) · `huggingface_hub` for durable palette storage.

---

Built by [Christian "RNVizion" Smith](https://rnvizion.dev).
