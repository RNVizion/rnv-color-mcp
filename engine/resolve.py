"""
RNV Color MCP - Color name resolution

Turns plain-language color tokens into exact hex. Two layers, checked in order, so the
server speaks both registers: RNV (your brand vocabulary + your saved palettes) and color
(the universal CSS/X11 names everyone shares).

Resolution order (most specific wins):
    1. Hex literal            "#d2bc93", "d2bc93", "#fff"   -> normalized hex
    2. Saved palette swatch   "Spring line", "Spring line:2" -> a color from the store
    3. RNV brand name         "brand gold", "near-black"     -> your chosen hex
                              ("near-black" is charcoal #1a1a1a; the web ground
                               #0a0a0f answers to "web black")
    4. CSS / X11 name         "red", "rebeccapurple"         -> standard hex
    5. Unknown                -> UnknownColor (refuse; never guess)

Precedence note: the RNV layer is checked before CSS, so "gold" resolves to RNV brand gold
(#d2bc93), not CSS gold (#ffd700). Use "css:gold" to force the universal one.

Shadowing note: saved palettes sit ABOVE the brand layer, so a palette named "brand gold"
would redefine that name for every caller -- and the public endpoint runs auth-off, so
every caller can save. The write path (api.save_palette) therefore refuses a palette name
that is a brand key, a CSS name, a "css:" form, a hex literal, or contains ":" (the swatch
separator). The order here is unchanged; the collision is made impossible at the only
place it could be created.
"""
from __future__ import annotations

import re

from engine.brand_vocab import RNV_BRAND

# RNV brand vocabulary is mirrored in engine/brand_vocab.py. That file is NOT the
# source; the source is engine/brand.py in RNVizion/rnv-brand, and this mirror is
# corrected when drift is detected against it. It is carried locally on purpose:
# resolve_color is the hot path, and a fetch here would have to answer what happens
# when it fails -- fail closed and the server refuses every color, fall back and the
# local copy is needed anyway, guess and the rule below is already broken.

