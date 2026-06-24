"""
RNV Color MCP - Color name resolution

Turns plain-language color tokens into exact hex. Two layers, checked in order, so the
server speaks both registers: RNV (your brand vocabulary + your saved palettes) and color
(the universal CSS/X11 names everyone shares).

Resolution order (most specific wins):
    1. Hex literal            "#d2bc93", "d2bc93", "#fff"   -> normalized hex
    2. Saved palette swatch   "Spring line", "Spring line:2" -> a color from the store
    3. RNV brand name         "brand gold", "near-black"     -> your chosen hex
    4. CSS / X11 name         "red", "rebeccapurple"         -> standard hex
    5. Unknown                -> UnknownColor (refuse; never guess)

Precedence note: the RNV layer is checked before CSS, so "gold" resolves to RNV brand gold
(#d2bc93), not CSS gold (#ffd700). Use "css:gold" to force the universal one.
"""
from __future__ import annotations

import re

# --- RNV brand vocabulary (your dialect; edit here to teach the server new brand colors) ---
RNV_BRAND: dict[str, str] = {
    "near-black": "#1a1a1a",
    "near black": "#1a1a1a",
    "brand black": "#1a1a1a",
    "rnv black": "#1a1a1a",
    "gold": "#d2bc93",
    "brand gold": "#d2bc93",
    "rnv gold": "#d2bc93",
    "dark gold": "#b19145",
    "gold dark": "#b19145",
    "light-mode gold": "#b19145",
}

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


def _normalize_hex(token: str) -> str | None:
    m = _HEX_RE.match(token.strip())
    if not m:
        return None
    h = m.group(1).lower()
    if len(h) == 3:  # expand shorthand #abc -> #aabbcc
        h = "".join(c * 2 for c in h)
    return "#" + h


def _from_palette(token: str, store) -> str | None:
    """Resolve 'Name' (primary swatch) or 'Name:N' (Nth swatch, 1-based) from the store."""
    if store is None:
        return None
    name, _, idx = token.partition(":")
    pal = store.get_palette(name.strip())
    if not pal or not pal.get("colors"):
        return None
    colors = pal["colors"]
    if idx.strip():
        try:
            i = int(idx) - 1
        except ValueError:
            return None
        if 0 <= i < len(colors):
            return colors[i]
        return None
    return colors[0]


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

    hexed = _normalize_hex(raw)
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


__all__ = ["resolve_color", "UnknownColor", "RNV_BRAND", "CSS_NAMES"]
