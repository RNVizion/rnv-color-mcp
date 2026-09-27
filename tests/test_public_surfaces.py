"""
Public surfaces cannot fall behind the server.

Found 2026-09-27: two weeks after the tenth tool landed, five surfaces still
described nine or fewer -- the README's table and auth paragraph, SECURITY.md,
a comment in server.py, and api.py's header and __all__ -- and the smoke
script the README tells people to run failed on its nine-tool set. Every one
of them was correct the day it was written. Describers stay behind when the
thing they describe moves (practices §7.6 and §3.2.2), and prose cannot be
wrong loudly; an assertion can (§5.5.4).

So the tool set is DISCOVERED from server.py -- every `mcp.tool(api.<name>, ...)`
call, parsed with ast, never imported through the framework -- and each
surface is held equal to it. Counts are not spelled in prose at all; the
sweep below fails if one reappears. The figures the new descriptions quote
(the brand/CSS collision set, the paint model's zero-channel collapse) are
asserted against the engine, so the text fails the day the behaviour changes.

What this file cannot see: the Claude connector's cached tool list, Glama's
copy, and the registry entry. Those refresh on reconnect, rescan, and the
next tagged publish. It checks the repository; the live surfaces follow it.

TestPositiveControl is the diagnostic: the discovery must find tools it
provably contains, and the count sweep must catch a count it is shown. If
either fails, every green below is a picture.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re

import pytest

import api
from engine.color_math import ColorMath
from engine.resolve import CSS_NAMES, RNV_BRAND

ROOT = pathlib.Path(api.__file__).resolve().parent
SURFACES = ["README.md", "SECURITY.md", "server.py", "api.py",
            "tests/server_test.py", "tests/smoke_test.py"]

# A number (word or digit) followed within two words by "tool" or "tools".
# The gap is words only, so it cannot cross punctuation or a sentence
# (practices §3.1b: carry the noun, and do not let the gap wander).
_COUNT = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d+)"
    r"\s+(?:[\w-]+\s+){0,2}tools?\b",
    re.IGNORECASE,
)


def registered_tools(source: str) -> set[str]:
    """Names passed as `api.<name>` to `mcp.tool(...)` calls in server.py."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == "tool"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "mcp"
                and node.args and isinstance(node.args[0], ast.Attribute)
                and isinstance(node.args[0].value, ast.Name) and node.args[0].value.id == "api"):
            found.add(node.args[0].attr)
    return found


def server_instructions(source: str) -> str:
    """The `instructions=` string passed to FastMCP(...), read with ast.

    Parsed rather than sliced: the first version of this helper split on "),"
    and stopped inside "(digital and physical/paint models)," -- a harness
    defect that read as a missing name. Implicit string concatenation is
    merged by the parser, so the keyword's value is one Constant.
    """
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "FastMCP":
            for kw in node.keywords:
                if kw.arg == "instructions":
                    return ast.literal_eval(kw.value)
    raise AssertionError("no FastMCP(instructions=...) call found in server.py")


@pytest.fixture(scope="module")
def tools() -> set[str]:
    return registered_tools((ROOT / "server.py").read_text(encoding="utf-8"))


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestPositiveControl:
    def test_discovery_finds_what_it_must(self, tools):
        assert {"mix_colors", "save_palette", "place_lightness"} <= tools
        assert len(tools) >= 3

    def test_discovery_works_on_a_known_source(self):
        src = "mcp.tool(api.a, x=1)\nmcp.tool(api.b)\nother.tool(api.c)\nmcp.tool(foo.d)\n"
        assert registered_tools(src) == {"a", "b"}

    @pytest.mark.parametrize("text", [
        "its nine tools", "the eight read-only tools", "The seven locked tools",
        "exercises all 10 tools", "one tool",
    ])
    def test_the_count_sweep_catches_a_count(self, text):
        assert _COUNT.search(text), text

    @pytest.mark.parametrize("text", [
        "every tool", "the only tool that mutates", "Two scopes: read for every read-only tool",
        "Blend up to 12 colors", "11 exact case transforms", "all six mix modes",
    ])
    def test_the_count_sweep_leaves_prose_alone(self, text):
        assert not _COUNT.search(text), text


