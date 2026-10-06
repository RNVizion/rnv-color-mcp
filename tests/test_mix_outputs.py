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
  - A colour mixed alone does not always come back. hsv, paint and ryb
    truncate a float to 8 bits, so a channel can lose one step and never
    gains one. rgb, lab and cmy return the colour exactly. Checked on every
    8-bit colour on 2026-10-05: lab returns all 16,777,216, hsv changes
    8,307,858 of them and ryb 3,243,093. paint and cmy work one channel at a
    time: paint changes 90 of the 256 values and cmy none. In paint every
    value from 1 to 24 is among them, so a dark channel falls a step on each
    pass until it is 0.
  - The recipes depend on that truncation. The register calls the paint
    model "truncating". Rounding instead would give #01aaaf and #00b1a1 for
    the teal's two stages as the register prints them, and #5c83aa for the
    blue mix.
  - hsv has no answer for opposite hues. Their hue vectors cancel and the hue
    that comes back is floating-point noise at full saturation.
A pin that records a limitation is still a pin: change the behaviour on
purpose, move the pin in the same commit, and say what moved. The Phase 7
pigment model will move the paint rows deliberately, and the brand side is
told in the same session (Build Runbook, Phase 7).

CMY WAS REWRITTEN ON 2026-10-05 (US EASTERN), ON PURPOSE, AND ITS PINS MOVED
IN THE SAME COMMIT. Before that commit cmy averaged in CMY, the same arithmetic
as averaging in RGB: it agreed with rgb to within one step on every channel,
cyan + magenta + yellow gave #aaaaaa, and this file pinned that as a
limitation under a tool description that calls the mode subtractive. The
owner decided it should be subtractive. Each channel is now the weighted
geometric mean of the ingredients, the way the densities of transparent inks
add; engine/color_math.py has the model and where it comes from. What moved
here: cmy's row in each of the three tables below, its place among the modes
that return a colour unchanged and among the modes that do not depend on
order or scale, and the three tests that held it to rgb, which
TestCmyIsSubtractive replaces. No cmy figure was found outside this
repository: the brand register's recipes use paint and lab, and a search of
every text file at rnv-brand@aaf34ed and rnvizion.github.io@4c3e3d0 on
2026-10-05 found no mention of the mode. The RNV desktop apps keep their own
copy of the old function; nothing here reaches them.

What this file cannot see, and who can:
  - whether any mode is physically right. Nothing here compares against
    measured pigment or ink;
  - anything beyond the interpreters and the platform CI runs. hsv takes
    sines and cosines and three modes truncate a float, so another maths
    library could move one of their pins by a step. Python 3.12 and 3.13
    agreed on 20,000 triples in every mode on 2026-10-05, and on 300,000
    mixes in the new cmy the same day. cmy takes a logarithm and an
    exponential, and for cmy the question is asked here and not left open:
    with each moved by one part in a hundred trillion, which is 45 to 90 of
    the smallest steps a float of that size can take, the mixes in
    cmy_cases() and every grey alone come out the same
    (TestCmyIsSubtractive). Three mixes sit closer to a half step than that
    nudge reaches. Two are held to exact arithmetic by themselves and left
    out of that test, and the third, nearer than the engine's arithmetic can
    tell, is pinned as a limitation;
  - order and scaling in general. Those properties are held on a fixed
    sample of 200 triples, which is not a proof;
  - the tool descriptions' prose. Only the teal example's two figures are
    read from server.py here. test_public_surfaces.py holds the paint
    figures and the collision set. Nothing holds what the mix_colors
    description says of cmy, which is one clause: "subtractive like printer
    inks";
  - the live server. A green run says the tree computes these values, not
    that the Space is running this tree.

