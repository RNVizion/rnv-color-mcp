"""
Phase 1 smoke test: prove the extracted engine + store run standalone (no Qt, no GUI),
and that every api function and all six mix modes behave.

Run from repo root:  python tests/smoke_test.py

ISOLATED FROM PRODUCTION DATA. The palette store reads HF_TOKEN at construction, and a
Codespace carries one; before 2026-09-27 each temporary store below would have hydrated
from the production Dataset and pushed its "Spring line" saves back over it. The token
is now removed and the default store pointed at a throwaway path before `api` is
imported -- the same two lines tests/conftest.py uses.

The setup runs only under __main__, and `api` is imported inside main(): pytest's
default glob matches *_test.py, so this module is imported at collection, and mutating
the environment there would change the suite's own configuration.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BRAND_NEAR_BLACK = "#1a1a1a"  # canonical brand black (charcoal)
BRAND_GOLD = "#d2bc93"


def _isolate_from_production() -> None:
    os.environ["RNV_PALETTE_STORE"] = os.path.join(
        tempfile.mkdtemp(prefix="rnv-smoke-"), "palettes.json"
    )
    os.environ.pop("HF_TOKEN", None)


def main() -> None:
    import api
    from engine.palette_store import PaletteStore

    assert not api._store.hf_token, "smoke run is holding an HF token; refusing to touch the Dataset"
    failures = []

    # 1. mix_colors across all six modes
    print("mix_colors — all six modes:")
    for mode in ["rgb", "hsv", "lab", "paint", "ryb", "cmy"]:
        out = api.mix_colors([BRAND_NEAR_BLACK, BRAND_GOLD], mode=mode)
        assert out["hex"].startswith("#") and len(out["hex"]) == 7, f"bad hex in {mode}"
        print(f"  {mode:5} -> {out['hex']}")

    # weighted mix (mostly gold)
    w = api.mix_colors([BRAND_NEAR_BLACK, BRAND_GOLD], weights=[1, 4], mode="lab")
    print(f"  weighted [1,4] lab -> {w['hex']}")

    # 2. convert_color (all formats + single format)
    conv = api.convert_color(BRAND_GOLD)
    assert set(conv) == {"hex", "rgb", "hsv", "hsl", "lab"}, "convert missing formats"
    one = api.convert_color(BRAND_GOLD, to="rgb")
    print(f"convert_color {BRAND_GOLD} -> rgb {one['rgb']}")

    # 2b. place_lightness: the register's blue pair, rebuilt from its mix
    placed = [p["hex"] for p in api.place_lightness("#5c82a9", [60.16, 44.17])["placements"]]
    assert placed == ["#6f94bc", "#456c91"], f"blue pair did not reproduce: {placed}"
    print(f"place_lightness #5c82a9 @ L* 60.16 / 44.17 -> {placed}")

    # 3. generate_harmony across schemes
    print("generate_harmony:")
    for scheme in ["complementary", "analogous", "triadic",
                   "split-complementary", "tetradic", "monochromatic", "compound"]:
        colors = api.generate_harmony(BRAND_GOLD, scheme)
        assert isinstance(colors, list) and colors, f"empty harmony for {scheme}"
        print(f"  {scheme:20} -> {colors}")

    # 4. transform_text across the 11 operations
    print("transform_text:")
    for op in ["UPPERCASE", "lowercase", "Title Case", "Sentence case",
               "camelCase", "PascalCase", "snake_case", "CONSTANT_CASE",
               "kebab-case", "dot.case", "iNVERTED cASE"]:
        r = api.transform_text("the honest machine", op)["result"]
        print(f"  {op:15} -> {r}")

    # 5. palette store round-trip (isolated temp file)
    with tempfile.TemporaryDirectory() as d:
        store = PaletteStore(Path(d) / "palettes.json")
        api._store = store  # point the API at the temp store for this test
        api.save_palette("Spring line", [BRAND_NEAR_BLACK, BRAND_GOLD], notes="launch palette")
        listed = api.list_palettes()
        got = api.get_palette("Spring line")
        assert any(p["name"] == "Spring line" for p in listed), "palette not listed"
        assert got and got["colors"] == [BRAND_NEAR_BLACK, BRAND_GOLD], "round-trip mismatch"
        assert got["metadata"]["author"] == "RNVizion", "author default missing"
        assert got["metadata"]["description"] == "launch palette", "notes->description failed"
        print(f"palette round-trip -> {got['name']} {got['colors']} "
              f"(author={got['metadata']['author']})")

    # 6. the fashion composition: get_palette -> generate_harmony
    with tempfile.TemporaryDirectory() as d:
        api._store = PaletteStore(Path(d) / "palettes.json")
        api.save_palette("Spring line", [BRAND_GOLD])
        base = api.get_palette("Spring line")["colors"][0]
        accents = api.generate_harmony(base, "complementary")
        print(f"compose (get->harmony) -> base {base} accents {accents}")

    # 7. plain-language resolution: CSS names, RNV brand, palette refs, refusal
    print("name resolution:")
    # "blue" is RNV blue (#6f94bc), not CSS blue: brand names win on collision,
    # and css:blue forces the universal one.
    rb = api.mix_colors(["red", "css:blue"], mode="rgb")
    print(f"  mix red + css:blue (rgb)    -> {rb['hex']}")
    assert api.convert_color("blue", to="hex")["hex"] == "#6f94bc", "'blue' should be RNV blue"
    bg = api.convert_color("brand gold", to="hex")
    assert bg["hex"] == BRAND_GOLD, "RNV 'brand gold' should be #d2bc93"
    print(f"  convert 'brand gold'        -> {bg['hex']}")
    d = api.color_difference("brand gold", "dark gold")
    assert d["delta_e"] > 0, "distinct colors should differ"
    print(f"  color_difference(gold, dark gold)  -> dE {d['delta_e']}")
    c = api.contrast_check("brand gold", "near-black")
    assert c["ratio"] > 1 and c["wcag"]["AA_normal_text"], "gold on near-black should pass AA"
    print(f"  contrast_check(gold/near-black)    -> {c['display']} AA={c['wcag']['AA_normal_text']}")
    nb = api.convert_color("near-black", to="hex")
    assert nb["hex"] == BRAND_NEAR_BLACK, "RNV 'near-black' should be #1a1a1a"
    print(f"  convert 'near-black'        -> {nb['hex']}")
    # RNV layer beats CSS: bare 'gold' is RNV gold, 'css:gold' forces universal
    assert api.convert_color("gold", to="hex")["hex"] == BRAND_GOLD, "'gold' should be RNV"
    assert api.convert_color("css:gold", to="hex")["hex"] == "#ffd700", "'css:gold' should be CSS"
    print(f"  'gold' (RNV) vs 'css:gold'  -> {api.convert_color('gold')['hex']} vs "
          f"{api.convert_color('css:gold')['hex']}")
    # harmony from a brand name and from a saved-palette reference
    with tempfile.TemporaryDirectory() as d:
        api._store = PaletteStore(Path(d) / "palettes.json")
        api.save_palette("Spring line", [BRAND_NEAR_BLACK, BRAND_GOLD, "#ffffff"])
        h_name = api.generate_harmony("brand gold", "complementary")
        h_ref = api.generate_harmony("Spring line:2", "complementary")  # 2nd swatch = gold
        print(f"  harmony 'brand gold'        -> {h_name}")
        print(f"  harmony 'Spring line:2'     -> {h_ref}")
        assert h_name == h_ref, "brand gold and Spring line's 2nd swatch should match"
    # refusal: an unknown token is refused, not guessed
    from engine.resolve import UnknownColor
    try:
        api.convert_color("definitely-not-a-color")
        failures.append("expected UnknownColor for unknown token")
    except UnknownColor:
        print("  unknown token              -> refused (UnknownColor), not guessed")

    if failures:
        print("\nFAILURES:", failures)
        sys.exit(1)
    print("\nAll checks passed. Engine + store run Qt-free.")


if __name__ == "__main__":
    _isolate_from_production()
    main()
