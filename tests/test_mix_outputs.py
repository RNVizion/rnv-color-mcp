"""
What the six mix modes compute, pinned.

Until 2026-10-05 nothing in CI asserted a mix output except the paint figures
the descriptions quote (test_public_surfaces.TestPaintClaimsAreTrue). The smoke
script printed all six modes and asserted none, so a change to any of them
would have deployed green. This file pins what each mode returns today, and
the two derivations the brand register publishes against this engine.

THE REGISTER'S RECIPES ARE THE LOAD-BEARING CASES. BRAND_COLORS.md says the
teal and the two blues were mixed through this server and gives the calls. If
those calls stop returning those values, a published derivation stops
reproducing, and the people who would notice are not looking at this
repository. TestRegisterRecipes pins each call as the register writes it, in
hex. The second half of the blues' derivation, the placement at two
lightnesses, is pinned in test_contrast_contract.py.

THESE PIN BEHAVIOUR, NOT CORRECTNESS. Several pins record a limitation, and
each says so where it stands. Measured while writing this file:
  - cmy is the rgb average. Averaging in CMY is averaging in RGB, so the two
    modes agree to within one step on every channel. The engine's docstring
    says all colours mix to black; cyan + magenta + yellow gives #aaaaaa.
  - A colour mixed alone does not always come back. hsv, paint, ryb and cmy
    truncate a float to 8 bits, so a channel can lose one step and never
    gains one. rgb and lab return the colour exactly. Checked on every 8-bit
    colour on 2026-10-05: lab returns all 16,777,216, hsv changes 8,307,858
    of them and ryb 3,243,093. paint and cmy work one channel at a time and
    change 90 and 42 of the 256 values. In paint every value from 1 to 24 is
    among them, so a dark channel falls a step on each pass until it is 0.
  - The recipes depend on that truncation. The register calls the paint
    model "truncating", and rounding instead would give #02b1a1 for the teal
    and #5c83aa for the blue mix.
  - hsv has no answer for opposite hues. Their hue vectors cancel and the hue
    that comes back is floating-point noise at full saturation.
A pin that records a limitation is still a pin: change the behaviour on
purpose, move the pin in the same commit, and say what moved. The Phase 7
pigment model will move the paint rows deliberately, and the brand side is
told in the same session (Build Runbook, Phase 7).

What this file cannot see, and who can:
  - whether any mode is physically right. Nothing here compares against
    measured pigment or ink;
  - anything beyond the interpreters and the platform CI runs. hsv takes
    sines and cosines and four modes truncate a float, so another maths
    library could move a pin by a step. Python 3.12 and 3.13 agreed on
    20,000 triples in every mode on 2026-10-05;
  - order and scaling in general. Those properties are held on a fixed
    sample of 200 triples, which is not a proof;
  - the tool descriptions' prose. Only the teal example's two figures are
    read from server.py here; test_public_surfaces.py holds the rest;
  - the live server. A green run says the tree computes these values, not
    that the Space is running this tree.

TestPositiveControl is the diagnostic. One mix is worked by hand with integer
arithmetic, two modes known to disagree must disagree, the pin tables must
name exactly the modes the tool offers, and the sample must be the sample the
measurements were taken on. If it fails, the harness is wrong and every green
below it is a picture.
"""
from __future__ import annotations

import pathlib

import pytest

import api
from engine.color_math import ColorMath
from engine.resolve import CSS_NAMES, RNV_BRAND

MODES = ("rgb", "hsv", "lab", "paint", "ryb", "cmy")

#: Modes that return a single colour unchanged, and modes that may lose a step.
EXACT_ALONE = ("rgb", "lab")
TRUNCATING_ALONE = ("hsv", "paint", "ryb", "cmy")

#: One pair in every mode, at equal weights and at 1:4. The pair is the smoke
#: script's, brand black and brand gold, written in hex so that a decision in
#: the register cannot move a pin here.
BLACK_AND_GOLD = ["#1a1a1a", "#d2bc93"]
BLACK_AND_GOLD_EXPECTED = {
    "rgb": ("#766b56", "#ad9b7a"),
    "hsv": ("#756f64", "#ad9e83"),
    "lab": ("#6f6553", "#a99879"),
    "paint": ("#2b2b2a", "#4d4b47"),
    "ryb": ("#756b56", "#ad9b7a"),
    "cmy": ("#756b56", "#ad9b7a"),
}

