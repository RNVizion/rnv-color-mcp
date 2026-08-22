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
import re

from engine import brand_vocab as V

RETIRED_GOLD = "#b" "19145"
SYNCED_SHA = "60bd56d1bf5cec15942332a1c8db543134f5ad4f"

# The resolver vocabulary IS the wire format. A client sends these strings.
WIRE_KEYS = {
    "near-black", "near black", "brand black", "rnv black", "charcoal",
    "gold", "brand gold", "rnv gold",
    "dark gold", "gold dark", "light-mode gold",
    "black", "true black", "white", "brand white", "web black",
}


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


def test_the_retired_rationale_is_not_asserted_as_current():
    """The file used to justify local identifiers. That rule was retired in the
    same change that renamed them; the sentence had to go with it."""
    doc = V.__doc__ or ""
    assert "Identifiers are local by design" not in doc, (
        "the mirror still asserts a rule the register retired")
