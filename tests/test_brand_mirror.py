"""
Brand mirror guard.   RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

This file NAMES THE RETIRED VALUE ON PURPOSE. A sweep for gold literals must
exclude it by the marker above.

This repo is a MIRROR, not a consumer. What has to be true is narrower than in
the apps and more important: the values match upstream, the wire format does
not move when the identifiers do, and the SHA says which upstream commit these
values came from.

Since Phase 8.12 (2026-11-01) the comparison with upstream runs here too.
rnv-brand is installed at the pin from tests/requirements-dev.txt, so the
suite reads the register itself, offline and with no credential, and a mirror
that does not carry its pinned commit fails every pytest job and the deploy
gate. Upstream at HEAD is still not read here: that is a queue, and lives in
scripts/check_brand_currency.py --mode currency, which gates nothing.
"""
from __future__ import annotations

import importlib.metadata
import json
import pathlib
import inspect
import re

import pytest

from engine import brand_vocab as V

RETIRED_GOLD = "#b" "19145"
SYNCED_SHA = "108213b82a4f71163ddd04b56ea15c2425de45dc"

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEV_REQS = ROOT / "tests" / "requirements-dev.txt"
PIN_RE = re.compile(
    r"^rnv-brand\s*@\s*git\+https://github\.com/RNVizion/rnv-brand"
    r"(?:\.git)?@(?P<ref>\S+)\s*$", re.M)

# The mirror's constants, named as the register names them.
CONSTANTS = tuple(n for n in V.__all__ if n != "RNV_BRAND")

# The resolver vocabulary IS the wire format. A client sends these strings.
WIRE_KEYS = {
    "near-black", "near black", "brand black", "rnv black", "charcoal",
    "gold", "brand gold", "rnv gold",
    "dark gold", "gold dark", "light-mode gold",
    "still gold", "still-gold", "stillness",
    "standby gold", "standby-gold",
    "blue", "brand blue", "rnv blue",
    "dark blue", "blue dark", "light-mode blue",
    "teal", "brand teal", "code", "code teal", "web code", "web-code",
    "black", "true black", "white", "brand white", "web black",
}

# WHAT THIS SET CAN AND CANNOT CATCH. Both sides of the comparison with
# WIRE_KEYS live in this repository, so it fires when the mirror is edited
# without meaning to and is SILENT when upstream adds a key. It went green for
# eighteen days over a mirror eleven keys behind. Since 8.12 the tests at the
# end of this file compare the mirror with the installed register at the pin;
# they still cannot see upstream past the pin. That is
# scripts/check_brand_currency.py --mode currency, in a scheduled workflow that
# gates nothing, because upstream moving is a queue, not a defect of this
# repository.


