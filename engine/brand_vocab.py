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

Mirrored from rnv-brand@0d96ff889c9f59286326207d40493207b419128d, 2026-09-12.
Previously rnv-brand@361c0e2a4b0e, 2026-08-24; @60bd56d1bf5c, 2026-08-22;
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
    "RNV_BRAND",
]