#: Three chromatic colours at 4:1:2, where the six modes come furthest apart.
THREE_COLOURS = (["#f32962", "#55eca9", "#d6aa96"], [4, 1, 2])
THREE_COLOURS_EXPECTED = {
    "rgb": "#d4697b",
    "hsv": "#e95169",
    "lab": "#e27d7a",
    "paint": "#a33b72",
    "ryb": "#d46484",
    "cmy": "#d4697a",
}

#: Black and white, the shortest statement of each model's character.
BLACK_AND_WHITE = {
    "rgb": "#7f7f7f",    # 255 // 2
    "hsv": "#7f7f7f",
    "lab": "#777777",    # L* 50, the perceptual middle
    "paint": "#000000",  # a channel at 0 dominates: white does not lift black
    "ryb": "#7f7f7f",
    "cmy": "#7f7f7f",
}


def mix(colors, weights=None, mode="lab"):
    return api.mix_colors(colors, weights=weights, mode=mode)["hex"]


def channels(hex_color):
    return ColorMath.hex_to_rgb(hex_color)


def grey(value):
    return f"#{value:02x}{value:02x}{value:02x}"


def steps_apart(first, second):
    """The largest difference on any one channel, in 8-bit steps."""
    return max(abs(a - b) for a, b in zip(channels(first), channels(second)))


def sample(count, size):
    """`count` lists of `size` colours with weights 1 to 9, the same on every
    run and every interpreter. A small generator written out here, so the
    sample cannot move with the standard library's."""
    state = 72
    out = []
    for _ in range(count):
        colours, weights = [], []
        for _ in range(size):
            rgb = []
            for _ in range(3):
                state = (state * 1103515245 + 12345) % 2**31
                rgb.append((state >> 16) % 256)
            state = (state * 1103515245 + 12345) % 2**31
            colours.append(ColorMath.rgb_to_hex(tuple(rgb)))
            weights.append((state >> 16) % 9 + 1)
        out.append((colours, weights))
    return out


TRIPLES = sample(200, 3)
REGISTERED_VALUES = sorted(set(RNV_BRAND.values()) | set(CSS_NAMES.values()))


class TestPositiveControl:
    def test_a_mix_worked_by_hand(self):
        """rgb is integer arithmetic: black and white average to 255 // 2 =
        127, and at 1:3 to 255 * 3 // 4 = 191. No knowledge of the engine is
        needed to check either."""
        assert mix(["#000000", "#ffffff"], mode="rgb") == "#7f7f7f"
        assert mix(["#000000", "#ffffff"], [1, 3], mode="rgb") == "#bfbfbf"

    def test_two_modes_known_to_differ_do_differ(self):
        """For an equality, the control is a pair known to differ. If mode
        never reached the engine, every pin for a second mode would be a
        comparison of one function with itself."""
        stage = (["#6f94bc", "#00ffa3"], [6, 5])
        assert mix(*stage, mode="paint") != mix(*stage, mode="lab")

    def test_every_mode_the_tool_offers_is_pinned(self):
        """Equality, so a seventh mode fails here until it has pins."""
        offered = set(api._MIX_MODES)
        assert offered == set(MODES)
        for table in (BLACK_AND_GOLD_EXPECTED, THREE_COLOURS_EXPECTED, BLACK_AND_WHITE):
            assert set(table) == offered
        assert set(EXACT_ALONE) | set(TRUNCATING_ALONE) == offered

    def test_the_sample_is_the_same_sample(self):
        """The order and scaling tests are claims about this sample. If the
        generator changed, they would be claims about another one."""
        assert TRIPLES[0] == (["#c69761", "#0617ac", "#aed5a4"], [3, 5, 9])
        assert TRIPLES[-1] == (["#a89bbc", "#b3a153", "#d9faf1"], [9, 7, 4])
        assert len(TRIPLES) == 200


