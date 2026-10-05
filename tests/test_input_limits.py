"""
Published input limits are enforced, not just published.

mix_colors has said "up to 12 colors" in its tool description, the README and
the Runbook since Phase 0, and until 2026-09-27 accepted any count. A limit
that is documented and not enforced is a claim the code does not back: a
caller who reads the description and a caller who does not get different
servers. Now the code refuses a thirteenth color with the count and a remedy.

The limit is asserted against the constant AND against the description text,
so moving one without the other fails here.

WEIGHTS ARE HELD THE SAME WAY SINCE 2026-10-05. The description says "optional
integer weights bias the blend". Until then a weight that was not above zero
was dropped inside the engine: [-1, 2] returned the second color alone, as a
computed mix, and nothing said the first had been left out. Found while
pinning the mix outputs (test_mix_outputs.py). Now a negative weight, a weight
that is not a whole number, and a set of weights that are all zero are each
refused with the position and the value. Zero still leaves a color out.

What this file cannot see: the MCP layer's own type check, which runs first.
It refuses a fractional weight, and it turns 2.0, "2" and true into whole
numbers before api.py sees them (read through an in-memory client on
2026-10-05). A negative integer is the one the schema lets through unchanged,
so for a caller of the server the negative check is the one that matters.

TestPositiveControl is the diagnostic: exactly the limit must mix, and
weights that are valid must still weigh. If it fails, the refusals below are
passing because mixing is broken, not because the checks work.
"""
from __future__ import annotations

import re

import pytest

import api


class TestPositiveControl:
    def test_exactly_the_limit_mixes(self):
        out = api.mix_colors(["#d2bc93"] * api.MAX_MIX_COLORS, mode="lab")
        assert out["hex"] == "#d2bc93"

    def test_valid_weights_still_weigh(self):
        """255 * 3 // 4 = 191 by hand, and a zero leaves its color out."""
        assert api.mix_colors(["#000000", "#ffffff"], weights=[1, 3], mode="rgb")["hex"] == "#bfbfbf"
        assert api.mix_colors(["#ff0000", "#0000ff"], weights=[1, 0], mode="rgb")["hex"] == "#ff0000"


class TestMixColorsLimit:
    def test_one_over_the_limit_is_refused_with_the_count(self):
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#d2bc93"] * (api.MAX_MIX_COLORS + 1))
        message = str(exc.value)
        assert f"up to {api.MAX_MIX_COLORS}" in message
        assert f"got {api.MAX_MIX_COLORS + 1}" in message

    def test_the_limit_is_checked_before_anything_is_resolved(self):
        """A refusal for the count must not be masked by a refusal for a
        color: the caller should learn the structural problem first."""
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["not-a-color"] * (api.MAX_MIX_COLORS + 1))
        assert "up to" in str(exc.value)

    def test_the_description_states_the_limit_the_code_enforces(self):
        """Read the model-facing text from the source, so this does not depend
        on how the framework exposes descriptions."""
        import pathlib
        src = pathlib.Path(api.__file__).with_name("server.py").read_text(encoding="utf-8")
        start = src.index("api.mix_colors,")
        described = re.search(r"Blend up to (\d+) colors", src[start:start + 400])
        assert described, "mix_colors' description no longer states a limit"
        assert int(described.group(1)) == api.MAX_MIX_COLORS


class TestMixWeights:
    def test_a_negative_weight_is_refused_with_its_position_and_value(self):
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#ff0000", "#0000ff", "#00ff00"], weights=[2, -3, 1], mode="rgb")
        message = str(exc.value)
        assert "Weight 2 is -3" in message
        assert "cannot be negative" in message
        assert "Use 0 to leave a color out" in message

    def test_it_is_refused_in_every_mode(self):
        """The engine dropped it in all six, so the check sits above them."""
        for mode in sorted(api._MIX_MODES):
            with pytest.raises(ValueError) as exc:
                api.mix_colors(["#ff0000", "#0000ff"], weights=[-1, 2], mode=mode)
            assert "Weight 1 is -1" in str(exc.value), mode

    def test_a_weight_is_refused_before_any_color_is_resolved(self):
        """Structure first, as with the count: the caller learns about the
        weight, not about a color the mix would never have reached."""
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["not-a-color", "#0000ff"], weights=[-1, 2])
        assert "Weight 1 is -1" in str(exc.value)

    @pytest.mark.parametrize("weight, shown", [
        (2.5, "2.5"), (2.0, "2.0"), ("2", "'2'"), (None, "None"), (True, "True"),
    ])
    def test_a_weight_that_is_not_a_whole_number_is_refused_by_name(self, weight, shown):
        """2.5 in rgb mode used to raise "Unknown format code 'x' for object
        of type 'float'", which is a report on the instrument. True is refused
        too: it is an int to Python and a mistake to a caller."""
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#ff0000", "#0000ff"], weights=[1, weight], mode="rgb")
        message = str(exc.value)
        assert f"Weight 2 is {shown}" in message
        assert "whole numbers, 0 or more" in message

    def test_all_zero_weights_are_refused_for_that_reason(self):
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#ff0000", "#0000ff"], weights=[0, 0])
        assert "Every weight is 0" in str(exc.value)

    def test_a_count_mismatch_names_both_counts(self):
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#ff0000", "#0000ff"], weights=[1])
        message = str(exc.value)
        assert "weights must match the number of colors" in message
        assert "Colors: 2" in message and "Weights: 1" in message
