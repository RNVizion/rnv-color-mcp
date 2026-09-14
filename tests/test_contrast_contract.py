"""
Contrast reporting contract.   RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

`ratio` is data and `display` is a label. This file pins the difference,
because collapsing it is what turned a 2.997638 failure into a 3.00 permission
that governed three repositories.
"""
from __future__ import annotations

import pytest

import api


def test_ratio_is_not_rounded():
    """The pair that started all of this. round(2.997638, 2) is 3.0, and a
    consumer writing `if ratio >= 3.0` then passes a pair that fails."""
    r = api.contrast_check("#b" "19145", "#ffffff")
    assert r["ratio"] < 3.0, (
        f"ratio {r['ratio']} must be the real value, under the 3.0 bar")
    assert abs(r["ratio"] - 2.997638) < 1e-5, r["ratio"]


def test_the_flags_were_always_right():
    """They compare the unrounded value and always did. Nothing about this
    change makes them stricter -- it stops the number beside them lying."""
    r = api.contrast_check("#b" "19145", "#ffffff")
    assert r["wcag"]["AA_large_text"] is False
    assert r["wcag"]["AA_ui_components"] is False


def test_display_truncates_and_shows_three_decimals():
    r = api.contrast_check("#b" "19145", "#ffffff")
    assert r["display"] == "2.997:1", r["display"]


def test_display_never_overstates_across_a_bar():
    """The property the rule exists for. Truncation cannot show a figure at or
    above a bar that the true value does not reach."""
    from api import _truncate
    for bar in (3.0, 4.5, 7.0):
        for delta in (1e-4, 1e-3, 4e-3, 9e-3):
            true = bar - delta
            shown = float(_truncate(true, 3))
            assert shown < bar, (
                f"true {true} is under {bar} but displays as {shown}")


def test_display_does_not_understate_across_a_bar():
    """The other gate: a value that passes must not be shown as failing."""
    from api import _truncate
    for bar in (3.0, 4.5, 7.0):
        for delta in (1e-7, 1e-4, 1e-3, 5e-3):
            true = bar + delta
            assert float(_truncate(true, 3)) >= bar, (
                f"true {true} clears {bar} but displays below it")


def test_the_new_gold_reports_its_real_figure():
    r = api.contrast_check("dark gold", "white")
    assert abs(r["ratio"] - 4.542947) < 1e-5, r["ratio"]
    assert r["display"] == "4.542:1", r["display"]
    assert r["wcag"]["AA_normal_text"] is True


def test_a_known_pair_that_sits_close_to_a_bar_still_reads_correctly():
    """The register asserts three pairs within 0.02 of a bar, not one as its
    note claims. This is the closest of the survivors: it clears 7.0 by
    0.0055, and must not be shown as failing."""
    r = api.contrast_check("#000000", "#b" "19145")
    assert r["ratio"] > 7.0
    assert float(r["display"].split(":")[0]) >= 7.0, r["display"]


# --------------------------------------------------------------------------
# color_difference: the same contract, added 2026-09-12.
#
# contrast_check has returned an unrounded ratio beside a truncated display
# since it was written; color_difference rounded its reported figure. Two
# tools in one file disagreeing about whether the caller gets the real number
# is the defect, not the 5e-5 -- an asymmetry inside one API surfaces as a
# bug in whichever consumer arrives first and reads the wrong one.


def test_delta_e_is_not_rounded():
    """The returned value is the computed float, not a rounded report."""
    r = api.color_difference("#d2bc93", "#8c7337")
    de = r["delta_e"]
    assert isinstance(de, float)
    assert de != round(de, 4) or float(f"{de:.10f}") == de
    # the real check: the value survives a round-trip no rounded figure would
    assert abs(de - float(repr(de))) == 0.0


def test_delta_e_display_truncates_and_never_overstates():
    """Truncation is the conservative direction for a floor and the honest
    one for a ceiling: the display can never claim more separation than the
    real value has."""
    for a, b in (("#d2bc93", "#8c7337"), ("#9b907a", "#ae986f"),
                 ("#6f94bc", "#456c91"), ("#000000", "#ffffff")):
        r = api.color_difference(a, b)
        shown = float(r["display"])
        assert shown <= r["delta_e"] + 1e-12, (a, b, shown, r["delta_e"])
        assert r["delta_e"] - shown < 1e-4, (a, b)


def test_delta_e_of_a_color_with_itself_is_zero():
    """Positive control: if this is not 0.0 the harness is wrong, not the
    engine."""
    assert api.color_difference("#d2bc93", "#d2bc93")["delta_e"] == 0.0


# --------------------------------------------------------------------------
# place_lightness: the register's pair-construction rule, made executable.
#
# Added 2026-09-14 after a published derivation said "placed in LAB" with no
# tool behind the sentence -- the step had been done by hand in a scratch
# script. These cases pin the two things that make the tool trustworthy: it
# reproduces the register's own published values, and it refuses instead of
# clamping.


def test_it_reproduces_the_registers_blue_pair():
    """The load-bearing case. BRAND_BLUE and BRAND_DARK_BLUE were built from
    one mix at two lightnesses; if this tool cannot rebuild them it does not
    implement the rule it claims to."""
    out = api.place_lightness("#5c82a9", [60.16, 44.17])
    assert [p["hex"] for p in out["placements"]] == ["#6f94bc", "#456c91"]


def test_the_source_lab_is_unrounded():
    out = api.place_lightness("#5c82a9", [50.0])
    lab = out["source"]["lab"]
    assert lab["a"] != round(lab["a"], 4)


def test_quantization_error_is_reported_not_hidden():
    """8-bit hex cannot hold a and b to LAB's precision. The tool must say so
    per placement rather than imply the request was met exactly."""
    out = api.place_lightness("#5c82a9", [60.16, 44.17])
    for p in out["placements"]:
        err = p["quantization_error"]
        assert set(err) == {"L", "a", "b"}
        src = out["source"]["lab"]
        assert abs(p["achieved"]["a"] - src["a"] - err["a"]) < 1e-9
        assert abs(p["achieved"]["b"] - src["b"] - err["b"]) < 1e-9
    # and the spread between two placements of one hue is real, not zero
    a0, a1 = (p["achieved"]["a"] for p in out["placements"])
    assert abs(a0 - a1) > 0.0


def test_out_of_gamut_is_refused_not_clamped():
    """The whole point of lab_to_rgb_exact. #5c82a9's hue runs out of sRGB
    above L* ~83.9; asking for 95 must name the problem, not return the
    nearest color that happens to fit."""
    with pytest.raises(ValueError) as exc:
        api.place_lightness("#5c82a9", [95.0])
    assert "no sRGB representation" in str(exc.value)


def test_lightness_outside_the_scale_is_refused():
    with pytest.raises(ValueError):
        api.place_lightness("#5c82a9", [140.0])
    with pytest.raises(ValueError):
        api.place_lightness("#5c82a9", [])


def test_placing_at_the_source_lightness_is_a_round_trip():
    """Positive control. Asking for the lightness a color already has must
    return that color; if it does not, the harness or the conversion pair is
    wrong, not the placement logic."""
    src = api.place_lightness("#5c82a9", [50.0])["source"]["lab"]
    out = api.place_lightness("#5c82a9", [src["L"]])
    assert out["placements"][0]["hex"] == "#5c82a9"


def test_it_resolves_brand_names_like_every_other_tool():
    out = api.place_lightness("brand blue", [44.17])
    assert out["placements"][0]["hex"] == "#456c91"