def differences(mine: dict[str, str], upstream: dict[str, str]) -> list[str]:
    """Every way two vocabularies disagree, named. Empty means identical.

    Values are compared exactly: the resolver returns them as they are, so a
    change of case is a change.
    """
    out = [f"missing {k!r}: upstream has {upstream[k]}"
           for k in sorted(upstream.keys() - mine.keys())]
    out += [f"extra {k!r}: the mirror has {mine[k]}"
            for k in sorted(mine.keys() - upstream.keys())]
    out += [f"drift {k!r}: mirror {mine[k]}, upstream {upstream[k]}"
            for k in sorted(mine.keys() & upstream.keys())
            if mine[k] != upstream[k]]
    return out


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
        "BRAND_GOLD_DARK was retired in favor of BRAND_DARK_GOLD")


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

    still-gold is the case that earned this test: a PERMANENT brand color
    that the brand's own resolver refused from 2026-08-25 to 2026-09-12.
    """
    assert V.BRAND_STILL_GOLD == "#9b907a"
    assert V.BRAND_STANDBY_GOLD == "#ae986f"
    assert V.BRAND_BLUE == "#6f94bc"
    assert V.BRAND_DARK_BLUE == "#456c91"
    assert V.BRAND_TEAL == "#00b0a0"
    for alias in ("still gold", "still-gold", "stillness"):
        assert V.RNV_BRAND[alias] == V.BRAND_STILL_GOLD, alias
    for alias in ("standby gold", "standby-gold"):
        assert V.RNV_BRAND[alias] == V.BRAND_STANDBY_GOLD, alias
    for alias in ("blue", "brand blue", "rnv blue"):
        assert V.RNV_BRAND[alias] == V.BRAND_BLUE, alias
    for alias in ("dark blue", "blue dark", "light-mode blue"):
        assert V.RNV_BRAND[alias] == V.BRAND_DARK_BLUE, alias
    for alias in ("teal", "brand teal", "code", "code teal", "web code",
                  "web-code"):
        assert V.RNV_BRAND[alias] == V.BRAND_TEAL, alias


def test_retired_identifiers_are_not_used_outside_a_mention():
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
    for retired in ("degraded", "BRAND_DOWN_GOLD", "signal-down",
                    "signal-ring-down", "BRAND_WEB_CODE"):
        assert retired not in src, (
            f"outside a MENTION marker, the mirror still describes standby "
            f"by the retired term {retired!r}")


def test_the_retired_rationale_is_not_asserted_as_current():
    """The file used to justify local identifiers. That rule was retired in the
    same change that renamed them; the sentence had to go with it."""
    doc = V.__doc__ or ""
    assert "Identifiers are local by design" not in doc, (
        "the mirror still asserts a rule the register retired")


# ==================== The register itself, at the pin (8.12) ====================


def _register():
    try:
        import rnv_brand.brand as register
    except ImportError as exc:
        pytest.fail(
            f"rnv-brand is not importable as rnv_brand: {exc}\n\n"
            f"It is a declared test dependency. Install it with:\n\n"
            f"    pip install -r tests/requirements-dev.txt\n\n"
            f"Without it nothing in this suite compares the mirror with the "
            f"register.")
    return register


def _pin() -> str:
    match = PIN_RE.search(DEV_REQS.read_text(encoding="utf-8"))
    assert match, "tests/requirements-dev.txt does not pin rnv-brand"
    return match.group("ref")


def test_the_register_is_installed_as_rnv_brand():
    """The one the rest depend on. It fails, never skips: a skipped
    comparison and a passing one look the same in a summary line."""
    register = _register()
    assert isinstance(getattr(register, "RNV_BRAND", None), dict), (
        "rnv_brand.brand has no RNV_BRAND dict")


def test_this_repository_still_reads_its_own_engine():
    """rnv-brand also installs a top-level `engine` for older consumers. From
    this repository's root the server's own package must still win; if it
    did not, `from engine import brand_vocab` would fail for every test that
    reads the server."""
    import engine
    assert pathlib.Path(engine.__file__).resolve().parent == ROOT / "engine", (
        f"`engine` resolves to {engine.__file__}, not this repository's")


def test_the_pin_is_a_full_commit():
    """A branch or a tag can move under the same line. A commit cannot."""
    pin = _pin()
    assert re.fullmatch(r"[0-9a-f]{40}", pin), (
        f"rnv-brand is pinned to {pin!r}, which is not a full commit ID")


def test_the_three_pins_agree():
    """The dev requirements, SYNCED_SHA and the mirror's docstring each name
    the commit. Moving one without the others is the mirror claiming a
    revision it was not checked against."""
    doc = re.findall(r"Mirrored from rnv-brand@([0-9a-f]{40})", V.__doc__ or "")
    assert doc, "the mirror does not record an upstream SHA"
    assert {_pin(), SYNCED_SHA, doc[0]} == {SYNCED_SHA}, (
        f"requirements-dev pins {_pin()[:12]}, SYNCED_SHA is "
        f"{SYNCED_SHA[:12]}, the mirror says {doc[0][:12]}")


def test_the_installed_register_is_the_pinned_one():
    """The pin says which commit; pip records which one it installed (PEP 610,
    direct_url.json). They part when the pin moves and nobody reinstalls, and
    then the comparison below is against a revision nobody declared.

    pip's record covers only what pip installed, so the module that was
    imported must be one of that installation's recorded files, with the hash
    pip recorded; an rnv_brand found elsewhere on sys.path, or a file edited
    after the install, would otherwise borrow the record."""
    import base64
    import hashlib

    register = _register()
    dist = importlib.metadata.distribution("rnv-brand")
    loaded = pathlib.Path(register.__file__).resolve()
    record = next((f for f in (dist.files or [])
                   if pathlib.Path(dist.locate_file(f)).resolve() == loaded), None)
    assert record is not None and record.hash is not None, (
        f"rnv_brand.brand was imported from {loaded}, which the installed "
        f"rnv-brand distribution does not record as its file")
    digest = base64.urlsafe_b64encode(
        hashlib.new(record.hash.mode, loaded.read_bytes()).digest()
    ).rstrip(b"=").decode()
    assert digest == record.hash.value, (
        f"{loaded} has changed since pip installed it. Run:\n\n"
        f"    pip install --force-reinstall -r tests/requirements-dev.txt\n")
    raw = dist.read_text("direct_url.json")
    commit = ((json.loads(raw) if raw else {}).get("vcs_info") or {}).get(
        "commit_id")
    assert commit, (
        "rnv-brand was not installed from a git commit, so nothing records "
        "which revision is installed. Run:\n\n"
        "    pip install -r tests/requirements-dev.txt\n")
    assert commit == _pin(), (
        f"tests/requirements-dev.txt pins {_pin()[:12]} but the installed "
        f"register is {commit[:12]}. Run:\n\n"
        f"    pip install -r tests/requirements-dev.txt\n")


def test_the_mirror_carries_the_register_at_its_pin():
    """The transcription check, read from the installed package instead of
    fetched. A failure here is this repository being wrong: the mirror says
    it carries the pinned commit and does not."""
    register = _register()
    found = differences(dict(V.RNV_BRAND), dict(register.RNV_BRAND))
    for name in CONSTANTS:
        mine, theirs = getattr(V, name), getattr(register, name, None)
        if mine != theirs:
            found.append(f"constant {name}: mirror {mine}, register {theirs}")
    assert not found, (
        "the mirror does not carry the register at its pin:\n  "
        + "\n  ".join(found))


def test_positive_control_the_comparison_can_fail():
    """Without this the test above could pass by comparing nothing. Each kind
    of disagreement is planted and must be named; two equal tables must give
    none. If this fails, the harness is wrong, not the mirror."""
    base = {"gold": "#d2bc93", "teal": "#00b0a0"}
    assert differences(base, dict(base)) == []
    assert differences({"gold": "#d2bc93"}, base) == [
        "missing 'teal': upstream has #00b0a0"]
    assert differences({**base, "mauve": "#e0b0ff"}, base) == [
        "extra 'mauve': the mirror has #e0b0ff"]
    assert differences({**base, "gold": "#D2BC93"}, base) == [
        "drift 'gold': mirror #D2BC93, upstream #d2bc93"]
    assert len(CONSTANTS) == 11, CONSTANTS
