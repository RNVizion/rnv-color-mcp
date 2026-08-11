"""
RNVizion brand vocabulary — local mirror.
=========================================
NOT a source. The source is `engine/brand.py` in RNVizion/rnv-brand; this file
is a mirror of the one thing this server needs from it, carried locally so
`resolve_color` never depends on a network call it cannot guarantee.

Why a mirror and not a fetch: resolve_color is the hot path — every mix,
convert, harmony, difference, and contrast call routes through it. A fetch
there has to answer what happens when it fails, and every answer is bad. Fail
closed and the server refuses every color; fall back and you need this file
anyway; guess and you have broken the one rule the resolver exists to enforce.

Why a mirror and not an import: this Space deploys as its own container. There
is no cross-repo import path, and adding one would put a build-time network
dependency under a value that changes twice a year.

Sync discipline: values here are corrected when drift is detected against
rnv-brand, by a human, in a deliberate commit. Identifiers are local by design
— BRAND_GOLD here, GOLD upstream — because the check compares values, never
names. Nothing propagates automatically, and nothing should appear to.

Mirrored from rnv-brand@c4d479dbf16b95b21fea80016372a03a64f1c450, 2026-08-10.

Consumed by: engine/resolve.py, which imports RNV_BRAND and nothing else.

Vocabulary note: "near-black" resolves to CHARCOAL (#1a1a1a), not to the web
ground. The web ground is "web black" (#0a0a0f). Both readings of "near-black"
were in circulation; this contract keeps the older one, because a live resolver
is expensive to repoint and a document is cheap to reword.

Spelling note: resolve_color only lowercases the token -- no hyphen or
whitespace normalization -- so every alias below is a literal spelling that had
to be anticipated. "near-black" and "near black" are two separate keys; there is
no "light mode gold", so that spelling refuses today. Which aliases got a second
spelling was never decided, only accumulated. Parked in the RUNBOOK: normalize
- and _ to spaces before lookup, and shrink this table.
"""
from __future__ import annotations

from typing import Final

# ==================== The values this vocabulary maps to ====================
BRAND_GOLD: Final[str] = "#d2bc93"
"""Primary brand gold. The accent on black and dark surfaces."""

BRAND_GOLD_DARK: Final[str] = "#b19145"
"""Dark gold. The accent on light surfaces; also gold's shade on dark."""

BRAND_BLACK: Final[str] = "#1a1a1a"
"""Charcoal. The default 'black' when asked with no context."""

TRUE_BLACK: Final[str] = "#000000"
"""App window ground; text on gold, on either surface."""

WHITE: Final[str] = "#ffffff"
"""Light-surface cards and inputs; the neutral ramp's far anchor."""

WEB_BLACK: Final[str] = "#0a0a0f"
"""rnvizion.dev ground; social and OG base. Blue-tinted, deliberately."""

# ==================== Resolver vocabulary ====================
# RNV names beat CSS names on collision, so `gold` resolves to brand gold and
# `css:gold` forces the universal one. "white" and "black" shadow CSS names at
# identical values, so resolution is unchanged either way; they are here
# because the register names them.
RNV_BRAND: Final[dict[str, str]] = {
    "near-black": BRAND_BLACK,
    "near black": BRAND_BLACK,
    "brand black": BRAND_BLACK,
    "rnv black": BRAND_BLACK,
    "charcoal": BRAND_BLACK,
    "gold": BRAND_GOLD,
    "brand gold": BRAND_GOLD,
    "rnv gold": BRAND_GOLD,
    "dark gold": BRAND_GOLD_DARK,
    "gold dark": BRAND_GOLD_DARK,
    "light-mode gold": BRAND_GOLD_DARK,
    "black": TRUE_BLACK,
    "true black": TRUE_BLACK,
    "white": WHITE,
    "brand white": WHITE,
    "web black": WEB_BLACK,
}

__all__ = [
    "BRAND_GOLD",
    "BRAND_GOLD_DARK",
    "BRAND_BLACK",
    "TRUE_BLACK",
    "WHITE",
    "WEB_BLACK",
    "RNV_BRAND",
]
