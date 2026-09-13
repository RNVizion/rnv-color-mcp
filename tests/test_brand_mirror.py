"""
Brand mirror guard.   RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

This file NAMES THE RETIRED VALUE ON PURPOSE. A sweep for gold literals must
exclude it by the marker above.

This repo is a MIRROR, not a consumer. What has to be true is narrower than in
the apps and more important: the values match upstream, the wire format does
not move when the identifiers do, and the SHA says which upstream commit these
values came from.
"""
from __future__ import annotations

import pathlib
import inspect
import re

from engine import brand_vocab as V

RETIRED_GOLD = "#b" "19145"
SYNCED_SHA = "a46a9eac6dd48b1fc13257be7a1121610d7dad6d"

# The resolver vocabulary IS the wire format. A client sends these strings.
WIRE_KEYS = {
    "near-black", "near black", "brand black", "rnv black", "charcoal",
    "gold", "brand gold", "rnv gold",
    "dark gold", "gold dark", "light-mode gold",
    "still gold", "still-gold", "stillness",
    "standby gold", "standby-gold",
    "blue", "brand blue", "rnv blue",
    "dark blue", "blue dark", "light-mode blue",
    "code", "code teal", "web code", "web-code",
    "black", "true black", "white", "brand white", "web black",
}

# WHAT THIS SET CAN AND CANNOT CATCH. Both sides of the comparison below live
# in this repository, so it fires when the mirror is edited without meaning to
# and is SILENT when upstream adds a key. It went green for eighteen days over
# a mirror eleven keys behind. The check that sees upstream is
# scripts/check_brand_currency.py; it is not in this suite because the suite
# stays offline, and it is not in the gated path in --mode currency because
# upstream moving is a queue, not a defect of this repository.


def test_registered_values_match_the_register():
    assert V.BRAND_GOLD == "#d2bc93"
    assert V.BRAND_DARK_GOLD == "#8c7337"


def test_the_retired_gold_is_gone():
    src = pathlib.Path(V.__file__).read_text(encoding="utf-8")
    assert RETIRED_GOLD not in src, (
        "the mirror still carries the retired gold")


def test_the_old_identifier_is_gone():
    src = pathlib.Path(V.__file__).read_text(encoding="utf-8")
    assert "BRAND_GOLD_DARK" not in src, (
        "BRAND_GOLD_DARK was retired in favour of BRAND_DARK_GOLD")


def test_the_wire_format_did_not_move():
    """The rename touches identifiers. Clients send STRINGS.

    RNV_BRAND keys are the public contract; renaming a constant must not add,
    drop or respell one of them.
    """
    assert set(V.RNV_BRAND) == WIRE_KEYS, (
        f"resolver vocabulary changed -- added "
        f"{sorted(set(V.RNV_BRAND) - WIRE_KEYS)}, lost "
        f"{sorted(WIRE_KEYS - set(V.RNV_BRAND))}")


def test_every_gold_alias_resolves_to_the_new_value():
    for alias in ("dark gold", "gold dark", "light-mode gold"):
        assert V.RNV_BRAND[alias] == V.BRAND_DARK_GOLD, alias
    for alias in ("gold", "brand gold", "rnv gold"):
        assert V.RNV_BRAND[alias] == V.BRAND_GOLD, alias


def test_the_mirror_records_which_upstream_commit_it_carries():
    """A mirror whose contents moved and whose SHA did not is worse than one
    that is plainly stale: the SHA asserts it is current."""
    doc = V.__doc__ or ""
    found = re.findall(r"Mirrored from rnv-brand@([0-9a-f]{40})", doc)
    assert found, "the mirror does not record an upstream SHA"
    assert found[0] == SYNCED_SHA, (
        f"the mirror pins {found[0][:12]} but these values came from "
        f"{SYNCED_SHA[:12]}")


def test_the_registered_additions_resolve():
    """The four constants upstream registered after the 2026-08-24 pin.

    still-gold is the case that earned this test: a PERMANENT brand colour
    that the brand's own resolver refused from 2026-08-25 to 2026-09-12.
    """
    assert V.BRAND_STILL_GOLD == "#9b907a"
    assert V.BRAND_STANDBY_GOLD == "#ae986f"
    assert V.BRAND_BLUE == "#6f94bc"
    assert V.BRAND_DARK_BLUE == "#456c91"
    assert V.BRAND_WEB_CODE == "#00b0a0"
    for alias in ("still gold", "still-gold", "stillness"):
        assert V.RNV_BRAND[alias] == V.BRAND_STILL_GOLD, alias
    for alias in ("standby gold", "standby-gold"):
        assert V.RNV_BRAND[alias] == V.BRAND_STANDBY_GOLD, alias
    for alias in ("blue", "brand blue", "rnv blue"):
        assert V.RNV_BRAND[alias] == V.BRAND_BLUE, alias
    for alias in ("dark blue", "blue dark", "light-mode blue"):
        assert V.RNV_BRAND[alias] == V.BRAND_DARK_BLUE, alias
    for alias in ("code", "code teal", "web code", "web-code"):
        assert V.RNV_BRAND[alias] == V.BRAND_WEB_CODE, alias


def test_standby_is_not_described_by_the_retired_meaning():
    """A rename is complete when nothing still describes the thing by the
    meaning that was retired -- not when the identifiers move.

    Upstream's own rename moved three identifiers by regex and left the
    retired meaning standing in four comments, in the exact place a reader
    looks to learn what a value is FOR. This is that check, one repository
    out.

    It skips [MENTION: ... :MENTION] regions, because the paragraph explaining
    why a term was retired necessarily contains the term. Sweep the mentions
    and you destroy the explanation; skip the uses and you keep the meaning.
    The marker is what lets one pass do both.
    """
    src = re.sub(r"\[MENTION:.*?:MENTION\]", "", inspect.getsource(V), flags=re.S)
    for retired in ("degraded", "BRAND_DOWN_GOLD", "signal-down", "signal-ring-down"):
        assert retired not in src, (
            f"outside a MENTION marker, the mirror still describes standby "
            f"by the retired term {retired!r}")


def test_the_retired_rationale_is_not_asserted_as_current():
    """The file used to justify local identifiers. That rule was retired in the
    same change that renamed them; the sentence had to go with it."""
    doc = V.__doc__ or ""
    assert "Identifiers are local by design" not in doc, (
        "the mirror still asserts a rule the register retired")