"""
RNV Color MCP - API surface

The seven locked tools, shaped as plain functions. This is the seam: Phase 2 wraps each
of these with @mcp.tool and a description; nothing else about the engine changes.

Color engine : mix_colors, convert_color, generate_harmony
Text         : transform_text
Palette store: save_palette, list_palettes, get_palette
"""
from __future__ import annotations

import os
from typing import Any

from engine.color_math import ColorMath
from engine.color_harmony import generate_harmony as _harmony_by_name
from engine.text_transform import TextTransformer
from engine.palette_store import PaletteStore
from engine.resolve import resolve_color

# ---- mix mode -> ColorMath method ---------------------------------------
_MIX_MODES = {
    "rgb": ColorMath.weighted_rgb_mix,     # additive average (blend like light)
    "hsv": ColorMath.weighted_hsv_mix,     # circular-hue average
    "lab": ColorMath.lab_perceptual_mix,   # perceptually uniform (default)
    "paint": ColorMath.kubelka_munk_mix,   # pigment physics (blend like real paint)
    "ryb": ColorMath.weighted_ryb_mix,     # artist's color wheel
    "cmy": ColorMath.subtractive_cmy_mix,  # subtractive (like printer inks)
}

# A single shared store instance; path is configurable for deployment (persistent
# storage on the Space). Defaults to a local file for dev / Codespace.
_store = PaletteStore(os.environ.get("RNV_PALETTE_STORE", "palettes.json"))


# ---- color engine -------------------------------------------------------
def mix_colors(
    colors: list[str],
    weights: list[int] | None = None,
    mode: str = "lab",
) -> dict[str, Any]:
    """Blend up to 12 colors. weights default to equal; mode is one of
    rgb | hsv | lab | paint | ryb | cmy. Returns the mixed color."""
    if not colors:
        raise ValueError("Provide at least one color to mix.")
    if mode not in _MIX_MODES:
        raise ValueError(f"Unknown mode '{mode}'. Choose from {sorted(_MIX_MODES)}.")
    if weights is None:
        weights = [1] * len(colors)
    if len(weights) != len(colors):
        raise ValueError("weights must match the number of colors.")

    rgb_list = [ColorMath.hex_to_rgb(resolve_color(c, _store)) for c in colors]
    colors_weights = list(zip(rgb_list, weights))
    mixed = _MIX_MODES[mode](colors_weights)
    if mixed is None:
        raise ValueError("Mixing produced no result (check colors and weights).")
    return {"hex": ColorMath.rgb_to_hex(mixed), "rgb": list(mixed), "mode": mode}


def convert_color(color: str, to: str | None = None) -> dict[str, Any]:
    """Convert a hex color between formats. With `to`, returns just that format;
    otherwise returns all of hex/rgb/hsv/hsl/lab."""
    rgb = ColorMath.hex_to_rgb(resolve_color(color, _store))
    all_formats = {
        "hex": ColorMath.rgb_to_hex(rgb),
        "rgb": list(rgb),
        "hsv": list(ColorMath.rgb_to_hsv(rgb)),
        "hsl": list(ColorMath.rgb_to_hsl(rgb)),
        "lab": list(ColorMath.rgb_to_lab(rgb)),
    }
    if to:
        key = to.lower()
        if key not in all_formats:
            raise ValueError(f"Unknown format '{to}'. Choose from {sorted(all_formats)}.")
        return {key: all_formats[key]}
    return all_formats


def generate_harmony(base: str, scheme: str) -> list[str]:
    """Generate a color harmony from a base hex color. scheme is one of
    complementary | analogous | triadic | split-complementary |
    tetradic/square | monochromatic | compound."""
    rgb = ColorMath.hex_to_rgb(resolve_color(base, _store))
    result = _harmony_by_name(rgb, scheme)
    return [ColorMath.rgb_to_hex(c) for c in result]


def color_difference(color1: str, color2: str, method: str = "ciede2000") -> dict[str, Any]:
    """Perceptual difference (Delta-E) between two colors.
    method: "ciede2000" (default, modern standard) or "cie76". A value near 1.0 is the
    threshold a human eye can just notice; larger means more different."""
    rgb1 = ColorMath.hex_to_rgb(resolve_color(color1, _store))
    rgb2 = ColorMath.hex_to_rgb(resolve_color(color2, _store))
    de = ColorMath.delta_e(rgb1, rgb2, method=method)
    if de < 1:
        note = "not perceptible by human eyes"
    elif de < 2:
        note = "perceptible on close inspection"
    elif de < 10:
        note = "perceptible at a glance"
    elif de < 50:
        note = "clearly different"
    else:
        note = "near-opposite colors"
    return {
        "delta_e": round(de, 4),
        "method": method,
        "interpretation": note,
        "color1": ColorMath.rgb_to_hex(rgb1),
        "color2": ColorMath.rgb_to_hex(rgb2),
    }


def contrast_check(foreground: str, background: str) -> dict[str, Any]:
    """WCAG contrast ratio between a foreground and background color, with pass/fail
    for each accessibility level. Ratio runs 1.0 (none) to 21.0 (black on white)."""
    fg = ColorMath.hex_to_rgb(resolve_color(foreground, _store))
    bg = ColorMath.hex_to_rgb(resolve_color(background, _store))
    ratio = ColorMath.contrast_ratio(fg, bg)
    return {
        "ratio": round(ratio, 2),
        "display": f"{round(ratio, 2)}:1",
        "foreground": ColorMath.rgb_to_hex(fg),
        "background": ColorMath.rgb_to_hex(bg),
        "wcag": {
            "AA_normal_text": ratio >= 4.5,
            "AA_large_text": ratio >= 3.0,
            "AAA_normal_text": ratio >= 7.0,
            "AAA_large_text": ratio >= 4.5,
            "AA_ui_components": ratio >= 3.0,
        },
    }


# ---- text ---------------------------------------------------------------
def transform_text(text: str, operation: str) -> dict[str, str]:
    """Apply an exact text transformation (case conversions, etc.)."""
    return {"result": TextTransformer.transform_text(text, operation)}


# ---- palette store ------------------------------------------------------
def save_palette(name: str, colors: list[str], notes: str = "") -> dict[str, Any]:
    """Save (or update) a named palette for later reuse."""
    return _store.save_palette(name, colors, notes)


def list_palettes() -> list[dict[str, Any]]:
    """List every saved palette as {name, colors}."""
    return _store.list_palettes()


def get_palette(name: str) -> dict[str, Any] | None:
    """Retrieve one saved palette by name, or None if it doesn't exist."""
    return _store.get_palette(name)


__all__ = [
    "mix_colors", "convert_color", "generate_harmony", "transform_text",
    "save_palette", "list_palettes", "get_palette",
]
