"""
resolve_color, asserted directly: the layer every colour input passes through.

Every tool that takes a colour calls engine.resolve.resolve_color, so nearly
every test file exercises it, and until 2026-09-30 none asserted it as a unit.
Its contract is the module docstring: a hex literal, then a saved palette, then
an RNV brand name, then a CSS name, then a refusal; "css:" forces the CSS
layer. This file holds the resolver to that contract, layer by layer and in
order, and holds the vocabulary to the one property the resolver needs of it:
every registered name is reachable.

REACHABILITY IS THE BRAND RULING, EXECUTABLE. A registered colour is permanent
and answers to every name it was registered under (Build Runbook, decisions
log, 2026-09-13). The resolver strips and lowercases the token and tries the
hex layer first, so a brand key that carried a capital or a space, read as a
hex literal ("ace", "decade"), or contained ":" would be registered and
unreachable, and the mirror would copy it in faithfully. Nothing else here
could see that: test_brand_mirror.py holds the mirror to its pin, not to the
resolver.

THE ORDER IS A CONTRACT OTHER CODE DEPENDS ON. api.save_palette refuses a
palette name that is a brand key, a CSS name or a hex literal because palettes
resolve before brand and CSS names and after hex literals. TestOrderOfLayers
writes a store file directly, the way a store written before 2026-09-27 could
hold it, so the order can be seen with palettes the write path would now
refuse.

What this file cannot see, and who can:
  - whether a brand value is RIGHT: test_brand_mirror.py against the pin,
    scripts/check_brand_currency.py against upstream;
  - how a refusal reaches a caller through a tool: test_palette_contract.py
    and test_selector_refusals.py;
  - the MCP layer's own type checks before a token reaches the resolver;
  - spellings nobody registered. Aliases are literal, so "light mode gold"
    refuses while "light-mode gold" resolves. TestAliasesAreLiteral pins that,
    so the parked normalization (Build Runbook, Deferred) moves it on purpose.

TestPositiveControl is the diagnostic: one token per layer resolves and a
nonsense token refuses. If it fails, the harness is wrong, not the resolver.
"""
from __future__ import annotations

import json

import pytest

from engine.palette_store import PaletteStore
from engine.resolve import CSS_NAMES, RNV_BRAND, UnknownColor, normalize_hex, resolve_color

# The names on which the brand layer and the CSS layer disagree, computed from
# the two tables rather than transcribed, so a new collision joins every test
# below the day it is mirrored.
COLLISIONS = sorted(k for k in RNV_BRAND if k in CSS_NAMES and RNV_BRAND[k] != CSS_NAMES[k])

ACCEPTED_KINDS = ("a hex", "a CSS name", "an RNV brand name", "a saved palette reference")


def store_holding(tmp_path, palettes: dict[str, list[str]]) -> PaletteStore:
    """A real PaletteStore over a file written directly, bypassing the write
    path, so it can hold names and colours save_palette would refuse today."""
    path = tmp_path / "palettes.json"
    path.write_text(json.dumps({
        name: {"colors": colors, "metadata": {}} for name, colors in palettes.items()
    }), encoding="utf-8")
    return PaletteStore(path)


@pytest.fixture
def spring(tmp_path):
    return store_holding(tmp_path, {"Spring line": ["#1a1a1a", "#d2bc93"]})


class TestPositiveControl:
    """If this fails, the harness or an import is wrong, not the resolver."""

    def test_one_token_per_layer_resolves(self, spring):
        assert resolve_color("#D2BC93") == "#d2bc93"
        assert resolve_color("Spring line:2", spring) == "#d2bc93"
        assert resolve_color("brand gold") == RNV_BRAND["brand gold"]
        assert resolve_color("rebeccapurple") == "#663399"

    def test_a_nonsense_token_is_refused(self):
        with pytest.raises(UnknownColor):
            resolve_color("not-a-colour-at-all")

    def test_the_collision_set_is_what_the_documents_say(self):
        # Computed above; checked once against the set the README, the server's
        # instructions and the register name, so the tests below are exercising
        # something real and not an empty list.
        assert COLLISIONS == ["blue", "gold", "teal"]


