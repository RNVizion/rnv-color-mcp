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
call, parsed with ast, never imported through the framework -- and the
surfaces that list tools are held EQUAL to it, in both directions: the
README's table, api.__all__, api.py's header listing, and the smoke script's
hand-kept EXPECTED_TOOLS. The server's `instructions` do not list tool names;
they offer capabilities in prose, so CAPABILITIES below maps each phrase to
the tools it stands for, and a phrase must appear exactly when one of its
tools is registered. That holds the one surface every model reads first to
the set in both directions: a new tool fails until it is offered, and a
removed tool fails until its phrase is gone. Counts are not spelled in prose
at all; the sweep below fails if one reappears in any of the six files. The
figures the descriptions quote (the brand/CSS collision set, the paint model's
zero-channel collapse) are asserted against the engine, so the text fails the
day the behaviour changes.

Until 2026-09-29 this docstring said every surface was held equal. Only the
README's table and api.__all__ were; api.py's header was checked one way,
EXPECTED_TOOLS not at all, and the instructions only for the collision set, so
removing a tool would have left it offered to every model with this file
green. A check built while the failure was a surface behind a GROWING set was
silent on the inverse (practices §3.0.4).

What this file cannot see, and who can:
  - the Claude connector's cached tool list, Glama's copy, and the registry
    entry, which refresh on reconnect, rescan, and the next tagged publish;
  - the brand surfaces outside this repository that describe or count the
    tool set: the rnvizion.dev homepage, /resume/, the maintained resume
    files, and Brand Book section 5. A change to the tool set reaches them
    only through a same-session note to the Architect chat (Build Runbook,
    Locked scope);
  - who links INTO this README. EXTERNAL_ANCHORS lists the anchors known to be
    linked from outside; a heading renamed from under one of them fails here,
    but a new external link is unknown until it is added to that table.
It checks the repository; the live surfaces follow it.

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


def hand_kept_tools(source: str, name: str = "EXPECTED_TOOLS") -> set[str]:
    """The set literal assigned to `name` in a module, read with ast."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise AssertionError(f"no `{name} = {{...}}` assignment found")


def header_listing(doc: str) -> set[str]:
    """Tool names in api.py's header listing: the `Label : a, b, c` lines and
    their indented continuations, up to the first blank line after them."""
    names: set[str] = set()
    started = False
    for line in doc.splitlines():
        label = re.match(r"^[A-Z][\w ]*:\s", line)
        if label:
            started = True
            names |= set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", line[label.end():]))
        elif started and line.startswith(" ") and line.strip():
            names |= set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", line))
        elif started:
            break
    return names


# Each phrase in the first sentence of the server's `instructions` that offers
# a capability, and the tools it stands for. A phrase must appear exactly when
# at least one of its tools is registered. A retired tool KEEPS its entry, so
# its phrase is then required to be gone; a new tool has no entry and fails
# coverage until it is given one. Edit this table on purpose, never to make a
# red test green.
CAPABILITIES: dict[str, frozenset[str]] = {
    r"\bmix colors\b": frozenset({"mix_colors"}),
    r"\bconvert formats\b": frozenset({"convert_color"}),
    r"\blightness\b": frozenset({"place_lightness"}),
    r"\bdifference\b": frozenset({"color_difference"}),
    r"\bcontrast\b": frozenset({"contrast_check"}),
    r"\bharmon(?:y|ies)\b": frozenset({"generate_harmony"}),
    r"\btext\b": frozenset({"transform_text"}),
    r"\bpalettes?\b": frozenset({"save_palette", "list_palettes", "get_palette"}),
}


def capability_sentence(instructions: str) -> str:
    """The instructions' first sentence: the list of what the server offers."""
    return instructions.split(". ", 1)[0]