# --- universal CSS / X11 named colors (baked from matplotlib CSS4; no runtime dep) ---
CSS_NAMES: dict[str, str] = {
    'aliceblue': '#f0f8ff',
    'antiquewhite': '#faebd7',
    'aqua': '#00ffff',
    'aquamarine': '#7fffd4',
    'azure': '#f0ffff',
    'beige': '#f5f5dc',
    'bisque': '#ffe4c4',
    'black': '#000000',
    'blanchedalmond': '#ffebcd',
    'blue': '#0000ff',
    'blueviolet': '#8a2be2',
    'brown': '#a52a2a',
    'burlywood': '#deb887',
    'cadetblue': '#5f9ea0',
    'chartreuse': '#7fff00',
    'chocolate': '#d2691e',
    'coral': '#ff7f50',
    'cornflowerblue': '#6495ed',
    'cornsilk': '#fff8dc',
    'crimson': '#dc143c',
    'cyan': '#00ffff',
    'darkblue': '#00008b',
    'darkcyan': '#008b8b',
    'darkgoldenrod': '#b8860b',
    'darkgray': '#a9a9a9',
    'darkgreen': '#006400',
    'darkgrey': '#a9a9a9',
    'darkkhaki': '#bdb76b',
    'darkmagenta': '#8b008b',
    'darkolivegreen': '#556b2f',
    'darkorange': '#ff8c00',
    'darkorchid': '#9932cc',
    'darkred': '#8b0000',
    'darksalmon': '#e9967a',
    'darkseagreen': '#8fbc8f',
    'darkslateblue': '#483d8b',
    'darkslategray': '#2f4f4f',
    'darkslategrey': '#2f4f4f',
    'darkturquoise': '#00ced1',
    'darkviolet': '#9400d3',
    'deeppink': '#ff1493',
    'deepskyblue': '#00bfff',
    'dimgray': '#696969',
    'dimgrey': '#696969',
    'dodgerblue': '#1e90ff',
    'firebrick': '#b22222',
    'floralwhite': '#fffaf0',
    'forestgreen': '#228b22',
    'fuchsia': '#ff00ff',
    'gainsboro': '#dcdcdc',
    'ghostwhite': '#f8f8ff',
    'gold': '#ffd700',
    'goldenrod': '#daa520',
    'gray': '#808080',
    'green': '#008000',
    'greenyellow': '#adff2f',
    'grey': '#808080',
    'honeydew': '#f0fff0',
    'hotpink': '#ff69b4',
    'indianred': '#cd5c5c',
    'indigo': '#4b0082',
    'ivory': '#fffff0',
    'khaki': '#f0e68c',
    'lavender': '#e6e6fa',
    'lavenderblush': '#fff0f5',
    'lawngreen': '#7cfc00',
    'lemonchiffon': '#fffacd',
    'lightblue': '#add8e6',
    'lightcoral': '#f08080',
    'lightcyan': '#e0ffff',
    'lightgoldenrodyellow': '#fafad2',
    'lightgray': '#d3d3d3',
    'lightgreen': '#90ee90',
    'lightgrey': '#d3d3d3',
    'lightpink': '#ffb6c1',
    'lightsalmon': '#ffa07a',
    'lightseagreen': '#20b2aa',
    'lightskyblue': '#87cefa',
    'lightslategray': '#778899',
    'lightslategrey': '#778899',
    'lightsteelblue': '#b0c4de',
    'lightyellow': '#ffffe0',
    'lime': '#00ff00',
    'limegreen': '#32cd32',
    'linen': '#faf0e6',
    'magenta': '#ff00ff',
    'maroon': '#800000',
    'mediumaquamarine': '#66cdaa',
    'mediumblue': '#0000cd',
    'mediumorchid': '#ba55d3',
    'mediumpurple': '#9370db',
    'mediumseagreen': '#3cb371',
    'mediumslateblue': '#7b68ee',
    'mediumspringgreen': '#00fa9a',
    'mediumturquoise': '#48d1cc',
    'mediumvioletred': '#c71585',
    'midnightblue': '#191970',
    'mintcream': '#f5fffa',
    'mistyrose': '#ffe4e1',
    'moccasin': '#ffe4b5',
    'navajowhite': '#ffdead',
    'navy': '#000080',
    'oldlace': '#fdf5e6',
    'olive': '#808000',
    'olivedrab': '#6b8e23',
    'orange': '#ffa500',
    'orangered': '#ff4500',
    'orchid': '#da70d6',
    'palegoldenrod': '#eee8aa',
    'palegreen': '#98fb98',
    'paleturquoise': '#afeeee',
    'palevioletred': '#db7093',
    'papayawhip': '#ffefd5',
    'peachpuff': '#ffdab9',
    'peru': '#cd853f',
    'pink': '#ffc0cb',
    'plum': '#dda0dd',
    'powderblue': '#b0e0e6',
    'purple': '#800080',
    'rebeccapurple': '#663399',
    'red': '#ff0000',
    'rosybrown': '#bc8f8f',
    'royalblue': '#4169e1',
    'saddlebrown': '#8b4513',
    'salmon': '#fa8072',
    'sandybrown': '#f4a460',
    'seagreen': '#2e8b57',
    'seashell': '#fff5ee',
    'sienna': '#a0522d',
    'silver': '#c0c0c0',
    'skyblue': '#87ceeb',
    'slateblue': '#6a5acd',
    'slategray': '#708090',
    'slategrey': '#708090',
    'snow': '#fffafa',
    'springgreen': '#00ff7f',
    'steelblue': '#4682b4',
    'tan': '#d2b48c',
    'teal': '#008080',
    'thistle': '#d8bfd8',
    'tomato': '#ff6347',
    'turquoise': '#40e0d0',
    'violet': '#ee82ee',
    'wheat': '#f5deb3',
    'white': '#ffffff',
    'whitesmoke': '#f5f5f5',
    'yellow': '#ffff00',
    'yellowgreen': '#9acd32'
}

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class UnknownColor(ValueError):
    """Raised when a token resolves to no known color. The server refuses rather than guess."""


