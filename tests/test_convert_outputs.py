"""
What convert_color returns for hsv and hsl, held to the definitions.

Until the change written on 2026-10-06 (US Eastern), convert_color returned
`hsl` as hue, lightness, saturation. The engine's rgb_to_hsl returns Python's
colorsys.rgb_to_hls, and the api passed the triple through under the label
`hsl`. For #ff8000 that was [0.0837, 0.5, 1] to four places; hue, saturation,
lightness is [0.0837, 1, 0.5]. It was a value under a label it did not match,
the same class as color_difference's method label, and nothing in the suite
held an hsl or an hsv value: the smoke script checks that the five names are
present. A reviewer found it on 2026-10-05 while reading for something else.

The fix is at the api seam, and the engine pair is left as it was. The
desktop apps this engine was copied from keep the same pair in the same
order. Here convert_color is the only caller of rgb_to_hsl and nothing calls
hsl_to_rgb, so reordering the engine would make this copy differ from its
source and change nothing a caller of the server sees. The order is a trap
for the next caller all the same: the name says hsl and the triple is hue,
lightness, saturation. TestTheEnginePair pins it, so that changing the
engine alone fails here by name.

These tests do not compare the tool with colorsys, which is what the engine
calls: that would hold the code to itself. `reference` works hsv and hsl from
their definitions in whole numbers and fractions, and TestPositiveControl
holds the reference to four colours worked by hand, one for each branch of
the hue, with lightness below 1/2, above it and on it. Read it first: if it
fails, the reference is wrong and every comparison below proves nothing.

What this file cannot see.
  - A `lab` value worked from its definition. `lab` is held to the engine's
    own rgb_to_lab, so the seam cannot relabel, reorder or reshape it. That
    function is held here at one point, white's L* of 100, and otherwise
    indirectly, by what is built on it: the lab mix pins in
    test_mix_outputs.py above all, the two difference figures pinned in
    test_selector_refusals.py, and the difference and placement contracts
    among others.
  - Colours outside the sample. sample() is 560 of the 16,777,216. A sweep of
    every colour on 2026-10-06, against a reference in whole-number ratios,
    found no component outside 0 to 1 and no gap above 3.5e-15; that sweep is
    not part of the suite.
  - Hue for a grey. The definitions leave it undefined; the tool returns 0
    there, and that is pinned as the convention it is.
  - How hsl_to_rgb rounds. Nothing in the server calls it; only the order of
    its argument is held.
  - Whether a caller reads hue as a fraction of a turn. That is the
    description's to say, and nothing here reads the description.
"""
from __future__ import annotations

from fractions import Fraction

import pytest

import api
from engine.color_math import ColorMath

F = Fraction

#: Four colours worked by hand: (hex, rgb, hsv, hsl). Every channel is a
#: multiple of 51, a whole number of fifths of 255, so the fractions stay
#: short.
#: With max and min the largest and smallest of r, g, b, and chroma their
#: difference:
#:   value = max;  hsv saturation = chroma / max
#:   lightness = (max + min) / 2;  hsl saturation = chroma / (1 - |2L - 1|)
#:   hue, as a fraction of a turn, by which channel is the max:
#:     red    ((g - b) / chroma, taken modulo 6) / 6
#:     green  ((b - r) / chroma + 2) / 6
#:     blue   ((r - g) / chroma + 4) / 6
#:
#: #996633 = 3/5, 2/5, 1/5. Red is the max, g above b, lightness below 1/2.
#:   chroma 2/5. hue (1/2) / 6 = 1/12. value 3/5, hsv s (2/5)/(3/5) = 2/3.
#:   L 2/5, hsl s (2/5)/(4/5) = 1/2.
#: #66cc99 = 2/5, 4/5, 3/5. Green is the max, lightness above 1/2.
#:   chroma 2/5. hue (1/2 + 2) / 6 = 5/12. value 4/5, hsv s (2/5)/(4/5) = 1/2.
#:   L 3/5, hsl s (2/5)/(1 - 1/5) = 1/2.
#: #6699cc = 2/5, 3/5, 4/5. Blue is the max, lightness above 1/2.
#:   chroma 2/5. hue (-1/2 + 4) / 6 = 7/12. value 4/5, hsv s 1/2.
#:   L 3/5, hsl s 1/2.
#: #cc3399 = 4/5, 1/5, 3/5. Red is the max and g is below b, so the hue wraps.
#:   chroma 3/5. (g - b)/chroma = -2/3, modulo 6 is 16/3, hue 8/9.
#:   value 4/5, hsv s (3/5)/(4/5) = 3/4. L 1/2, hsl s (3/5)/1 = 3/5.
HAND_WORKED = [
    ("#996633", (153, 102, 51), (F(1, 12), F(2, 3), F(3, 5)), (F(1, 12), F(1, 2), F(2, 5))),
    ("#66cc99", (102, 204, 153), (F(5, 12), F(1, 2), F(4, 5)), (F(5, 12), F(1, 2), F(3, 5))),
    ("#6699cc", (102, 153, 204), (F(7, 12), F(1, 2), F(4, 5)), (F(7, 12), F(1, 2), F(3, 5))),
    ("#cc3399", (204, 51, 153), (F(8, 9), F(3, 4), F(4, 5)), (F(8, 9), F(3, 5), F(1, 2))),
]
HAND, HAND_RGB, HAND_HSV, HAND_HSL = HAND_WORKED[0]