class TestRegisterRecipes:
    """BRAND_COLORS.md publishes these calls and their results. Read at
    rnv-brand@cba2e89, register rev 43, and written here in hex as the
    register writes them. Each stage starts from the value the register
    prints, so the teal's second stage starting from the first's result is
    two pins agreeing, not a third test."""

    def test_the_teal_first_stage(self):
        """BRAND_BLUE into a mint neon."""
        assert mix(["#6f94bc", "#00ffa3"], [6, 5], mode="paint") == "#00aaae"

    def test_the_teal_second_stage(self):
        """Then BRAND_GOLD into that."""
        assert mix(["#00aaae", "#d2bc93"], [8, 6], mode="paint") == "#00b0a0"

    def test_the_blue_mix(self):
        """2 parts the web violet, 6 parts CSS steelblue, 1 part brand gold,
        2 parts the status purple. The result is what place_lightness then
        places at L* 60.16 and 44.17 to make the pair;
        test_contrast_contract.py pins that half from this same value."""
        mixed = mix(["#b794ff", "#4682b4", "#d2bc93", "#926c89"], [2, 6, 1, 2], mode="paint")
        assert mixed == "#5c82a9"

    def test_the_recipes_still_describe_the_values_the_mirror_carries(self):
        """The one test here that reads the vocabulary. The recipes start
        from the blue and the gold and end on the teal and the two blues. If
        the register moves one of those values, the pins above still hold,
        because they are in hex, and the recipe has become provenance for a
        value that is gone. Update the example in mix_colors' description and
        this test. Do not change the engine to follow."""
        assert RNV_BRAND["teal"] == "#00b0a0"
        assert RNV_BRAND["blue"] == "#6f94bc"
        assert RNV_BRAND["dark blue"] == "#456c91"
        assert RNV_BRAND["brand gold"] == "#d2bc93"
        assert CSS_NAMES["steelblue"] == "#4682b4"

    def test_the_descriptions_teal_example_is_true(self):
        """mix_colors' description tells a model that the teal's ingredients
        at the same weights in lab give #9cc1a5, 15.94 away. Both figures are
        computed here and read from server.py."""
        first = mix(["#6f94bc", "#00ffa3"], [6, 5], mode="lab")
        in_lab = mix([first, "#d2bc93"], [8, 6], mode="lab")
        away = api.color_difference("#00b0a0", in_lab)["delta_e"]
        assert in_lab == "#9cc1a5"
        assert f"{away:.2f}" == "15.94"
        description = pathlib.Path(api.__file__).with_name("server.py").read_text(
            encoding="utf-8")
        assert "#9cc1a5" in description and "15.94" in description

    def test_the_teals_red_channel_leaves_zero_at_gold_weight_24(self):
        """A LIMITATION the register states as a threshold: red stays 0 until
        gold outweighs the teal stage three to one, 8:24, and reaches 1 there.
        Asserted as a threshold, at every weight from the recipe's 6 upward,
        because the figure first sent for it was one sample read as a
        multiple. It pins the paint model's empty-channel collapse. A pigment
        model that fixes the collapse moves it, and the brand side is told."""
        def red(gold_weight):
            return channels(mix(["#00aaae", "#d2bc93"], [8, gold_weight], mode="paint"))[0]

        assert [red(w) for w in range(6, 24)] == [0] * 18
        assert red(24) == 1
        assert mix(["#00aaae", "#d2bc93"], [8, 23], mode="paint") == "#00b698"
        assert mix(["#00aaae", "#d2bc93"], [8, 24], mode="paint") == "#01b698"


class TestEachModeIsPinned:
    @pytest.mark.parametrize("mode", MODES)
    def test_brand_black_and_brand_gold(self, mode):
        equal, mostly_gold = BLACK_AND_GOLD_EXPECTED[mode]
        assert mix(BLACK_AND_GOLD, mode=mode) == equal
        assert mix(BLACK_AND_GOLD, [1, 4], mode=mode) == mostly_gold

    @pytest.mark.parametrize("mode", MODES)
    def test_three_colours_at_unequal_weights(self, mode):
        colours, weights = THREE_COLOURS
        assert mix(colours, weights, mode=mode) == THREE_COLOURS_EXPECTED[mode]

    @pytest.mark.parametrize("mode", MODES)
    def test_black_and_white(self, mode):
        assert mix(["#000000", "#ffffff"], mode=mode) == BLACK_AND_WHITE[mode]

    def test_lab_is_the_default(self):
        assert api.mix_colors(BLACK_AND_GOLD)["hex"] == mix(BLACK_AND_GOLD, mode="lab")
        assert api.mix_colors(BLACK_AND_GOLD)["mode"] == "lab"

    def test_the_result_names_its_mode_and_agrees_with_itself(self):
        out = api.mix_colors(BLACK_AND_GOLD, mode="paint")
        assert out == {"hex": "#2b2b2a", "rgb": [43, 43, 42], "mode": "paint"}

    def test_a_name_mixes_as_its_value(self):
        """Brand names, without a literal: whatever the vocabulary says the
        names are today, they mix exactly as those values do."""
        named = ["near-black", "brand gold"]
        valued = [RNV_BRAND["near-black"], RNV_BRAND["brand gold"]]
        for mode in MODES:
            assert mix(named, [1, 4], mode) == mix(valued, [1, 4], mode)