TestPositiveControl is the diagnostic. One mix is worked by hand with integer
arithmetic, two modes known to disagree must disagree, the pin tables must
name exactly the modes the tool offers, the exact reference that cmy is held
to is itself worked by hand, and the sample must be the sample the
measurements were taken on. If it fails, the harness is wrong and every green
below it is a picture.
"""
from __future__ import annotations

import math
import pathlib
import re
import sys
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

import api
from engine.color_math import ColorMath
from engine.resolve import CSS_NAMES, RNV_BRAND

MODES = ("rgb", "hsv", "lab", "paint", "ryb", "cmy")

#: Modes that return a single colour unchanged, and modes that may lose a step.
EXACT_ALONE = ("rgb", "lab", "cmy")
TRUNCATING_ALONE = ("hsv", "paint", "ryb")

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
    "cmy": ("#4a463e", "#8a7f68"),
}

#: Three chromatic colours at 4:1:2, where the six modes come furthest apart.
THREE_COLOURS = (["#f32962", "#55eca9", "#d6aa96"], [4, 1, 2])
THREE_COLOURS_EXPECTED = {
    "rgb": "#d4697b",
    "hsv": "#e95169",
    "lab": "#e27d7a",
    "paint": "#a33b72",
    "ryb": "#d46484",
    "cmy": "#ca4f78",
}

#: Black and white, the shortest statement of each model's character.
BLACK_AND_WHITE = {
    "rgb": "#7f7f7f",    # 255 // 2
    "hsv": "#7f7f7f",
    "lab": "#777777",    # L* 50, the perceptual middle
    "paint": "#000000",  # a channel at 0 dominates: white does not lift black
    "ryb": "#7f7f7f",
    "cmy": "#070707",    # black is a very dark ink, so half-strength black is near-black
}

#: Every mix engine/color_math.py's cmy docstring states: colours, weights and
#: result. TestCmyIsSubtractive computes each one and holds the docstring to
#: this table row by row, in both directions.
CMY_QUOTED = [
    (["yellow", "cyan"], None, "#07ff07"),
    (["yellow", "magenta"], None, "#ff0707"),
    (["cyan", "magenta"], None, "#0707ff"),
    (["cyan", "magenta", "yellow"], None, "#171717"),
    (["black", "white"], None, "#070707"),
    (["red", "yellow"], None, "#ff0700"),
    (["yellow", "#0000ff"], None, "#070707"),
    (["white", "#0000ff"], [1, 1], "#0707ff"),
    (["white", "#0000ff"], [3, 1], "#2a2aff"),
    (["white", "#0000ff"], [9, 1], "#7c7cff"),
    (["white", "#0000ff"], [99, 1], "#ededff"),
]

#: Mixes of greys whose true value is close to the middle between two steps:
#: colours, weights, the half it is near, bounds on how far short of that half
#: it falls (negative when it is above), and the step it belongs to. In the
#: model nothing lands exactly on a half; the comment on
#: ColorMath.CMY_ZERO_REFLECTANCE says why. These three are far enough from
#: one for the nudge test to move exp and log without moving them.
CMY_NEAR_A_HALF = [
    # 117 and 181 at 1:2. The nearest pair of channel values at the ratios
    # 1:1, 1:2, 1:3, 2:3, 1:9 and 1:99, either way round (2026-10-05).
    (["#757575", "#b5b5b5"], [1, 2], "156.5", "1.70e-6", "1.71e-6", "#9c9c9c"),
    # 79, 132 and 253 at 4:9:6: three colours, less than a billionth short.
    (["#4f4f4f", "#848484", "#fdfdfd"], [4, 9, 6], "145.5", "8.33e-10", "8.34e-10", "#919191"),
    # 3 and 173 at 9:1: just above a half, so it goes up.
    (["#030303", "#adadad"], [9, 1], "4.5", "-1.28e-5", "-1.27e-5", "#050505"),
]

#: Two mixes nearer a half than the nudge test reaches, and still far enough
#: from it for the float to be right: on every mix measured the float was
#: within 1e-13 of a step of the true value (engine/color_math.py). They are
#: held to exact arithmetic by themselves.
CMY_NEARER_THAN_THE_NUDGE = [
    # Six greys in equal parts, 8.2e-13 of a step short of 79.5.
    (["#070707", "#4f4f4f", "#616161", "#676767", "#b9b9b9", "#f7f7f7"], None,
     "79.5", "8.20e-13", "8.21e-13", "#4f4f4f"),
    # Eleven greys in equal parts, 1.2e-13 short of 81.5. With this row a
    # tolerance of 2e-13 added before rounding fails; one of 1e-13 does not.
    (["#010101", "#131313", "#535353", "#676767", "#7d7d7d", "#7d7d7d", "#9b9b9b",
      "#e3e3e3", "#e3e3e3", "#e3e3e3", "#e5e5e5"], None,
     "81.5", "1.22e-13", "1.23e-13", "#515151"),
]

#: A LIMITATION. Nine greys in equal parts whose true value is 1.6e-14 of a
#: step short of 105.5. A float could hold that: the one just below 105.5 is
#: the nearer to it. The engine's arithmetic cannot, because its result is
#: good to about 1e-13 of a step and not to the last bit. Where this was
#: measured (glibc 2.39, Python 3.12 and 3.13, 2026-10-05 US Eastern) it
#: comes out at 105.5 exactly and cmy returns 106, where exact arithmetic
#: gives 105. The pin allows either step, so that a maths library whose last
#: bit differs does not fail it.
CMY_NEARER_THAN_THE_ARITHMETIC_CAN_TELL = (
    ["#010101", "#474747", "#959595", "#cbcbcb", "#e2e2e2", "#e2e2e2",
     "#f0f0f0", "#f8f8f8", "#f8f8f8"],
    "105.5", "1.61e-14", "1.62e-14", ("#696969", "#6a6a6a"),
)

#: A stored 0 in steps, as exact_cmy reads it: half a step over e, with e
#: exactly as a float holds it. Written here and not read from the engine.
EXACT_ZERO = Fraction(1, 2) / Fraction(math.e)


def mix(colors, weights=None, mode="lab"):
    return api.mix_colors(colors, weights=weights, mode=mode)["hex"]


def channels(hex_color):
    return ColorMath.hex_to_rgb(hex_color)


def grey(value):
    return f"#{value:02x}{value:02x}{value:02x}"


def steps_apart(first, second):
    """The largest difference on any one channel, in 8-bit steps."""
    return max(abs(a - b) for a, b in zip(channels(first), channels(second)))


def rounded_average(colours, weights):
    """The weighted average of each channel, rounded half up, in integer
    arithmetic: no knowledge of the engine is needed to check it."""
    total = sum(weights)
    return tuple(
        (2 * sum(channels(c)[i] * w for c, w in zip(colours, weights)) + total) // (2 * total)
        for i in range(3)
    )


def exact_cmy(colours, weights=None):
    """The cmy model worked without a float, as a second statement of it. Each
    channel is the weighted geometric mean of its values, a stored 0 counts
    as EXACT_ZERO, and the result is rounded to the nearest step. Raising
    both sides to the total weight turns the root into whole-number powers,
    so every comparison here is exact. Returns the three channels, and
    whether any of them was exactly on a half step. A name is resolved the
    way the tools resolve it; the arithmetic is all that is independent."""
    weights = weights or [1] * len(colours)
    total = sum(weights)
    values = [api.convert_color(colour, to="rgb")["rgb"] for colour in colours]
    result, on_a_half = [], False
    for i in range(3):
        power = Fraction(1)
        for rgb, weight in zip(values, weights):
            power *= (Fraction(rgb[i]) if rgb[i] else EXACT_ZERO) ** weight
        step = 0
        while Fraction(2 * step + 1, 2) ** total <= power:
            on_a_half = on_a_half or Fraction(2 * step + 1, 2) ** total == power
            step += 1
        result.append(step)
    return tuple(result), on_a_half


def true_grey_value(colours, weights=None):
    """The cmy value of a mix of greys with no 0 among them, to 50 digits."""
    weights = weights or [1] * len(colours)
    with localcontext() as context:
        context.prec = 50
        logs = sum(Decimal(weight) * Decimal(channels(colour)[0]).ln()
                   for colour, weight in zip(colours, weights))
        return (logs / Decimal(sum(weights))).exp()


class NudgedMath:
    """The math module with exp and log off by a relative error: a stand-in
    for a platform whose maths library rounds them another way. Everything
    else is the real module."""

    def __init__(self, exp_error=0.0, log_error=0.0):
        self.exp_error, self.log_error = exp_error, log_error

    def __getattr__(self, name):
        return getattr(math, name)

    def exp(self, x):
        return math.exp(x) * (1.0 + self.exp_error)

    def log(self, x):
        return math.log(x) * (1.0 + self.log_error)


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


def cmy_cases():
    """The cmy mixes the tables hold, one part #0000ff in 1 to 99 of white, and
    the fixed sample, as (colours, weights). The mixes nearer a half than the
    nudge reaches are not here."""
    cases = [(c, w) for c, w, _ in CMY_QUOTED]
    cases += [(row[0], row[1]) for row in CMY_NEAR_A_HALF]
    cases += [(BLACK_AND_GOLD, None), (BLACK_AND_GOLD, [1, 4]), THREE_COLOURS,
              (["#000000", "#ffffff"], None)]
    cases += [(["white", "#0000ff"], [white, 1]) for white in range(1, 100)]
    return cases + TRIPLES


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

    def test_the_exact_cmy_reference_worked_by_hand(self):
        """exact_cmy is what the engine's cmy is held to, so it is checked
        first, by hand. A stored 0 is half a step over e, 0.1839 of a step.
        Black and white in equal parts: 0.1839 times 255 is 46.9, and its
        square root is between 6.5 and 7.5, because 42.25 <= 46.9 < 56.25. So
        7. Two parts #020202 and one part #404040: 2 times 2 times 64 is 256,
        and its cube root is between 5.5 and 6.5, because 166.4 <= 256 <
        274.6. So 6. A colour alone is itself. None of these is on a half."""
        assert exact_cmy(["#000000", "#ffffff"]) == ((7, 7, 7), False)
        assert exact_cmy(["#020202", "#404040"], [2, 1]) == ((6, 6, 6), False)
        assert exact_cmy(["#40a0ff"]) == ((64, 160, 255), False)

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


class TestCmyIsSubtractive:
    """cmy mixes subtractively: each channel is the weighted geometric mean of
    the ingredients. These pin what that returns today and the properties the
    engine's docstring states for it. They do not say the model is physically
    right; nothing here is compared with measured ink. They do say the
    arithmetic is the model's: the engine is held to the same model worked
    without a float, and to the same answers when exp and log are moved in
    their last bits."""

    @pytest.mark.parametrize("colours, weights, expected", CMY_QUOTED)
    def test_quoted_mix(self, colours, weights, expected):
        assert mix(colours, weights, mode="cmy") == expected

    def test_the_engines_docstring_states_each_quoted_mix(self):
        """Derive once, assert everywhere. The docstring writes each mix as
        `a + b -> #hex`, with `at m:n` where it gives weights. Every one is
        read here and has to be a row of the table, colours, weights and
        result together, and every row has to be in the docstring. So a
        figure cannot move to another mix, or stay behind when the table
        moves. The only other hex the docstring prints is #aaaaaa, what the
        three inks returned before the rewrite of 2026-10-05, which is the
        rgb average."""
        doc = ColorMath.subtractive_cmy_mix.__doc__
        colour = r"(?:[a-z]+|#[0-9a-f]{6})"
        stated = {
            (tuple(names.split(" + ")),
             tuple(int(part) for part in ratio.split(":")) if ratio else None,
             result)
            for names, ratio, result in re.findall(
                rf"({colour}(?: \+ {colour})+)(?: at (\d+(?::\d+)+))? -> (#[0-9a-f]{{6}})", doc)
        }
        table = {(tuple(c), tuple(w) if w else None, r) for c, w, r in CMY_QUOTED}
        assert stated == table
        ingredients = {c for colours, _, _ in CMY_QUOTED for c in colours if c.startswith("#")}
        results = {result for _, _, result in CMY_QUOTED}
        assert set(re.findall(r"#[0-9a-f]{6}", doc)) == results | ingredients | {"#aaaaaa"}
        assert mix(["cyan", "magenta", "yellow"], mode="rgb") == "#aaaaaa"

    def test_the_engine_agrees_with_exact_arithmetic(self):
        """A pin says what the engine returned when it was written. This says
        the pins are also what the model gives with no float involved: the
        quoted mixes, the mixes near a half, cmy's row in each table, one part
        #0000ff in 1 to 99 of white, and all 200 triples."""
        for colours, weights in cmy_cases():
            exact, _ = exact_cmy(colours, weights)
            assert channels(mix(colours, weights, "cmy")) == exact, (colours, weights)

    @pytest.mark.parametrize("colours, weights, half, at_least, at_most, expected",
                             CMY_NEAR_A_HALF + CMY_NEARER_THAN_THE_NUDGE)
    def test_a_mix_near_a_half_goes_the_right_way(self, colours, weights, half, at_least,
                                                  at_most, expected):
        """Each of these is close to the middle between two steps and not on
        it. How close is worked here to 50 digits, so a row cannot claim a
        distance it does not have, and the engine has to land on the side the
        true value is on. The last two rows are nearer than the nudge test
        reaches: 8.2e-13 and 1.2e-13 of a step."""
        short = Decimal(half) - true_grey_value(colours, weights)
        assert Decimal(at_least) < short < Decimal(at_most)
        assert mix(colours, weights, mode="cmy") == expected
        assert channels(expected) == exact_cmy(colours, weights)[0]

    def test_a_mix_nearer_a_half_than_the_arithmetic_can_tell(self):
        """A LIMITATION, and the edge of what "rounded to the nearest step"
        means here. The true value is worked to 50 digits and is short of the
        half by less than the error the engine's float has been measured to
        carry, so the engine cannot be held to the side the true value is on.
        Exact arithmetic says 105. The engine has to return one of the two
        steps the true value lies between: 106 where this was measured."""
        colours, half, at_least, at_most, either = CMY_NEARER_THAN_THE_ARITHMETIC_CAN_TELL
        short = Decimal(half) - true_grey_value(colours)
        assert Decimal(at_least) < short < Decimal(at_most)
        assert short < Decimal("1e-13")
        assert exact_cmy(colours) == ((105, 105, 105), False)
        assert mix(colours, mode="cmy") in either

    @pytest.mark.parametrize("exp_error, log_error", [
        (-1e-14, -1e-14), (-1e-14, 1e-14), (1e-14, -1e-14), (1e-14, 1e-14),
        (-1e-14, 0.0), (1e-14, 0.0), (0.0, -1e-14), (0.0, 1e-14),
    ])
    def test_exp_and_log_moved_in_their_last_bits_move_no_result(self, monkeypatch, exp_error,
                                                                  log_error):
        """exp and log are the two parts of cmy that belong to the platform.
        With each moved by one part in a hundred trillion, either way, every
        case in cmy_cases() and every grey mixed alone comes out as it does
        unmoved. That is 45 to 90 of the smallest steps a float of that size
        can take: a wide margin, not a measurement of any library."""
        cases = cmy_cases() + [([grey(value)], None) for value in range(256)]
        unmoved = [mix(colours, weights, "cmy") for colours, weights in cases]
        monkeypatch.setattr("engine.color_math.math", NudgedMath(exp_error, log_error))
        assert [mix(colours, weights, "cmy") for colours, weights in cases] == unmoved

    def test_the_nudges_reach_the_engine(self, monkeypatch):
        """The control for the test above: a tamper has to reach what it
        tests. With exp a fifth low, white mixed alone is no longer white.
        With log a fifth high, a mid grey mixed alone is no longer itself. So
        both stand-ins are in the engine's path."""
        assert mix(["#ffffff"], mode="cmy") == "#ffffff"
        assert mix(["#808080"], mode="cmy") == "#808080"
        monkeypatch.setattr("engine.color_math.math", NudgedMath(exp_error=-0.2))
        assert mix(["#ffffff"], mode="cmy") != "#ffffff"
        monkeypatch.setattr("engine.color_math.math", NudgedMath(log_error=0.2))
        assert mix(["#ffffff"], mode="cmy") == "#ffffff"
        assert mix(["#808080"], mode="cmy") != "#808080"

    def test_no_channel_is_lighter_than_the_rounded_average(self):
        """Inks only take light away. In the model that is certain, and the
        engine's docstring says why. Here the engine is held to it: on the
        fixed sample, where every triple also comes out darker than its
        average on some channel, so this is not passing because cmy is still
        the average; and on black with every grey at five ratios, because a
        channel at 0 is where the model departs furthest from plain
        averaging. The comparison is with the average rounded half up, as cmy
        rounds. It is not with the rgb mode, which truncates: on this sample
        cmy is as much as one step above rgb on a channel, and that is
        asserted too."""
        darker_somewhere, most_above_rgb = 0, 0
        for colours, weights in TRIPLES:
            mixed = channels(mix(colours, weights, "cmy"))
            average = rounded_average(colours, weights)
            assert all(m <= a for m, a in zip(mixed, average)), (colours, weights)
            darker_somewhere += any(m < a for m, a in zip(mixed, average))
            in_rgb = channels(mix(colours, weights, "rgb"))
            most_above_rgb = max(most_above_rgb, max(m - r for m, r in zip(mixed, in_rgb)))
        assert darker_somewhere == len(TRIPLES)
        assert most_above_rgb == 1
        for value in range(256):
            for weights in ([1, 1], [2, 1], [3, 1], [9, 1], [1, 2]):
                colours = ["#000000", grey(value)]
                mixed = channels(mix(colours, weights, "cmy"))
                assert mixed[0] <= rounded_average(colours, weights)[0], (value, weights)

    def test_no_channel_leaves_the_range_of_its_ingredients(self):
        for colours, weights in TRIPLES:
            mixed = channels(mix(colours, weights, "cmy"))
            for i in range(3):
                values = [channels(c)[i] for c in colours]
                assert min(values) <= mixed[i] <= max(values), (colours, weights)

    def test_white_is_no_ink_and_adding_it_only_lightens(self):
        """One part #0000ff in up to ninety-nine of white. The empty red
        channel never falls as white is added, and climbs from 7 to 237."""
        reds = [channels(mix(["white", "#0000ff"], [w, 1], mode="cmy"))[0] for w in range(1, 100)]
        assert reds == sorted(reds)
        assert (reds[0], reds[-1]) == (7, 237)

    def test_how_a_stored_zero_is_read(self, monkeypatch):
        """Five of the claims the comment on CMY_ZERO_REFLECTANCE makes are
        run here. It is half a step over e. That is the model's own mix of
        everything a stored 0 can stand for: the geometric mean of 100,000
        values spread evenly below half a step comes to it within one part in
        a hundred thousand. Two plainer stand-ins put a mix exactly on a
        half, and the exact reference says so when it is given each: a
        quarter of a step, for black + #090909, and the 0.001 of reflectance
        that paint clamps at, for the three inks. And with the smallest
        positive float in its place, white cannot lift #0000ff even at 99:1,
        and the three inks reach #000000."""
        assert ColorMath.CMY_ZERO_REFLECTANCE * 255 == pytest.approx(0.5 / math.e, rel=1e-15)
        spread = [(i + 0.5) * 0.5 / 100_000 for i in range(100_000)]
        mean = math.exp(math.fsum(math.log(value) for value in spread) / len(spread))
        assert mean == pytest.approx(0.5 / math.e, rel=1e-5)
        assert exact_cmy(["#000000", "#090909"]) == ((1, 1, 1), False)
        assert exact_cmy(["cyan", "magenta", "yellow"]) == ((23, 23, 23), False)
        monkeypatch.setattr(sys.modules[__name__], "EXACT_ZERO", Fraction(1, 4))
        assert exact_cmy(["#000000", "#090909"]) == ((2, 2, 2), True)
        monkeypatch.setattr(sys.modules[__name__], "EXACT_ZERO", Fraction(255, 1000))
        assert exact_cmy(["cyan", "magenta", "yellow"]) == ((26, 26, 26), True)
        assert mix(["white", "#0000ff"], [99, 1], mode="cmy") == "#ededff"
        monkeypatch.setattr(ColorMath, "CMY_ZERO_REFLECTANCE", 5e-324)
        assert mix(["white", "#0000ff"], [99, 1], mode="cmy") == "#0000ff"
        assert mix(["cyan", "magenta", "yellow"], mode="cmy") == "#000000"

    def test_a_weight_too_large_for_a_float_still_mixes(self):
        """Each share is one whole number divided by another, so a weight no
        float can hold is still a share."""
        huge = 10 ** 400
        assert mix(BLACK_AND_GOLD, [huge, huge], mode="cmy") == mix(BLACK_AND_GOLD, mode="cmy")
        assert mix(BLACK_AND_GOLD, [1, huge], mode="cmy") == BLACK_AND_GOLD[1]