#: The colour the defect was reported with. Hue is (128/255) / 6 = 64/765.
REPORTED = "#ff8000"
REPORTED_HSL = (F(64, 765), F(1), F(1, 2))

#: Floats against exact fractions. Over every 8-bit colour the largest gap
#: measured on 2026-10-06 was 3.5e-15, in hsl saturation for a near-white
#: (251, 251, 252), which is in the sample; that is a measurement of this
#: engine on Python 3.13 and no bound. 1e-13 is about 29 times it, and small
#: enough that a result rounded to 12 places fails.
CLOSE = 1e-13


def reference(rgb):
    """(hsv, hsl) for an 8-bit colour, from the definitions, in fractions.

    Hue is a fraction of a turn. For a grey it is undefined and given as 0,
    with saturation 0, which is the convention the tool follows."""
    r, g, b = (F(c, 255) for c in rgb)
    high, low = max(r, g, b), min(r, g, b)
    chroma = high - low
    if chroma == 0:
        hue = F(0)
    elif high == r:
        hue = ((g - b) / chroma % 6) / 6
    elif high == g:
        hue = ((b - r) / chroma + 2) / 6
    else:
        hue = ((r - g) / chroma + 4) / 6
    value = high
    lightness = (high + low) / 2
    hsv_saturation = chroma / high if high else F(0)
    hsl_saturation = chroma / (1 - abs(2 * lightness - 1)) if chroma else F(0)
    return (hue, hsv_saturation, value), (hue, hsl_saturation, lightness)


def sample():
    """560 colours, made by arithmetic so that no library's random stream is
    part of the test:
      - the 216 on the grid of 0, 51, ... 255, which holds the greys, the
        primaries and every tie between channels;
      - 216 off the grid;
      - 126 near-greys, one channel 1 to 7 steps above the other two, where
        the divisions are by the smallest numbers;
      - the two colours at which a sweep of every colour found the largest
        float gaps in saturation and in hue."""
    steps = range(0, 256, 51)
    grid = [(r, g, b) for r in steps for g in steps for b in steps]
    off = [(i * 37 % 256, i * 101 % 256, i * 59 % 256) for i in range(1, 217)]
    near_grey = [colour
                 for base in (1, 64, 127, 128, 200, 247)
                 for k in range(1, 8)
                 for colour in ((base + k, base, base), (base, base + k, base), (base, base, base + k))]
    return grid + off + near_grey + [(251, 251, 252), (130, 132, 131)]


def as_hex(rgb):
    return "#%02x%02x%02x" % rgb


def floats(fractions):
    return [float(x) for x in fractions]


