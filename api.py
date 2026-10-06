"""
RNV Color MCP - API surface

The tools, shaped as plain functions. This is the seam: server.py registers each one with a
model-facing description; nothing else about the engine changes.

Color engine : mix_colors, convert_color, place_lightness, generate_harmony,
               color_difference, contrast_check
Text         : transform_text
Palette store: save_palette, list_palettes, get_palette

Input and selector checks live here, at the seam, not in the engine: mix_colors' mode,
color count and weights, convert_color's `to`, generate_harmony's scheme, color_difference's
method, transform_text's operation, save_palette's name and colors. The engine keeps the
desktop apps' lenient defaults (an unknown scheme returns the base, an unknown operation
returns the text, an unknown method computes CIEDE2000); the server never relies on them.
tests/test_public_surfaces.py holds this listing and __all__ equal to the registered tools,
so neither can fall behind the server again.
"""
from __future__ import annotations

import os
from typing import Any
from typing import Annotated
from pydantic import BaseModel, Field

from engine.color_math import ColorMath
from engine.color_harmony import HARMONY_SCHEMES, generate_harmony as _harmony_by_name
from engine.text_transform import TextTransformer, TransformMode
from engine.palette_store import PaletteStore
from engine.resolve import CSS_NAMES, RNV_BRAND, UnknownColor, normalize_hex, resolve_color

# ---- mix mode -> ColorMath method ---------------------------------------
# The published contract since Phase 0: the tool description, the README, and the
# Runbook all say "up to 12". Enforced here since 2026-09-27; before that the code
# accepted any count while every public surface promised a limit. The count comes
# from the desktop mixer's slot count, not from the math, and the locked scope
# widens only on demand already in evidence -- none has been asked for.
MAX_MIX_COLORS = 12

_MIX_MODES = {
    "rgb": ColorMath.weighted_rgb_mix,     # additive average (blend like light)
    "hsv": ColorMath.weighted_hsv_mix,     # circular-hue average
    "lab": ColorMath.lab_perceptual_mix,   # perceptually uniform (default)
    "paint": ColorMath.kubelka_munk_mix,   # pigment physics (blend like real paint)
    "ryb": ColorMath.weighted_ryb_mix,     # artist's color wheel
    "cmy": ColorMath.subtractive_cmy_mix,  # subtractive (like printer inks)
}

# ---- delta-E method -----------------------------------------------------
# The methods the tool description offers, by name. The check on them was written
# on 2026-10-05 (US Eastern). Before it, the engine's own rule reached the caller:
# it computes cie76 for that exact string and CIEDE2000 for anything else, and
# color_difference returned the caller's own string as `method`. So any other
# spelling came back as a CIEDE2000 figure under the caller's label: "CIE76", as
# the README writes it, returned 3.9372 for a pair whose CIE76 is 6.5389. The scan
# of 2026-09-27 fixed the scheme and the operation, which failed open the same
# way, and did not look here.
_DIFFERENCE_METHODS = ("ciede2000", "cie76")

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
    rgb | hsv | lab | paint | ryb | cmy. Returns the mixed color.

    Case and outer spaces in mode are folded: "LAB" can only mean lab. The
    result names the mode that ran."""
    if not colors:
        raise ValueError("Provide at least one color to mix.")
    if len(colors) > MAX_MIX_COLORS:
        raise ValueError(
            f"mix_colors blends up to {MAX_MIX_COLORS} colors; got {len(colors)}. "
            f"Mix in stages: blend a subset, then mix that result with the rest."
        )
    key = mode.strip().lower() if isinstance(mode, str) else None
    if key not in _MIX_MODES:
        raise ValueError(f"Unknown mode {mode!r}. Choose from {sorted(_MIX_MODES)}.")
    if weights is None:
        weights = [1] * len(colors)
    if len(weights) != len(colors):
        raise ValueError(
            f"weights must match the number of colors. Colors: {len(colors)}. "
            f"Weights: {len(weights)}."
        )
    # Refused here since 2026-10-05. Until then the engine dropped any weight that was
    # not above zero, so [-1, 2] returned the second color alone, as a computed mix,
    # and nothing said the first had been left out. Zero still leaves a color out; that
    # is a choice a caller can make. A negative weight asks for something mixing cannot
    # do, and guessing what was meant is the one thing this server does not do.
    for position, weight in enumerate(weights, start=1):
        if isinstance(weight, bool) or not isinstance(weight, int):
            raise ValueError(
                f"Weight {position} is {weight!r}. Weights are whole numbers, 0 or more."
            )
        if weight < 0:
            raise ValueError(
                f"Weight {position} is {weight}. A weight cannot be negative: mixing adds "
                f"colors and cannot take one out. Use 0 to leave a color out."
            )
    if not any(weights):
        raise ValueError(
            "Every weight is 0, so there is nothing to mix. Give at least one color a "
            "weight above 0."
        )

    rgb_list = [ColorMath.hex_to_rgb(resolve_color(c, _store)) for c in colors]
    colors_weights = list(zip(rgb_list, weights))
    mixed = _MIX_MODES[key](colors_weights)
    if mixed is None:
        raise ValueError("Mixing produced no result (check colors and weights).")
    return {"hex": ColorMath.rgb_to_hex(mixed), "rgb": list(mixed), "mode": key}


def convert_color(color: str, to: str | None = None) -> dict[str, Any]:
    """Convert a hex color between formats. With `to`, returns just that format;
    otherwise returns all of hex/rgb/hsv/hsl/lab.

    Case and outer spaces in `to` are folded. An empty `to` is read as not given."""
    rgb = ColorMath.hex_to_rgb(resolve_color(color, _store))
    all_formats = {
        "hex": ColorMath.rgb_to_hex(rgb),
        "rgb": list(rgb),
        "hsv": list(ColorMath.rgb_to_hsv(rgb)),
        "hsl": list(ColorMath.rgb_to_hsl(rgb)),
        "lab": list(ColorMath.rgb_to_lab(rgb)),
    }
    if to:
        key = to.strip().lower()
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
    tetradic/square | monochromatic | compound.

    An unknown scheme is refused here, by name, against the table the engine
    dispatches on. The engine's own by-name entry point returns [base] for a
    name it does not know -- a one-colour "harmony" for a typo, indistinguishable
    from a real answer downstream. That is the guess the resolver refuses for
    colours, and the same rule applies to the scheme. (Selector checks live at
    this seam, beside mix_colors' mode check and convert_color's `to` check.)
    """
    key = scheme.strip().lower()
    if key not in HARMONY_SCHEMES:
        raise ValueError(f"Unknown scheme '{scheme}'. Choose from {sorted(HARMONY_SCHEMES)}.")
    rgb = ColorMath.hex_to_rgb(resolve_color(base, _store))
    result = _harmony_by_name(rgb, key)
    return [ColorMath.rgb_to_hex(c) for c in result]


