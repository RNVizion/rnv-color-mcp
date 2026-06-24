"""
Phase 1 smoke test: prove the extracted engine + store run standalone (no Qt, no GUI),
and that all seven tools and all six mix modes behave.

Run from repo root:  python tests/smoke_test.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api
from engine.palette_store import PaletteStore

BRAND_NEAR_BLACK = "#1a1a1a"
BRAND_GOLD = "#d2bc93"


def main() -> None:
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

    if failures:
        print("\nFAILURES:", failures)
        sys.exit(1)
    print("\nAll checks passed. Engine + store run Qt-free.")


if __name__ == "__main__":
    main()