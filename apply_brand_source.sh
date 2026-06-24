#!/bin/bash
# apply_brand_source.sh  -  install the brand color source of truth + rewire the resolver
# Run from the repo root in your Codespace:
#     bash apply_brand_source.sh          (uses HF_TOKEN secret)
#     bash apply_brand_source.sh <token>  (or pass it)
set -e

TOKEN="${HF_TOKEN:-$1}"
if [ -z "$TOKEN" ]; then
  echo "Need a Hugging Face WRITE token: bash apply_brand_source.sh <token>"
  exit 1
fi

echo "1/4  Writing engine/brand.py ..."
cat > engine/brand.py << 'BRANDEOF'
"""
RNVizion - Brand Color Source of Truth
=======================================
The single place RNV brand colors are defined. Other code imports from here
instead of hardcoding hexes, so brand values can never drift between surfaces.

Three canonical brand colors answer "what is the brand color?" with no context.
Everything else is a *context variant* with a named role (desktop app vs website),
because the brand deliberately runs two darks: a neutral charcoal for app UI and a
blue-tinted near-black ramp for rnvizion.dev. Both are intentional; do not collapse them.

Consumed by: the MCP color resolver (engine/resolve.py imports RNV_BRAND).
Reference doc: BRAND_COLORS.md.
"""
from __future__ import annotations

from typing import Final

# ==================== Canonical brand colors ====================
BRAND_GOLD: Final[str] = "#d2bc93"
"""Primary brand gold. Hover accents, highlights, links, the dot."""

BRAND_GOLD_DARK: Final[str] = "#b19145"
"""Darker gold. Light-mode elements, borders, pressed states."""

BRAND_BLACK: Final[str] = "#1a1a1a"
"""Canonical brand black: charcoal. The default 'black' when asked with no context."""

BRAND_GOLD_RGB: Final[tuple[int, int, int]] = (210, 188, 147)
BRAND_GOLD_DARK_RGB: Final[tuple[int, int, int]] = (177, 145, 69)
BRAND_BLACK_RGB: Final[tuple[int, int, int]] = (26, 26, 26)

# ==================== Context variant: desktop / app UI ====================
# Neutral dark system used by the PyQt6 toolkit.
APP: Final[dict[str, str]] = {
    "window": "#000000",        # true-black window background
    "panel": BRAND_BLACK,       # raised surface (the charcoal)
    "card": "#2a2a2a",
    "border": "#333333",
    "text": "#e0e0e0",
    "text_dim": "#aaaaaa",
    "accent": BRAND_GOLD,
    "accent_light_mode": BRAND_GOLD_DARK,
    "accent_text": "#000000",   # black text on a gold fill
}

# ==================== Context variant: website (rnvizion.dev) ====================
# Blue-tinted near-black ramp. Deliberate depth; do NOT flatten to charcoal.
WEB: Final[dict[str, str]] = {
    "bg": "#0a0a0f",            # base (near-black, blue cast)
    "bg_2": "#11111a",
    "bg_3": "#1a1a26",
    "border": "#25253a",
    "border_soft": "#1e1e2e",
    "text": "#e8e8f0",
    "text_dim": "#9a9ab0",
    "text_faint": "#5a5a72",
    "accent": BRAND_GOLD,
    "accent_violet": "#b794ff",  # secondary, homepage only, used sparingly
    "accent_warm": "#ffd166",    # secondary, homepage only, used sparingly
}

# ==================== Status colors (app) ====================
STATUS: Final[dict[str, str]] = {
    "success": "#4caf50",
    "warning": "#ffc107",
    "error": "#f44336",
}

# ==================== Resolver vocabulary (name -> hex) ====================
# The MCP color resolver imports this directly. Add a brand color here once and
# every surface that reads this module gets it.
RNV_BRAND: Final[dict[str, str]] = {
    "near-black": BRAND_BLACK,
    "near black": BRAND_BLACK,
    "brand black": BRAND_BLACK,
    "rnv black": BRAND_BLACK,
    "gold": BRAND_GOLD,
    "brand gold": BRAND_GOLD,
    "rnv gold": BRAND_GOLD,
    "dark gold": BRAND_GOLD_DARK,
    "gold dark": BRAND_GOLD_DARK,
    "light-mode gold": BRAND_GOLD_DARK,
}

__all__ = [
    "BRAND_GOLD", "BRAND_GOLD_DARK", "BRAND_BLACK",
    "BRAND_GOLD_RGB", "BRAND_GOLD_DARK_RGB", "BRAND_BLACK_RGB",
    "APP", "WEB", "STATUS", "RNV_BRAND",
]
BRANDEOF

echo "2/4  Writing BRAND_COLORS.md ..."
cat > BRAND_COLORS.md << 'BRANDMDEOF'
# RNVizion Brand Colors

The single source of truth for RNV brand color. Machine source: `engine/brand.py`
(import from there; never hardcode). This doc is the human-readable explanation.