class TestWhatEachModelDoes:
    def test_hsv_averages_hue_around_the_circle(self):
        """Two reds either side of 0 degrees meet at red. A straight average
        of the hue number would land on cyan; rgb, for comparison, loses
        saturation instead."""
        assert mix(["#ff0033", "#ff3300"], mode="hsv") == "#ff0000"
        assert mix(["#ff0033", "#ff3300"], mode="rgb") == "#ff1919"

    def test_hsv_with_no_hue_stays_grey(self):
        assert mix(["#404040", "#c0c0c0"], mode="hsv") == "#808080"

    @pytest.mark.parametrize("pair", [
        ["#ff0000", "#00ffff"], ["#0000ff", "#ffff00"], ["#ff00ff", "#00ff00"],
    ])
    def test_hsv_has_no_answer_for_opposite_hues(self, pair):
        """A LIMITATION. Opposite hues cancel, and what is left to take the
        hue from is rounding noise, while saturation and value are averaged
        as plain numbers. The result is some fully saturated colour: red and
        cyan give a chartreuse, #7fff00, on the interpreters CI runs. The hue
        means nothing, so this pins the shape and not the hue: full
        saturation, never the grey a vector average would give, and the same
        answer in either order."""
        hue, saturation, value = ColorMath.rgb_to_hsv(channels(mix(pair, mode="hsv")))
        assert saturation == 1.0 and value == 1.0
        assert mix(pair, mode="hsv") == mix(pair[::-1], mode="hsv")

    def test_ryb_makes_the_artists_secondaries(self):
        """Half-strength, because the mix is an average: a dark orange, a
        dark purple, and the green that test_public_surfaces also quotes."""
        assert mix(["red", "yellow"], mode="ryb") == "#7f3f00"
        assert mix(["red", "css:blue"], mode="ryb") == "#7f007f"
        assert mix(["yellow", "css:blue"], mode="ryb") == "#007f00"

    def test_cmy_is_the_rgb_average_to_within_one_step(self):
        """A LIMITATION, and the finding of this file. CMY is 1 - RGB, so the
        weighted mean of one is the weighted mean of the other; cmy differs
        from rgb only where a float truncates below an integer. The tool
        description calls cmy subtractive, like printer inks. Held on the
        fixed sample, and it follows from the arithmetic."""
        apart = [steps_apart(mix(c, w, "cmy"), mix(c, w, "rgb")) for c, w in TRIPLES]
        assert max(apart) <= 1
        assert 0 < sum(apart) < len(apart), "expected some triples to differ, and most to agree"

    def test_cmy_and_rgb_do_differ_by_that_one_step(self):
        """So the test above is not passing because the two are one function."""
        pair, weights = ["#f0d1ea", "#5d61a2"], [8, 8]
        assert mix(pair, weights, "rgb") == "#a699c6"
        assert mix(pair, weights, "cmy") == "#a699c5"

    def test_cmy_does_not_mix_the_three_inks_to_black(self):
        """A LIMITATION. The engine's docstring says all colours give black."""
        assert mix(["cyan", "magenta", "yellow"], mode="cmy") == "#aaaaaa"
        assert mix(["yellow", "cyan"], mode="cmy") == mix(["yellow", "cyan"], mode="rgb")