def color_difference(color1: str, color2: str, method: str = "ciede2000") -> dict[str, Any]:
    """Perceptual difference (Delta-E) between two colors.
    method: "ciede2000" (default, modern standard) or "cie76". A value near 1.0 is the
    threshold a human eye can just notice; larger means more different.

    An unknown method is refused here, by name, with the choices. The engine
    falls through to CIEDE2000 for any name it does not know, which would arrive
    as a figure computed one way and labelled another. Case and outer spaces are
    folded first: the names stay distinct when folded, so "CIE76" can only mean
    cie76, and that is resolving, not guessing. The result names the method that
    was used, in the spelling above.
    """
    key = method.strip().lower() if isinstance(method, str) else None
    if key not in _DIFFERENCE_METHODS:
        raise ValueError(
            f"Unknown method {method!r}. Choose from {sorted(_DIFFERENCE_METHODS)}."
        )
    rgb1 = ColorMath.hex_to_rgb(resolve_color(color1, _store))
    rgb2 = ColorMath.hex_to_rgb(resolve_color(color2, _store))
    de = ColorMath.delta_e(rgb1, rgb2, method=key)
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
        "method": key,
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
# The eleven operations, keyed two ways: by their exact spelling, and by their
# case-folded spelling. The folded keys are unique (a test pins that), so folding
# case on the selector is resolution, not guessing: "uppercase" can only mean
# UPPERCASE. Whitespace and underscore normalization is deliberately NOT done
# here -- it is parked with alias normalization in the Runbook, and "snake case"
# refuses today with the list that shows the spelling.
_TEXT_OPERATIONS: dict[str, TransformMode] = {m.value: m for m in TransformMode}
_TEXT_OPERATIONS_FOLDED: dict[str, TransformMode] = {m.value.lower(): m for m in TransformMode}


def transform_text(text: str, operation: str) -> dict[str, str]:
    """Apply an exact text transformation (case conversions, etc.).

    An unknown operation is refused here, by name. The engine's dispatcher
    returns the text UNCHANGED for a mode it does not know -- which arrives as
    a `result` that reads like success and is not. That is the guess the
    resolver refuses for colours, and the same rule applies to the operation.
    """
    mode = _TEXT_OPERATIONS.get(operation)
    if mode is None:
        mode = _TEXT_OPERATIONS_FOLDED.get(operation.strip().lower())
    if mode is None:
        raise ValueError(
            f"Unknown operation '{operation}'. Choose from {[m.value for m in TransformMode]}."
        )
    return {"result": TextTransformer.transform_text(text, mode)}


