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