class TestAColourMixedAlone:
    @pytest.mark.parametrize("mode", EXACT_ALONE)
    def test_rgb_and_lab_return_it_unchanged(self, mode):
        changed = [value for value in REGISTERED_VALUES if mix([value], mode=mode) != value]
        assert changed == []

    @pytest.mark.parametrize("mode", TRUNCATING_ALONE)
    def test_the_other_four_lose_at_most_one_step_and_never_gain(self, mode):
        """A LIMITATION. Every channel comes back equal or one step lower.
        Checked here on every value the resolver can return for a name, and
        on 2026-10-05 on every 8-bit colour, so a value the register adds
        later cannot fail this."""
        moved = 0
        for value in REGISTERED_VALUES:
            for before, after in zip(channels(value), channels(mix([value], mode=mode))):
                assert after in (before, before - 1), (mode, value)
                moved += before - after
        assert moved > 0, f"{mode} returned every registered value unchanged"

    def test_paint_on_every_channel_value(self):
        """A LIMITATION, measured on every case there is and not on a sample.
        paint works one channel at a time, so 256 greys cover it. 90 of them
        come back one step lower and none comes back higher. White is one,
        because reflectance is capped below 1. So is every value from 1 to
        24."""
        lower = [v for v in range(256) if mix([grey(v)], mode="paint") != grey(v)]
        assert all(mix([grey(v)], mode="paint") == grey(v - 1) for v in lower)
        assert len(lower) == 90
        assert lower[:24] == list(range(1, 25))
        assert lower[24] == 26 and lower[-1] == 255

    def test_a_dark_channel_falls_to_zero_under_repeated_passes(self):
        """What the run from 1 to 24 means for this brand. Its web black,
        #0a0a0f, mixed alone in paint and the result mixed alone again, is
        pure black on the fifteenth pass. Its black, #1a1a1a, loses one step
        and stops, because 25 comes back unchanged. The descriptions
        recommend paint for blending brand colours, and a recipe in stages
        makes one pass per stage."""
        colour = "#0a0a0f"
        for _ in range(14):
            colour = mix([colour], mode="paint")
        assert colour == "#000001"
        assert mix([colour], mode="paint") == "#000000"
        assert mix(["#1a1a1a"], mode="paint") == "#191919"
        assert mix(["#191919"], mode="paint") == "#191919"


class TestOrderAndScale:
    """Held on the fixed sample of 200 triples. Exact where the arithmetic is
    integer or rounds at the end; within one step where a float is truncated
    and a sum can fall either side of an integer."""

    @pytest.mark.parametrize("mode", ("rgb", "hsv", "lab", "paint"))
    def test_order_does_not_change_the_result(self, mode):
        for colours, weights in TRIPLES:
            assert mix(colours, weights, mode) == mix(colours[::-1], weights[::-1], mode)

    @pytest.mark.parametrize("mode", ("ryb", "cmy"))
    def test_order_moves_ryb_and_cmy_by_at_most_one_step(self, mode):
        apart = [steps_apart(mix(c, w, mode), mix(c[::-1], w[::-1], mode)) for c, w in TRIPLES]
        assert max(apart) == 1, "exact now? then move the mode to the test above"

    @pytest.mark.parametrize("mode", ("rgb", "lab", "paint"))
    def test_scaling_every_weight_does_not_change_the_result(self, mode):
        for colours, weights in TRIPLES:
            assert mix(colours, weights, mode) == mix(colours, [3 * w for w in weights], mode)

    @pytest.mark.parametrize("mode", ("hsv", "ryb", "cmy"))
    def test_scaling_moves_hsv_ryb_and_cmy_by_at_most_one_step(self, mode):
        apart = [steps_apart(mix(c, w, mode), mix(c, [3 * x for x in w], mode))
                 for c, w in TRIPLES]
        assert max(apart) == 1, "exact now? then move the mode to the test above"


class TestWeights:
    def test_equal_weights_are_the_default(self):
        for mode in MODES:
            assert mix(BLACK_AND_GOLD, [1, 1], mode) == mix(BLACK_AND_GOLD, None, mode)

    def test_a_weight_of_zero_leaves_a_colour_out(self):
        assert mix(["#ff0000", "#0000ff"], [1, 0], mode="rgb") == "#ff0000"
        assert mix(["#ff0000", "#0000ff"], [0, 1], mode="rgb") == "#0000ff"

    def test_all_zero_weights_are_refused(self):
        with pytest.raises(ValueError):
            mix(["#ff0000", "#0000ff"], [0, 0], mode="rgb")

    def test_a_weight_for_every_colour_or_a_refusal(self):
        with pytest.raises(ValueError) as refusal:
            mix(["#ff0000", "#0000ff"], [1], mode="rgb")
        assert "weights must match the number of colors" in str(refusal.value)
