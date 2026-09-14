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
from typing import Annotated
from pydantic import BaseModel, Field

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


def place_lightness(color: str, lightness: list[float]) -> dict[str, Any]:
    """Hold a colour's hue and chroma, set its lightness -- the register's own
    construction rule for a text pair, made executable.

    RNV builds a pair as ONE HUE AT TWO LIGHTNESSES: take a colour, keep `a`
    and `b` exactly, set `L*` to each rung. BRAND_BLUE and BRAND_DARK_BLUE were
    built this way from a single mix, as were the status text pairs. Until now
    the step was done by hand in a scratch script, which is why a published
    derivation could say "placed in LAB" with no tool behind the sentence.

    Returns what was ASKED FOR and what was ACHIEVED, per placement. Eight-bit
    hex cannot store `a` and `b` to the precision LAB expresses them, so two
    placements of one hue come back a few hundredths apart on both axes no
    matter how exactly the input held them. That is the storage format, not the
    operation -- and a tool that hid it would be handing back a value slightly
    different from the one requested while implying they were the same.

    Refuses rather than clamps. Not every (L*, a, b) exists in sRGB; a
    lightness too far from a chromatic colour's range has no representation,
    and the honest answer is the refusal, not the nearest colour that does fit.
    """
    if not lightness:
        raise ValueError("place_lightness needs at least one lightness value.")

    rgb = ColorMath.hex_to_rgb(resolve_color(color, _store))
    src_L, src_a, src_b = ColorMath.rgb_to_lab(rgb)

    placements: list[dict[str, Any]] = []
    for target in lightness:
        if not 0.0 <= target <= 100.0:
            raise ValueError(
                f"Lightness {target} is outside the L* range 0-100."
            )
        placed = ColorMath.lab_to_rgb_exact((target, src_a, src_b))
        if placed is None:
            raise ValueError(
                f"L* {target} has no sRGB representation while holding "
                f"a={src_a:.4f} b={src_b:.4f} (from {ColorMath.rgb_to_hex(rgb)}). "
                f"Pick a lightness nearer the source's, or accept a chroma change."
            )
        got_L, got_a, got_b = ColorMath.rgb_to_lab(placed)
        placements.append({
            "lightness": target,
            "hex": ColorMath.rgb_to_hex(placed),
            "rgb": list(placed),
            "achieved": {"L": got_L, "a": got_a, "b": got_b},
            "quantization_error": {
                "L": got_L - target,
                "a": got_a - src_a,
                "b": got_b - src_b,
            },
        })

    return {
        "source": {
            "hex": ColorMath.rgb_to_hex(rgb),
            "lab": {"L": src_L, "a": src_a, "b": src_b},
        },
        "placements": placements,
    }


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
        # UNROUNDED, for the reason contrast_check states twenty lines down:
        # rounding moves a number toward whichever side is nearer, which is
        # generous for a CEILING check ("within N of") and can pass a value
        # that should fail. Every consumer in this ecosystem currently asks
        # delta-E as a FLOOR (minimum separation), where round() could only
        # ever be conservative -- which is why `round(de, 4)` sat here
        # harmlessly and why the first ceiling consumer would have inherited
        # the error silently. The caller is entitled to the real number; the
        # short form is a separate field, never the value itself.
        "delta_e": de,
        "display": _truncate(de, 4),
        "method": method,
        "interpretation": note,
        "color1": ColorMath.rgb_to_hex(rgb1),
        "color2": ColorMath.rgb_to_hex(rgb2),
    }



def _truncate(value: float, places: int) -> str:
    """Format to `places` decimals by TRUNCATING, never rounding.

    Rounding can only be wrong in one direction that matters: a true 4.4996
    rounds to 4.500 and reads as a pass it has not earned. Truncation cannot
    overstate. It cannot understate across a bar either -- a true 4.5000001
    truncates to 4.500, which still reads as passing -- so it satisfies both
    gates: refuse when you must, and do not refuse when you could have answered.

    More precision alone does not fix this. It moves the trap to a finer scale;
    only truncation removes it.
    """
    scale = 10 ** places
    # int() truncates toward zero, and a contrast ratio is always >= 1.
    return f"{int(value * scale) / scale:.{places}f}"


def contrast_check(foreground: str, background: str) -> dict[str, Any]:
    """WCAG contrast ratio between a foreground and background color, with pass/fail
    for each accessibility level. Ratio runs 1.0 (none) to 21.0 (black on white)."""
    fg = ColorMath.hex_to_rgb(resolve_color(foreground, _store))
    bg = ColorMath.hex_to_rgb(resolve_color(background, _store))
    ratio = ColorMath.contrast_ratio(fg, bg)
    return {
        # UNROUNDED. A consumer compares this against a threshold and is
        # entitled to the real number: round(2.997638, 2) is 3.0, and
        # `if ratio >= 3.0` then passes a pair that fails. The wcag flags
        # below always compared the unrounded value and were never wrong.
        "ratio": ratio,
        "display": f"{_truncate(ratio, 3)}:1",
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
class SavePaletteResult(BaseModel):
    name: str = Field(description="Name the palette was stored under.")
    colors: list[str] = Field(description="The hex colors saved, in order.")
    notes: str = Field(description="Description stored on the palette; empty if none given.")
    color_count: int = Field(description="Number of colors in the saved palette.")
    overwritten: bool = Field(
        description="True if a palette with this name already existed and was replaced; False if newly created."
    )
    durable: bool = Field(
        description="True if the palette was written through to the durable HF Dataset and will survive a Space rebuild; False if it saved to the local working copy only (e.g. the Space HF_TOKEN is missing or lacks write scope), meaning it will be lost on the next restart."
    )


def save_palette(
    name: Annotated[str, Field(
        description="Unique key the palette is stored under. Reusing an existing name overwrites that palette (upsert). Can be referenced later by other tools as 'name:index', e.g. 'Spring line:2'."
    )],
    colors: Annotated[list[str], Field(
        description="Ordered list of hex colors, each '#RRGGBB' (e.g. '#d2bc93'). Order is preserved; at least one required."
    )],
    notes: Annotated[str, Field(
        description="Optional human-readable description stored as the palette's notes."
    )] = "",
) -> SavePaletteResult:
    """Persist a named color palette for later retrieval with get_palette or list_palettes.

    Use when the user wants to keep a set of colors under a name for reuse across sessions,
    such as a brand or launch palette. Idempotent upsert: a new name creates a palette, an
    existing name replaces it. The saved name can then be referenced by convert_color and
    generate_harmony as a palette reference. Author is recorded as RNVizion.

    The returned `durable` flag reports whether the save reached durable storage (the HF
    Dataset) or only the local working copy; a False here means the palette will not survive
    a Space rebuild and the Space's HF_TOKEN should be checked.
    """
    if not colors:
        raise ValueError("Provide at least one color to save.")
    existed = _store.get_palette(name) is not None
    result = _store.save_palette(name, colors, notes)
    return SavePaletteResult(
        name=name,
        colors=colors,
        notes=notes,
        color_count=len(colors),
        overwritten=existed,
        durable=bool(result.get("durable", False)),
    )


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