class TestPositiveControl:
    """If this fails, the reference or the sample is wrong, not the tool."""

    @pytest.mark.parametrize("name, rgb, hsv, hsl", HAND_WORKED)
    def test_the_reference_gives_each_hand_worked_colour_exactly(self, name, rgb, hsv, hsl):
        assert as_hex(rgb) == name
        assert reference(rgb) == (hsv, hsl)

    def test_the_hand_worked_colours_reach_every_branch_of_the_reference(self):
        """One colour for each way the hue is worked, and lightness on both
        sides of 1/2 and on it, where hsl saturation changes its divisor."""
        tops = set()
        for _, (r, g, b), _, (_, _, lightness) in HAND_WORKED:
            high = max(r, g, b)
            tops.add(("red, wrapped" if g < b else "red") if high == r
                     else "green" if high == g else "blue")
        assert tops == {"red", "red, wrapped", "green", "blue"}
        sides = {(l > F(1, 2)) - (l < F(1, 2)) for *_, (_, _, l) in HAND_WORKED}
        assert sides == {-1, 0, 1}

    def test_the_reference_gives_the_reported_colour_exactly(self):
        assert reference((255, 128, 0))[1] == REPORTED_HSL

    def test_the_two_orders_can_be_told_apart(self):
        """The control for every hsl comparison below: for each hand colour
        and for most of the sample, saturation and lightness differ by far
        more than the tolerance, so a triple in the other order cannot
        pass."""
        for name, _, _, (_, saturation, lightness) in HAND_WORKED:
            assert abs(saturation - lightness) >= F(1, 10), name
        apart = [rgb for rgb in sample()
                 if abs(reference(rgb)[1][1] - reference(rgb)[1][2]) > F(1, 20)]
        assert len(apart) > 500, len(apart)

    def test_the_sample_is_the_size_it_says_and_reaches_the_edges(self):
        colours = sample()
        assert len(colours) == 560 == len(set(colours))
        for edge in [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0),
                     (0, 0, 255), (255, 255, 0), (102, 102, 102)]:
            assert edge in colours, edge
        chroma = lambda rgb: max(rgb) - min(rgb)
        assert {chroma(rgb) for rgb in colours} >= set(range(0, 8)), "near-greys are missing"


class TestHsl:
    @pytest.mark.parametrize("name, rgb, hsv, hsl", HAND_WORKED)
    def test_each_hand_worked_colour_is_hue_saturation_lightness(self, name, rgb, hsv, hsl):
        assert api.convert_color(name)["hsl"] == pytest.approx(floats(hsl), abs=CLOSE)

    def test_the_reported_colour_is_hue_saturation_lightness(self):
        """This came back [0.0837, 0.5, 1] to four places."""
        assert api.convert_color(REPORTED)["hsl"] == pytest.approx(floats(REPORTED_HSL), abs=CLOSE)

    def test_every_sampled_colour_matches_the_definition(self):
        for rgb in sample():
            _, expected = reference(rgb)
            got = api.convert_color(as_hex(rgb))["hsl"]
            assert got == pytest.approx(floats(expected), abs=CLOSE), (rgb, got)


class TestHsv:
    @pytest.mark.parametrize("name, rgb, hsv, hsl", HAND_WORKED)
    def test_each_hand_worked_colour_is_hue_saturation_value(self, name, rgb, hsv, hsl):
        assert api.convert_color(name)["hsv"] == pytest.approx(floats(hsv), abs=CLOSE)

    def test_every_sampled_colour_matches_the_definition(self):
        for rgb in sample():
            expected, _ = reference(rgb)
            got = api.convert_color(as_hex(rgb))["hsv"]
            assert got == pytest.approx(floats(expected), abs=CLOSE), (rgb, got)

    def test_hsv_and_hsl_are_two_different_triples(self):
        """They share a hue and nothing else, so one cannot stand in for the
        other."""
        out = api.convert_color(HAND)
        assert out["hsv"][0] == out["hsl"][0]
        assert out["hsv"][1:] != pytest.approx(out["hsl"][1:], abs=0.05)