class TestAColourMixedAlone:
    @pytest.mark.parametrize("mode", EXACT_ALONE)
    def test_rgb_lab_and_cmy_return_it_unchanged(self, mode):
        changed = [value for value in REGISTERED_VALUES if mix([value], mode=mode) != value]
        assert changed == []

    @pytest.mark.parametrize("mode", TRUNCATING_ALONE)
    def test_the_other_three_lose_at_most_one_step_and_never_gain(self, mode):
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

    def test_cmy_on_every_channel_value(self):
        """Measured on every case there is. cmy works one channel at a time,
        so 256 greys cover every 8-bit colour. Each comes back unchanged,
        alone and with its weight split over two entries."""
        for value in range(256):
            assert mix([grey(value)], mode="cmy") == grey(value)
            assert mix([grey(value), grey(value)], [1, 2], mode="cmy") == grey(value)

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
    and a sum can fall either side of an integer. cmy is exact by
    construction: its sum does not depend on the order it is added in, and a
    weight enters only as its share of the total."""

    @pytest.mark.parametrize("mode", ("rgb", "hsv", "lab", "paint", "cmy"))
    def test_order_does_not_change_the_result(self, mode):
        for colours, weights in TRIPLES:
            assert mix(colours, weights, mode) == mix(colours[::-1], weights[::-1], mode)

    def test_order_moves_ryb_by_at_most_one_step(self):
        apart = [steps_apart(mix(c, w, "ryb"), mix(c[::-1], w[::-1], "ryb")) for c, w in TRIPLES]
        assert max(apart) == 1, "exact now? then move the mode to the test above"

    @pytest.mark.parametrize("mode", ("rgb", "lab", "paint", "cmy"))
    def test_scaling_every_weight_does_not_change_the_result(self, mode):
        for colours, weights in TRIPLES:
            assert mix(colours, weights, mode) == mix(colours, [3 * w for w in weights], mode)

    @pytest.mark.parametrize("mode", ("hsv", "ryb"))
    def test_scaling_moves_hsv_and_ryb_by_at_most_one_step(self, mode):
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