class TestOrderOfLayers:
    def test_a_hex_literal_answers_before_a_palette(self, tmp_path):
        # "abc" reads as #aabbcc, so a palette by that name is unreachable; that
        # is why save_palette refuses hex-shaped names.
        s = store_holding(tmp_path, {"abc": ["#123456"]})
        assert resolve_color("abc", s) == "#aabbcc"

    def test_a_palette_answers_before_a_brand_name(self, tmp_path):
        # The reason save_palette refuses brand keys: a palette named "gold"
        # would redefine gold for every caller.
        s = store_holding(tmp_path, {"gold": ["#123456"]})
        assert resolve_color("gold", s) == "#123456"
        assert resolve_color("gold") == RNV_BRAND["gold"]

    # A brand name answering before a CSS name is TestCssEscape's collision
    # test: each collision resolves to the brand value bare, the CSS one with
    # the prefix.

    def test_css_prefix_answers_before_everything(self, tmp_path):
        s = store_holding(tmp_path, {"css:gold": ["#123456"]})
        assert resolve_color("css:gold", s) == CSS_NAMES["gold"]

    def test_without_a_store_the_palette_layer_is_skipped(self):
        with pytest.raises(UnknownColor):
            resolve_color("Spring line")


class TestCssEscape:
    def test_every_css_name_is_reachable_through_the_prefix(self):
        wrong = {n: resolve_color(f"css:{n}") for n in CSS_NAMES
                 if resolve_color(f"css:{n}") != CSS_NAMES[n]}
        assert not wrong

    @pytest.mark.parametrize("name", COLLISIONS)
    def test_every_collision_has_both_values(self, name):
        assert resolve_color(name) == RNV_BRAND[name]
        assert resolve_color(f"css:{name}") == CSS_NAMES[name]

    def test_the_prefix_ignores_case_and_spacing(self):
        assert resolve_color("CSS: Gold ") == CSS_NAMES["gold"]

    @pytest.mark.parametrize("token", ["css:brand gold", "css:#fff", "css:"])
    def test_the_prefix_never_falls_through_to_another_layer(self, token):
        with pytest.raises(UnknownColor) as exc:
            resolve_color(token)
        assert "Unknown CSS color" in str(exc.value)


class TestHexLayer:
    @pytest.mark.parametrize("token, expected", [
        ("D2BC93", "#d2bc93"),
        ("#FFF", "#ffffff"),
        ("fff", "#ffffff"),
        ("  #0a0a0f  ", "#0a0a0f"),
    ])
    def test_accepted_forms_normalize(self, token, expected):
        assert resolve_color(token) == expected

    @pytest.mark.parametrize("token", [
        "#d2bc93ff",          # CSS alpha form: refused, never truncated to #d2bc93
        "#abcd",              # CSS short alpha form
        "#12345g",
        "rgb(210, 188, 147)",
    ])
    def test_other_forms_are_refused_by_name(self, token):
        with pytest.raises(UnknownColor) as exc:
            resolve_color(token)
        assert repr(token) in str(exc.value)


class TestEveryRegisteredNameIsReachable:
    def test_every_brand_key_resolves_to_its_value_in_any_case(self):
        wrong = {}
        for key, value in RNV_BRAND.items():
            for spelling in (key, key.upper(), f"  {key.title()}  "):
                got = resolve_color(spelling)
                if got != value:
                    wrong[spelling] = (got, value)
        assert not wrong

    def test_no_name_has_a_shape_the_resolver_cannot_reach(self):
        # A key must survive strip().lower() unchanged, must not read as a hex
        # literal (the hex layer answers first), must not start with "css:" (the
        # escape answers first), and must not contain ":", which a palette
        # reference splits on.
        def unreachable(name):
            return (name != name.strip().lower() or normalize_hex(name) is not None
                    or ":" in name)
        assert not [k for k in RNV_BRAND if unreachable(k)]
        assert not [k for k in CSS_NAMES if unreachable(k)]

    def test_every_value_is_already_in_the_form_the_resolver_returns(self):
        # The hex layer normalizes; a table value in another form would make the
        # same colour compare unequal depending on how it was named.
        assert not {k: v for k, v in RNV_BRAND.items() if normalize_hex(v) != v}
        assert not {k: v for k, v in CSS_NAMES.items() if normalize_hex(v) != v}