class TestEachFormatAlone:
    """Asking for one format returns that format's value and no other's.
    Without this, `to="hsv"` could hand back the hsl triple under the hsv
    label with every test above green: they read the all-formats result."""

    COLOURS = [name for name, *_ in HAND_WORKED] + [REPORTED, "#fbfbfc", "brand gold"]

    def test_the_five_values_of_a_colour_are_five_different_values(self):
        """The control: for these colours no two formats hold the same value,
        so a format answered with another's value cannot pass below."""
        for colour in self.COLOURS:
            values = [repr(v) for v in api.convert_color(colour).values()]
            assert len(values) == 5 == len(set(values)), (colour, values)

    def test_each_format_alone_is_the_value_the_full_result_holds(self):
        for colour in self.COLOURS:
            every = api.convert_color(colour)
            for name in every:
                assert api.convert_color(colour, to=name) == {name: every[name]}, (colour, name)

    def test_a_folded_name_is_answered_with_its_own_format_too(self):
        """Capitals and outer spaces are folded before the lookup, so a name
        written that way has to reach the same value as the name itself."""
        for colour in self.COLOURS:
            every = api.convert_color(colour)
            for name in every:
                for written in (name.upper(), name.capitalize(), f"  {name} ", f"\t{name.upper()}\n"):
                    assert api.convert_color(colour, to=written) == {name: every[name]}, (colour, written)


class TestShape:
    def test_every_component_is_a_fraction_from_0_to_1(self):
        for rgb in sample():
            out = api.convert_color(as_hex(rgb))
            for name in ("hsv", "hsl"):
                assert len(out[name]) == 3
                assert all(0.0 <= x <= 1.0 for x in out[name]), (rgb, name, out[name])

    def test_the_types_are_the_ones_a_client_is_sent(self):
        """hex a string, rgb three whole numbers, hsv, hsl and lab three
        floats each, every triple a list."""
        for colour in (HAND, "#000000", "#ffffff", REPORTED):
            out = api.convert_color(colour)
            assert type(out["hex"]) is str
            assert type(out["rgb"]) is list and [type(x) for x in out["rgb"]] == [int] * 3
            for name in ("hsv", "hsl", "lab"):
                assert type(out[name]) is list, (colour, name)
                assert [type(x) for x in out[name]] == [float] * 3, (colour, name, out[name])

    def test_a_grey_has_hue_0_and_saturation_0(self):
        """Pinned as a convention: hue has no value for a grey."""
        for grey in ("#000000", "#808080", "#ffffff"):
            out = api.convert_color(grey)
            assert out["hsl"][:2] == [0.0, 0.0] and out["hsv"][:2] == [0.0, 0.0], (grey, out)

    def test_hex_and_rgb_are_the_colour_that_went_in(self):
        for name, rgb, _, _ in HAND_WORKED:
            out = api.convert_color(name)
            assert (out["hex"], out["rgb"]) == (name, list(rgb))

    def test_lab_is_the_engines_own_value_unchanged(self):
        """Held to the engine and not to the definition: see the module
        docstring. The seam cannot reorder it or answer with another triple."""
        for rgb in sample():
            assert api.convert_color(as_hex(rgb))["lab"] == list(ColorMath.rgb_to_lab(rgb)), rgb
        lightness = api.convert_color("#ffffff")["lab"][0]
        assert lightness == pytest.approx(100.0, abs=0.01), "white is L* 100 in any lab"


class TestTheEnginePair:
    """The engine's own order, pinned so that it moves on purpose or not at
    all. See the module docstring for why it is left."""

    def test_rgb_to_hsl_returns_hue_lightness_saturation(self):
        hue, saturation, lightness = HAND_HSL
        assert ColorMath.rgb_to_hsl(HAND_RGB) == pytest.approx(
            (float(hue), float(lightness), float(saturation)), abs=CLOSE)

    def test_hsl_to_rgb_takes_the_order_rgb_to_hsl_returns(self):
        """The two are a pair. Each sampled colour comes back within one step
        a channel; in the other order most would not come back at all. How
        hsl_to_rgb rounds is not held here."""
        for rgb in sample():
            back = ColorMath.hsl_to_rgb(ColorMath.rgb_to_hsl(rgb))
            assert max(abs(a - b) for a, b in zip(rgb, back)) <= 1, (rgb, back)

    def test_the_pair_in_the_other_order_does_not_come_back(self):
        """The control for the test above: it can fail."""
        hue, lightness, saturation = ColorMath.rgb_to_hsl(HAND_RGB)
        back = ColorMath.hsl_to_rgb((hue, saturation, lightness))
        assert max(abs(a - b) for a, b in zip(HAND_RGB, back)) > 10, back
