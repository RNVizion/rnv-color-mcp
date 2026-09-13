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
rnv-brand, by a human, in a deliberate commit. Nothing propagates
automatically, and nothing should appear to.

Identifiers used to be local by design — BRAND_GOLD here, GOLD upstream —
on the grounds that the check compares values and never names. The register
retired that rule on 2026-08-17: it permitted four spellings of one colour
across six repos, and a system that cannot hold one identifier across its
own repositories is not positioned to align anyone else's. The names now
match upstream. The check still compares values.

Mirrored from rnv-brand@9ddde4572859748e56e1ae532738f6a9cc548cbc, 2026-09-13.
Previously rnv-brand@a46a9eac6dd4, 2026-09-13; @0d96ff889c9f, 2026-09-12; @361c0e2a4b0e, 2026-08-24; @60bd56d1bf5c, 2026-08-22;
and @c4d479dbf16b, 2026-08-10, which carried the gold retired on 2026-08-17.
A mirror whose contents moved and whose SHA did not is worse than one that
is plainly stale: the SHA asserts it is current.

THE PREVIOUS PIN WAS TRUE FOR TWELVE HOURS AND FORTY-SEVEN MINUTES. It was
committed 2026-08-24 20:03 EDT recording that BRAND_STILL_GOLD and
BRAND_STANDBY_GOLD were registered upstream but absent from upstream's own
RNV_BRAND -- which was accurate when written. Upstream added the five gold
keys the next morning, 2026-08-25 08:51 EDT (rnv-brand@9c9c8d2), and from
that moment this file's note was false and nothing said so. It stayed false
for eighteen days, through a green suite, and was found from outside by a
consumer asking the live server for a PERMANENT brand colour and being
refused.

That note also claimed the wire-format guard in tests/test_brand_mirror.py
would fail if upstream added a key. IT COULD NOT. That guard compares this
file to WIRE_KEYS, a constant in the test file; both sides of it live in
this repository, so it fires when the MIRROR changes and is silent when
UPSTREAM does -- the only case it was written for. A guard scoped to one
side of a boundary cannot see the boundary.

The check that can is scripts/check_brand_currency.py, which parses
upstream's engine/brand.py and compares key sets. It runs in a SCHEDULED
workflow that gates nothing, because upstream moving is a queue and not a
defect of this repository; the same script runs in the gated path in
--mode transcription, where a mismatch against the pin above IS a defect.

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

BRAND_DARK_GOLD: Final[str] = "#8c7337"
"""Dark gold. The accent on light surfaces; also gold's shade on dark."""

BRAND_BLACK: Final[str] = "#1a1a1a"
"""Charcoal. The default 'black' when asked with no context."""

TRUE_BLACK: Final[str] = "#000000"
"""App window ground; text on gold, on either surface."""

WHITE: Final[str] = "#ffffff"
"""Light-surface cards and inputs; the neutral ramp's far anchor."""

WEB_BLACK: Final[str] = "#0a0a0f"
"""rnvizion.dev ground; social and OG base. Blue-tinted, deliberately."""

BRAND_STILL_GOLD: Final[str] = "#9b907a"
"""Stillness: not-live, dead, absence of life. The seventh permanent,
registered upstream 2026-08-23. Mirrored here 2026-09-12."""

BRAND_STANDBY_GOLD: Final[str] = "#ae986f"
"""The standby ring: running, but not the main event.

Not a failure state. Anything absent is BRAND_STILL_GOLD instead.

[MENTION: upstream renamed this identifier on 2026-08-23, value unchanged,
because the retired spellings -- BRAND_DOWN_GOLD, and the word degraded --
both assert that something is WRONG, which standby does not. The rename moved
the identifiers cleanly and the meaning survived in four comments upstream,
found and corrected the same day. This paragraph is a MENTION of the retired
terms, not a use of them, and the sweep in tests/test_brand_mirror.py skips
marked regions for exactly that reason: sweep it and you destroy the
explanation, skip it and you keep the meaning. :MENTION]
"""

BRAND_BLUE: Final[str] = "#6f94bc"
"""Dark-surface blue. The eighth permanent, and the register's second hue;
registered upstream 2026-09-12."""