# ---- palette store ------------------------------------------------------
class SavePaletteResult(BaseModel):
    name: str = Field(description="Name the palette was stored under.")
    colors: list[str] = Field(description="The hex colors saved, in order, normalized to '#rrggbb'.")
    notes: str = Field(description="Description stored on the palette; empty if none given.")
    color_count: int = Field(description="Number of colors in the saved palette.")
    overwritten: bool = Field(
        description="True if a palette with this name already existed and was replaced; False if newly created."
    )
    durable: bool = Field(
        description="True if the palette was written through to the durable HF Dataset and will survive a Space rebuild; False if it saved to the local working copy only (e.g. the Space HF_TOKEN is missing or lacks write scope), meaning it will be lost on the next restart."
    )
    durable_reason: str = Field(
        description="Empty when durable is true. Otherwise names the step that stopped durability: no token, the Dataset could not be reached or hydrated at startup, or the push failed. A false flag with no reason is a shrug; this is the reason."
    )


def _reserved_palette_name(name: str) -> str | None:
    """Why a palette may not be stored under `name`, or None if it may.

    Saved palettes resolve BEFORE brand and CSS names (engine/resolve.py), so a
    palette named "brand gold" would redefine that name for every caller -- and
    the public endpoint runs auth-off, so every caller can save. A name that is
    a hex literal can never be referenced (the hex layer answers first), and ":"
    is the swatch-index separator, so a name containing it cannot be referenced
    either. Each refusal names its reason; the resolver's order is unchanged.
    """
    key = name.strip().lower()
    if key in RNV_BRAND:
        return f"{name!r} is an RNV brand name and cannot be a palette name."
    if key in CSS_NAMES:
        return f"{name!r} is a CSS color name and cannot be a palette name."
    if key.startswith("css:"):
        return f"{name!r} uses the 'css:' namespace, which forces a CSS color, so it cannot be a palette name."
    if normalize_hex(key) is not None:
        return f"{name!r} reads as a hex literal, so a palette by that name could never be referenced."
    if ":" in key:
        return f"{name!r} contains ':', the swatch-index separator ('Spring line:2'), so it could not be referenced."
    return None


def save_palette(
    name: Annotated[str, Field(
        description="Unique key the palette is stored under. Reusing an existing name overwrites that palette (upsert). Can be referenced later by other tools as 'name:index', e.g. 'Spring line:2'. Refused, with the reason, if it is an RNV brand name, a CSS color name, a 'css:' form, a hex literal, or contains ':'."
    )],
    colors: Annotated[list[str], Field(
        description="Ordered list of colors. Each accepts what every other tool accepts: a hex ('#d2bc93'), a CSS name ('red'), an RNV brand name ('brand gold'), or a saved-palette reference ('Spring line:2'); each is resolved and stored as normalized '#rrggbb'. An unknown token refuses the whole save, naming the position. Order is preserved; at least one required."
    )],
    notes: Annotated[str, Field(
        description="Optional human-readable description stored as the palette's notes."
    )] = "",
) -> SavePaletteResult:
    """Persist a named color palette for later retrieval with get_palette or list_palettes.

    Use when the user wants to keep a set of colors under a name for reuse across sessions,
    such as a brand or launch palette. Idempotent upsert: a new name creates a palette, an
    existing name replaces it. The saved name can then be referenced by mix_colors,
    convert_color, generate_harmony and the other color tools as a palette reference.
    Author is recorded as RNVizion.

    Every color is resolved through the same resolver as the other tools and stored as
    hex, so the store only ever holds what the resolver can serve. Until 2026-09-27 it
    stored whatever it was handed; the live store held a swatch reading 'Purple', and the
    first arithmetic on it failed with an int() error instead of a named refusal. The
    resolution happens at save time, so a brand name saved today is a snapshot of today's
    value -- which is what a saved palette is for.

    The returned `durable` flag reports whether the save reached durable storage (the HF
    Dataset) or only the local working copy; a False here means the palette will not survive
    a Space rebuild, and `durable_reason` says which step stopped it.
    """
    if not colors:
        raise ValueError("Provide at least one color to save.")
    reason = _reserved_palette_name(name)
    if reason is not None:
        raise ValueError(reason)
    resolved: list[str] = []
    for i, token in enumerate(colors, start=1):
        try:
            resolved.append(resolve_color(token, _store))
        except UnknownColor as exc:
            raise ValueError(f"colors[{i}] {token!r}: {exc}") from exc
    existed = _store.get_palette(name) is not None
    result = _store.save_palette(name, resolved, notes)
    return SavePaletteResult(
        name=name,
        colors=resolved,
        notes=notes,
        color_count=len(resolved),
        overwritten=existed,
        durable=bool(result.get("durable", False)),
        durable_reason=str(result.get("durable_reason", "")),
    )


def list_palettes() -> list[dict[str, Any]]:
    """List every saved palette as {name, colors}."""
    return _store.list_palettes()


def get_palette(name: str) -> dict[str, Any] | None:
    """Retrieve one saved palette by name, or None if it doesn't exist."""
    return _store.get_palette(name)


__all__ = [
    "mix_colors", "convert_color", "place_lightness", "generate_harmony",
    "color_difference", "contrast_check", "transform_text",
    "save_palette", "list_palettes", "get_palette",
]
