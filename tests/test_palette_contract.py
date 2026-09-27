"""
Palette write-path contract: the store only ever holds what the resolver can serve.

Two defects, one write path, found 2026-09-27:

1. save_palette stored whatever it was handed. The live store held a palette
   whose swatches read 'Purple' and 'Green'; referencing one failed with
   `invalid literal for int() with base 16: 'Pu'` -- no reason, no location.
   Now every colour is resolved through the same resolver as the other tools
   and stored as normalized hex; an unknown token refuses the save naming its
   position; and a malformed swatch already in the store refuses by palette,
   position and value instead of leaking arithmetic.

2. Saved palettes resolve ahead of brand and CSS names, and the public
   endpoint runs auth-off, so one save_palette("brand gold", ["#ff0000"]) made
   `brand gold` red for every caller, durably. The write path now refuses a
   name that is a brand key, a CSS name, a `css:` form, a hex literal, or
   contains ':' -- each with its reason. Resolution order is unchanged.

TestPositiveControl is the diagnostic: a plain hex round-trip through an
isolated store. If it fails, the fixture or the store is wrong and nothing
below is evidence.
"""
from __future__ import annotations

import json

import pytest

import api
from engine.palette_store import PaletteStore
from engine.resolve import UnknownColor, resolve_color


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A fresh, isolated, local-only store wired into the api for one test."""
    s = PaletteStore(tmp_path / "palettes.json")
    monkeypatch.setattr(api, "_store", s)
    return s


class TestPositiveControl:
    def test_hex_round_trip(self, store):
        r = api.save_palette("Spring line", ["#0a0a0f", "#d2bc93"], notes="launch")
        assert r.colors == ["#0a0a0f", "#d2bc93"]
        assert r.overwritten is False
        assert api.get_palette("Spring line")["colors"] == ["#0a0a0f", "#d2bc93"]
        assert api.convert_color("Spring line:2", to="hex") == {"hex": "#d2bc93"}


class TestColorsAreResolvedAndNormalized:
    def test_shorthand_and_case_are_normalized(self, store):
        r = api.save_palette("short", ["#FFF", "D2BC93", "#0A0A0F"])
        assert r.colors == ["#ffffff", "#d2bc93", "#0a0a0f"]
        assert api.get_palette("short")["colors"] == ["#ffffff", "#d2bc93", "#0a0a0f"]

    def test_names_resolve_like_every_other_tool(self, store):
        r = api.save_palette("named", ["brand gold", "css:gold", "red", "near-black"])
        assert r.colors == ["#d2bc93", "#ffd700", "#ff0000", "#1a1a1a"]

    def test_a_palette_reference_is_a_snapshot(self, store):
        api.save_palette("A", ["#d2bc93"])
        api.save_palette("B", ["A:1"])
        assert api.get_palette("B")["colors"] == ["#d2bc93"]
        api.save_palette("A", ["#000000"])  # overwrite the source
        assert api.get_palette("B")["colors"] == ["#d2bc93"], "B must hold the value, not the reference"

    def test_unknown_token_refuses_the_whole_save_naming_its_position(self, store):
        with pytest.raises(ValueError) as exc:
            api.save_palette("junk", ["#d2bc93", "banana"])
        assert "colors[2] 'banana'" in str(exc.value)
        assert api.get_palette("junk") is None, "a refused save must write nothing"

    def test_the_production_case(self, store):
        """What the live store's 'Test Colors' would have been, had the write
        path resolved: names become hex and the palette becomes servable."""
        r = api.save_palette("Test Colors", ["#d2bc93", "Purple", "#0a0a0f", "Green"])
        assert r.colors == ["#d2bc93", "#800080", "#0a0a0f", "#008000"]
        assert api.convert_color("Test Colors:2", to="hex") == {"hex": "#800080"}


class TestMalformedStoredSwatchRefusesByName:
    """A palette written before the write path validated, simulated by writing
    the file the store reads, exactly as the pre-fix store would have left it."""

    @pytest.fixture
    def legacy_store(self, tmp_path, monkeypatch):
        path = tmp_path / "palettes.json"
        path.write_text(json.dumps({
            "Test Colors": {"colors": ["#d2bc93", "Purple", "#0a0a0f", "Green"], "metadata": {}},
        }), encoding="utf-8")
        s = PaletteStore(path)
        monkeypatch.setattr(api, "_store", s)
        return s

    def test_a_good_swatch_in_the_same_palette_still_resolves(self, legacy_store):
        """Control: the refusal is per swatch, not per palette."""
        assert resolve_color("Test Colors:1", legacy_store) == "#d2bc93"
        assert resolve_color("Test Colors", legacy_store) == "#d2bc93"

    def test_the_malformed_swatch_is_refused_with_palette_position_and_value(self, legacy_store):
        with pytest.raises(UnknownColor) as exc:
            resolve_color("Test Colors:2", legacy_store)
        message = str(exc.value)
        assert "'Test Colors'" in message and "swatch 2" in message and "'Purple'" in message
        assert "int()" not in message and "base 16" not in message

    def test_every_tool_surfaces_the_named_refusal(self, legacy_store):
        for call in (
            lambda: api.convert_color("Test Colors:4"),
            lambda: api.mix_colors(["Test Colors:2", "#000000"]),
            lambda: api.contrast_check("Test Colors:2", "#ffffff"),
            lambda: api.place_lightness("Test Colors:4", [50.0]),
        ):
            with pytest.raises(UnknownColor) as exc:
                call()
            assert "is not a hex color" in str(exc.value)

    def test_resaving_the_palette_repairs_it(self, legacy_store):
        api.save_palette("Test Colors", ["#d2bc93", "Purple", "#0a0a0f", "Green"])
        assert api.convert_color("Test Colors:2", to="hex") == {"hex": "#800080"}


class TestReservedNames:
    @pytest.mark.parametrize("name, why", [
        ("brand gold", "RNV brand name"),
        ("Blue", "RNV brand name"),          # case-folded: 'blue' is a brand key
        ("rebeccapurple", "CSS color name"),
        ("css:gold", "'css:' namespace"),
        ("#fff", "hex literal"),
        ("d2bc93", "hex literal"),
        ("Spring:line", "swatch-index separator"),
    ])
    def test_reserved_name_is_refused_with_its_reason(self, store, name, why):
        with pytest.raises(ValueError) as exc:
            api.save_palette(name, ["#d2bc93"])
        assert why in str(exc.value), str(exc.value)
        assert api.get_palette(name) is None

    def test_a_refused_name_cannot_shadow_the_brand(self, store):
        with pytest.raises(ValueError):
            api.save_palette("brand gold", ["#ff0000"])
        assert api.convert_color("brand gold", to="hex") == {"hex": "#d2bc93"}

    def test_the_names_already_in_production_are_all_allowed(self, store):
        """Control: the rule is not over-broad. Every palette the live store
        held on 2026-09-27 must still be storable."""
        for name in ("Spring line", "Spring line - Outerwear Accents", "Test Colors",
                     "Check", "test", "rnv-token-check", "scope-test"):
            api.save_palette(name, ["#d2bc93"])
            assert api.get_palette(name) is not None, name