BRAND_TEAL: Final[str] = "#00b0a0"
"""A brand colour, permanently registered; the tenth. Its first role is inline
code on the web, emitted as --rnv-code, but a role is where a colour starts
rather than where it is confined -- which upstream acted on.

[MENTION: this constant was BRAND_WEB_CODE for one day and was renamed
2026-09-13, because a name that states a surface is not undone by documentation
saying the colour is not confined to it. The PERMANENT key moved with it,
web-code to teal. The WEB key, the emitted token and the value are all
unchanged, and "web-code" is kept below as a resolver alias so the name it
shipped under still answers -- a retired IDENTIFIER, not a retired key. :MENTION] brand colours are the base set the brand
reuses, derives from, and builds ramps out of. Expect it anywhere the register
is consumed, the fashion app included.

What upstream means by "not a third brand hue" is narrower than membership and
should not be read as "not a brand colour". NO COLOUR CLEARS 4.5 ON BOTH
#1a1a1a AND #f5f5f5: the two grounds need Y >= 0.2215 and Y <= 0.1640, which do
not overlap, and setting the ratios equal gives a ceiling of 3.9954:1 for every
colour that exists. That is why every text role in the register is a PAIR --
gold with BRAND_DARK_GOLD, blue with BRAND_DARK_BLUE -- and the teal simply has
no partner derived yet. It is short of nothing the gold and the blue were not
also short of. A completeness question about the hue, not a membership question
about the colour.

Registered upstream 2026-09-12, mirrored 2026-09-13. Upstream states it was
mixed in two paint stages: BRAND_BLUE + #00ffa3 at 6:5, then that + BRAND_GOLD
at 8:6. Both stages reproduce byte-identical through this server."""

BRAND_DARK_BLUE: Final[str] = "#456c91"
"""Light-surface blue -- darker BECAUSE the ground is lighter, exactly as
BRAND_DARK_GOLD is. The ninth permanent; registered upstream 2026-09-12."""

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
    "dark gold": BRAND_DARK_GOLD,
    "gold dark": BRAND_DARK_GOLD,
    "light-mode gold": BRAND_DARK_GOLD,
    # The five gold keys upstream added 2026-08-25 (rnv-brand@9c9c8d2) and this
    # mirror did not carry until 2026-09-12. "still gold" is a PERMANENT brand
    # colour that this resolver refused for eighteen days.
    "still gold": BRAND_STILL_GOLD,
    "still-gold": BRAND_STILL_GOLD,
    "stillness": BRAND_STILL_GOLD,
    "standby gold": BRAND_STANDBY_GOLD,
    "standby-gold": BRAND_STANDBY_GOLD,
    # The blue pair, upstream 2026-09-12, mirrored the same day. "light-mode
    # blue" follows "light-mode gold": the light-mode value is the DARKER one.
    "blue": BRAND_BLUE,
    "brand blue": BRAND_BLUE,
    "rnv blue": BRAND_BLUE,
    "dark blue": BRAND_DARK_BLUE,
    "blue dark": BRAND_DARK_BLUE,
    "light-mode blue": BRAND_DARK_BLUE,
    # Inline-code teal, upstream 2026-09-12, mirrored 2026-09-13. Caught by
    # scripts/check_brand_currency.py the day after that check landed -- its
    # first live find, against eighteen days for the gap before it.
    "teal": BRAND_TEAL,
    "brand teal": BRAND_TEAL,
    "code": BRAND_TEAL,
    "code teal": BRAND_TEAL,
    "web code": BRAND_TEAL,
    # Kept deliberately: the name this colour shipped under on 2026-09-12,
    # before the 2026-09-13 rename. Nothing that resolved stops resolving.
    "web-code": BRAND_TEAL,
    "black": TRUE_BLACK,
    "true black": TRUE_BLACK,
    "white": WHITE,
    "brand white": WHITE,
    "web black": WEB_BLACK,
}

__all__ = [
    "BRAND_GOLD",
    "BRAND_DARK_GOLD",
    "BRAND_BLACK",
    "TRUE_BLACK",
    "WHITE",
    "WEB_BLACK",
    "BRAND_STILL_GOLD",
    "BRAND_STANDBY_GOLD",
    "BRAND_BLUE",
    "BRAND_DARK_BLUE",
    "BRAND_TEAL",
    "RNV_BRAND",
]