def normalize_hex(token: str) -> str | None:
    """'#D2BC93', 'd2bc93', '#fff' -> '#d2bc93' / '#ffffff'; anything else -> None.

    Public because the palette store normalizes through it on the write path:
    the one rule for what a hex literal is lives here, and a swatch is stored in
    the form this resolver returns.
    """
    m = _HEX_RE.match(token.strip())
    if not m:
        return None
    h = m.group(1).lower()
    if len(h) == 3:  # expand shorthand #abc -> #aabbcc
        h = "".join(c * 2 for c in h)
    return "#" + h


def _from_palette(token: str, store) -> str | None:
    """Resolve 'Name' (primary swatch) or 'Name:N' (Nth swatch, 1-based) from the store.

    A stored swatch is served only if it is a hex literal. The store has
    normalized every colour it accepts since 2026-09-27; before that it stored
    whatever it was handed, and the live store held a palette whose second
    swatch was the string 'Purple'. Resolving it returned that string as if it
    were hex, and the first arithmetic on it failed with
    `invalid literal for int() with base 16: 'Pu'` -- no reason, no location.
    A malformed swatch is now refused by palette, position and value, which is
    the second gate: say why and where. It is not resolved as a CSS name on the
    way out, because a store that holds a non-hex swatch is wrong and a lenient
    read would hide that forever.

    The same holds for a swatch the palette does not have (2026-09-30). When the
    palette exists, a missing or non-numeric swatch is refused with the palette,
    its swatch count and the valid range: a swatch number is a selector, and
    every selector here refuses with its valid choices. Before, it fell through
    to the brand and CSS layers and came back as "Don't know the color
    'Spring line:5'", which never said the palette was there. Refusing here
    shadows nothing: no brand or CSS name contains ":" (tests/test_resolve.py
    holds that).
    """
    if store is None:
        return None
    name, _, idx = token.partition(":")
    name = name.strip()
    pal = store.get_palette(name)
    if not pal:
        return None
    colors = pal.get("colors") or []
    n = len(colors)
    if n == 0:
        raise UnknownColor(
            f"{token!r}: palette {name!r} has no swatches. Re-save it with at least one color."
        )
    if idx.strip():
        try:
            k = int(idx)
        except ValueError:
            raise UnknownColor(
                f"{token!r}: {idx.strip()!r} is not a swatch number. "
                f"{_swatch_range(name, n)}"
            ) from None
        if not 1 <= k <= n:
            raise UnknownColor(
                f"{token!r} names swatch {k}, which does not exist. {_swatch_range(name, n)}"
            )
        i = k - 1
    else:
        i = 0
    swatch = colors[i]
    hexed = normalize_hex(str(swatch))
    if hexed is None:
        raise UnknownColor(
            f"Palette {name!r} swatch {i + 1} holds {swatch!r}, which is not a "
            f"hex color. Re-save the palette with save_palette; every color is "
            f"resolved and stored as hex on the way in."
        )
    return hexed


def _swatch_range(name: str, n: int) -> str:
    """The valid references to a palette of n swatches, for a refusal."""
    first, last = f"{name}:1", f"{name}:{n}"
    if n == 1:
        return f"Palette {name!r} has 1 swatch: {first!r}."
    return f"Palette {name!r} has {n} swatches: {first!r} through {last!r}."


def resolve_color(token: str, store=None) -> str:
    """Resolve one color token to hex. See module docstring for order. Raises UnknownColor."""
    if token is None or not str(token).strip():
        raise UnknownColor("Empty color token.")
    raw = str(token).strip()
    key = raw.lower()

    # explicit namespace escape: "css:gold" forces the universal layer
    if key.startswith("css:"):
        name = key[4:].strip()
        if name in CSS_NAMES:
            return CSS_NAMES[name]
        raise UnknownColor(f"Unknown CSS color: {name!r}")

    hexed = normalize_hex(raw)
    if hexed:
        return hexed

    pal = _from_palette(raw, store)
    if pal:
        return pal

    if key in RNV_BRAND:
        return RNV_BRAND[key]

    if key in CSS_NAMES:
        return CSS_NAMES[key]

    raise UnknownColor(
        f"Don't know the color {raw!r}. Use a hex, a CSS name, an RNV brand name, "
        f"or a saved palette reference."
    )


__all__ = ["resolve_color", "normalize_hex", "UnknownColor", "RNV_BRAND", "CSS_NAMES"]