def capability_mismatches(sentence: str, registered: set[str]) -> list[str]:
    covered = set().union(*CAPABILITIES.values())
    problems = [f"{t}: registered, but no phrase in CAPABILITIES offers it"
                for t in sorted(registered - covered)]
    for pattern, owners in CAPABILITIES.items():
        present = re.search(pattern, sentence) is not None
        live = sorted(owners & registered)
        if live and not present:
            problems.append(f"{pattern!r} is missing from the instructions, but {live} is registered")
        if present and not live:
            problems.append(f"{pattern!r} is still offered, but none of {sorted(owners)} is registered")
    return problems


# Anchors in this README that something OUTSIDE the repository links to. A
# heading renamed from under one of them breaks that link with nothing here
# noticing, so each is held, beside the consumer that depends on it.
EXTERNAL_ANCHORS = {
    "connect-in-30-seconds": "Glama publisher profile, documentation link (filled 2026-09-28)",
}


def github_slug(heading: str) -> str:
    """The anchor GitHub renders for a Markdown heading's text."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


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

    def test_the_header_reader_reads_a_known_listing(self):
        doc = ("Title\n\nEngine : a_one, b_two,\n         c_three\n"
               "Text   : d_four\n\nLater prose names e_five.\n")
        assert header_listing(doc) == {"a_one", "b_two", "c_three", "d_four"}

    def test_the_hand_kept_reader_reads_a_known_set(self):
        assert hand_kept_tools("X = 1\nEXPECTED_TOOLS = {'a', 'b'}\n") == {"a", "b"}

    def test_the_capability_check_sees_a_removed_tool_still_offered(self, tools):
        sentence = capability_sentence(server_instructions(_read("server.py")))
        dropped = sorted(tools)[0]
        assert any("still offered" in p for p in capability_mismatches(sentence, tools - {dropped}))

    def test_the_capability_check_sees_a_new_tool_not_offered(self, tools):
        sentence = capability_sentence(server_instructions(_read("server.py")))
        assert any("new_tool" in p for p in capability_mismatches(sentence, tools | {"new_tool"}))

    def test_the_capability_check_sees_a_phrase_removed(self, tools):
        sentence = capability_sentence(server_instructions(_read("server.py")))
        assert "generate harmonies" in sentence
        broken = sentence.replace("generate harmonies, ", "")
        assert any("missing" in p for p in capability_mismatches(broken, tools))

    @pytest.mark.parametrize("heading, slug", [
        ("Connect in 30 seconds", "connect-in-30-seconds"),
        ("Running a copy?", "running-a-copy"),
        ("What it does", "what-it-does"),
    ])
    def test_the_slug_matches_githubs(self, heading, slug):
        assert github_slug(heading) == slug


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

    def test_api_header_lists_exactly_the_registered_tools(self, tools):
        listed = header_listing(api.__doc__ or "")
        assert listed == tools, f"api.py header vs server: {sorted(listed ^ tools)}"

    def test_smoke_script_expects_exactly_the_registered_tools(self, tools):
        """tests/server_test.py is run by hand and failed on its own nine-tool
        set for two weeks after the tenth landed; its copy is held here."""
        kept = hand_kept_tools(_read("tests/server_test.py"))
        assert kept == tools, f"server_test.py EXPECTED_TOOLS vs server: {sorted(kept ^ tools)}"

    def test_the_instructions_offer_exactly_the_registered_tools(self, tools):
        sentence = capability_sentence(server_instructions(_read("server.py")))
        assert sentence.startswith("Color workflow for RNVizion:"), sentence
        problems = capability_mismatches(sentence, tools)
        assert not problems, "\n".join(problems)

    @pytest.mark.parametrize("anchor", sorted(EXTERNAL_ANCHORS))
    def test_externally_linked_anchor_still_exists(self, anchor):
        slugs = {github_slug(m.group(1))
                 for m in re.finditer(r"^#{1,6}\s+(.+?)\s*$", _read("README.md"), re.M)}
        assert anchor in slugs, (
            f"README no longer has #{anchor}, which {EXTERNAL_ANCHORS[anchor]} links to; "
            f"restore the heading or update that link first")

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