Last locked: 2026-06-24

---

## Canonical brand colors

The answer when someone asks for "the brand color" with no other context.

| Role | Hex | RGB |
|---|---|---|
| Brand gold (primary) | `#d2bc93` | 210, 188, 147 |
| Dark gold | `#b19145` | 177, 145, 69 |
| Brand black (charcoal) | `#1a1a1a` | 26, 26, 26 |

Gold is one value everywhere. Black is charcoal `#1a1a1a` by default.

---

## The two-dark rule

The brand deliberately runs **two** darks, by context. This is intentional, not drift.

- **App / desktop UI** uses a neutral dark: true-black window with charcoal panels.
- **Website (rnvizion.dev)** uses a blue-tinted near-black *ramp* for depth. Flattening it to charcoal would kill the layering, so the site keeps its own base. Do not "fix" it to `#1a1a1a`.

What stays constant across both: the gold.

---

## Desktop / app palette

| Role | Hex |
|---|---|
| Window background | `#000000` |
| Panel (raised surface) | `#1a1a1a` |
| Card | `#2a2a2a` |
| Border | `#333333` |
| Text | `#e0e0e0` |
| Text dim | `#aaaaaa` |
| Accent | `#d2bc93` |
| Accent (light mode) | `#b19145` |
| Text on gold | `#000000` |

## Website palette (rnvizion.dev)

| Role | Hex |
|---|---|
| Base background | `#0a0a0f` |
| Background 2 | `#11111a` |
| Background 3 | `#1a1a26` |
| Border | `#25253a` |
| Border soft | `#1e1e2e` |
| Text | `#e8e8f0` |
| Text dim | `#9a9ab0` |
| Text faint | `#5a5a72` |
| Accent | `#d2bc93` |
| Accent violet (secondary, sparing) | `#b794ff` |
| Accent warm (secondary, sparing) | `#ffd166` |

## Status colors (app)

| Role | Hex |
|---|---|
| Success | `#4caf50` |
| Warning | `#ffc107` |
| Error | `#f44336` |

---

## Resolver vocabulary (MCP)

What the color server resolves brand names to in chat. Defined once in `brand.py`
as `RNV_BRAND`; the resolver imports it. RNV names win over CSS names on collision
(so `gold` = brand gold, not CSS gold); use `css:gold` to force the universal one.

| You say | Resolves to |
|---|---|
| near-black, brand black, rnv black | `#1a1a1a` |
| gold, brand gold, rnv gold | `#d2bc93` |
| dark gold, gold dark, light-mode gold | `#b19145` |

To teach the server a new brand color: add it to `RNV_BRAND` in `engine/brand.py`,
push, done. Every consumer updates from the one edit.

---

## Typography (reference)

Verified from rnvizion.dev:

- Display: Bricolage Grotesque
- Serif (emphasis / italics): Instrument Serif
- Mono (wordmark, labels, footer): JetBrains Mono
- Body: Inter / system stack

Social / OG-card typography is tracked separately; add it here when you want this doc
to cover those surfaces too.
BRANDMDEOF

echo "3/4  Rewiring engine/resolve.py to import from brand.py ..."
python3 << 'PYEOF'
import re, pathlib
r = pathlib.Path("engine/resolve.py")
t = r.read_text()
if "from engine.brand import RNV_BRAND" not in t:
    t = t.replace("import re\n", "import re\n\nfrom engine.brand import RNV_BRAND\n", 1)
t = re.sub(
    r"# --- RNV brand vocabulary.*?\nRNV_BRAND: dict\[str, str\] = \{.*?\n\}\n\n",
    "# RNV brand vocabulary now lives in engine/brand.py (single source of truth).\n\n",
    t, flags=re.DOTALL,
)
r.write_text(t)
s = pathlib.Path("tests/smoke_test.py")
if s.exists():
    st = s.read_text()
    st = st.replace('BRAND_NEAR_BLACK = "#0a0a0f"', 'BRAND_NEAR_BLACK = "#1a1a1a"')
    st = st.replace("should be #0a0a0f", "should be #1a1a1a")
    s.write_text(st)
print("   resolver rewired; brand values now sourced from engine/brand.py")
PYEOF

echo "4/4  Commit + push to the Space ..."
BASE=$(git remote get-url space | sed 's|https://[^@]*@|https://|')
USER=$(echo "$BASE" | cut -d/ -f5)
git add -A
git commit -m "Brand color source of truth: engine/brand.py + BRAND_COLORS.md; resolver imports RNV_BRAND" || true
git push "$(echo "$BASE" | sed "s|https://|https://${USER}:${TOKEN}@|")" HEAD:main --force

echo ""
echo "Done. After rebuild, the resolver reads brand colors from engine/brand.py."
echo "Verify in chat: 'convert near-black to hex' -> #1a1a1a ; 'dark gold' -> #b19145"