class TestToolSetOnEverySurface:
    def test_readme_table_lists_exactly_the_registered_tools(self, tools):
        readme = _read("README.md")
        section = readme.split("## What it does", 1)[1].split("\n## ", 1)[0]
        listed: set[str] = set()
        for line in section.splitlines():
            if line.startswith("| `"):
                listed |= set(re.findall(r"`(\w+)`", line.split("|")[1]))
        assert listed == tools, f"README table vs server: {sorted(listed ^ tools)}"

    def test_api_all_is_exactly_the_registered_tools(self, tools):
        assert set(api.__all__) == tools, sorted(set(api.__all__) ^ tools)

    def test_api_header_names_every_registered_tool(self, tools):
        header = api.__doc__ or ""
        missing = sorted(t for t in tools if t not in header)
        assert not missing, f"api.py header does not name {missing}"

    @pytest.mark.parametrize("rel", SURFACES)
    def test_no_surface_spells_a_tool_count(self, rel):
        hits = [m.group(0) for m in _COUNT.finditer(_read(rel))]
        assert not hits, (
            f"{rel} states a tool count {hits}; counts go stale when the surface "
            f"grows -- describe the set, or let the CI badge carry the number")


class TestRetiredRationale:
    def test_readme_does_not_assert_local_identifiers(self):
        """The register retired local identifiers on 2026-08-17; the mirror's
        own docstring is guarded by test_brand_mirror.py, and this sentence
        survived in the README, outside that guard's reach (practices §4.3)."""
        assert "Identifiers are local by design" not in _read("README.md")


class TestBrandCollisionsAreNamed:
    """Brand names win over CSS names. Where the values differ, the model has
    to be told, or "mix red and blue" silently means RNV blue."""

    @staticmethod
    def shadowed() -> set[str]:
        return {k for k in RNV_BRAND
                if k in CSS_NAMES and RNV_BRAND[k].lower() != CSS_NAMES[k].lower()}

    def test_the_readme_names_exactly_the_shadowed_set(self):
        readme = _read("README.md")
        m = re.search(r"on collision \(([^)]*)\)", readme)
        assert m, "README no longer names the brand/CSS collisions"
        named = set(re.findall(r"`([\w-]+)`", m.group(1)))
        assert named == self.shadowed(), (
            f"collision set moved: README names {sorted(named)}, "
            f"engine shadows {sorted(self.shadowed())}")

    def test_the_instructions_reader_reads_the_whole_string(self):
        """Control for the helper below: it must reach the END of the
        instructions, past the parenthesis that broke its first version."""
        text = server_instructions(_read("server.py"))
        assert text.startswith("Color workflow for RNVizion")
        assert text.rstrip().endswith("never guessed.")

    def test_the_server_instructions_name_every_shadowed_key(self):
        block = server_instructions(_read("server.py"))
        for key in self.shadowed():
            assert re.search(rf"\b{re.escape(key)}\b", block), key

    def test_the_quoted_value_of_blue_is_true(self):
        block = server_instructions(_read("server.py"))
        assert RNV_BRAND["blue"] in block
        assert CSS_NAMES["blue"] in block
        assert api.convert_color("blue", to="hex") == {"hex": RNV_BRAND["blue"]}
        assert api.convert_color("css:blue", to="hex") == {"hex": CSS_NAMES["blue"]}


class TestPaintClaimsAreTrue:
    """Every figure the mix_colors description, the Kubelka-Munk docstring and
    the README quote about paint. These pin a LIMITATION, not a spec: if the
    paint model is improved, these fail, and the text that warns about the
    collapse must change with it."""

    @pytest.mark.parametrize("colors, mode, expected", [
        (["yellow", "css:blue"], "paint", "#000000"),
        (["#ffff00", "#0000ff"], "paint", "#000000"),
        (["red", "yellow"], "paint", "#fe0000"),
        (["white", "css:blue"], "paint", "#0000fe"),
        (["yellow", "css:blue"], "ryb", "#007f00"),
        (["#fdd835", "#1e40af"], "paint", "#315c4d"),
        (["crimson", "royalblue"], "paint", "#5d2157"),
    ])
    def test_quoted_mix(self, colors, mode, expected):
        assert api.mix_colors(colors, mode=mode)["hex"] == expected

    def test_the_readme_example_darkens_in_paint(self):
        """'the blend darkens the way mixed pigment actually does, not the
        way averaged light does' -- for the example the README now uses."""
        assert "Mix crimson and royalblue like real pigment" in _read("README.md")
        lightness = lambda h: ColorMath.rgb_to_lab(ColorMath.hex_to_rgb(h))[0]
        paint = api.mix_colors(["crimson", "royalblue"], mode="paint")["hex"]
        light = api.mix_colors(["crimson", "royalblue"], mode="rgb")["hex"]
        assert lightness(paint) < lightness(light) - 10, (paint, light)


class TestRegistryMetadata:
    def test_description_fits_the_registry_schema(self):
        """server.schema.json (2025-10-17) caps description at 100 characters;
        an overlong one fails publish-mcp.yml at tag time, after the tag is
        pushed. Checked here, before."""
        meta = json.loads(_read("server.json"))
        assert meta["$schema"].endswith("/2025-10-17/server.schema.json")
        assert 1 <= len(meta["description"]) <= 100, len(meta["description"])