class TestPaletteReferences:
    @pytest.mark.parametrize("token, expected", [
        ("Spring line", "#1a1a1a"),       # the bare name is the first swatch
        ("Spring line:1", "#1a1a1a"),
        ("Spring line:2", "#d2bc93"),
        ("Spring line: 2", "#d2bc93"),
        ("Spring line:", "#1a1a1a"),      # an empty index is the first swatch
    ])
    def test_a_reference_selects_a_swatch(self, spring, token, expected):
        assert resolve_color(token, spring) == expected

    def test_a_palette_name_is_matched_exactly(self, spring):
        # The store keys palettes by the name they were saved under; brand and
        # CSS names are case-folded, palette names are not.
        with pytest.raises(UnknownColor):
            resolve_color("spring line", spring)

    @pytest.mark.parametrize("token", [
        "Spring line:0", "Spring line:3", "Spring line:x",
    ])
    def test_a_swatch_that_does_not_exist_is_refused_with_the_range(self, spring, token):
        # A swatch number is a selector, so the refusal gives the valid choices.
        # Before 2026-09-30 it fell through to the brand and CSS layers and came
        # back as "Don't know the color", which never said the palette existed.
        with pytest.raises(UnknownColor) as exc:
            resolve_color(token, spring)
        message = str(exc.value)
        assert repr(token) in message
        assert "Palette 'Spring line' has 2 swatches: 'Spring line:1' through 'Spring line:2'." in message
        assert "Don't know the color" not in message

    def test_a_one_swatch_palette_names_its_only_reference(self, tmp_path):
        s = store_holding(tmp_path, {"Solo": ["#0a0a0f"]})
        with pytest.raises(UnknownColor) as exc:
            resolve_color("Solo:2", s)
        assert "Palette 'Solo' has 1 swatch: 'Solo:1'." in str(exc.value)

    def test_a_palette_with_no_swatches_is_refused_by_name(self, tmp_path):
        s = store_holding(tmp_path, {"Empty": []})
        with pytest.raises(UnknownColor) as exc:
            resolve_color("Empty", s)
        assert "palette 'Empty' has no swatches" in str(exc.value)


class TestRefusal:
    @pytest.mark.parametrize("token", ["", "   ", None])
    def test_an_empty_token_is_refused_as_empty(self, token):
        with pytest.raises(UnknownColor) as exc:
            resolve_color(token)
        assert str(exc.value) == "Empty color token."

    def test_the_refusal_is_a_value_error(self):
        # api's callers and save_palette's position wrapper catch ValueError.
        assert issubclass(UnknownColor, ValueError)

    def test_the_refusal_names_the_token_as_given_and_what_is_accepted(self):
        with pytest.raises(UnknownColor) as exc:
            resolve_color("  Brand Chartreuse ")
        message = str(exc.value)
        assert "'Brand Chartreuse'" in message
        missing = [kind for kind in ACCEPTED_KINDS if kind not in message]
        assert not missing, (missing, message)


class TestAliasesAreLiteral:
    """Pins today's behaviour so the parked alias normalization moves it on
    purpose. The README writes `royalblue` because `royal blue` refuses."""

    @pytest.mark.parametrize("registered, unregistered", [
        ("light-mode gold", "light mode gold"),
        ("royalblue", "royal blue"),
    ])
    def test_only_the_registered_spelling_resolves(self, registered, unregistered):
        resolve_color(registered)
        with pytest.raises(UnknownColor):
            resolve_color(unregistered)
