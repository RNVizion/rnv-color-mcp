"""
Contrast reporting contract.   RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN

`ratio` is data and `display` is a label. This file pins the difference,
because collapsing it is what turned a 2.997638 failure into a 3.00 permission
that governed three repositories.
"""
from __future__ import annotations

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
