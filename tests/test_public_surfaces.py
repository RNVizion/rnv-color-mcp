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

Since the change written on 2026-10-06 (US Eastern) four more passages a
model reads are read here and held to the code. The instructions' last
sentence lists what is refused; it listed names, schemes and operations while
modes, formats and methods were refused too, an understatement with nothing
to hold it. mix_colors' advice on paint and lab gave a reason that held for
one brand colour and not for another. Its warning about an empty channel
named paint alone, after the change that made an empty channel dominate in
cmy as well. And convert_color's description now says what hsv and hsl hold.
TestWhatIsRefused, TestTheMixAdvice, TestTheEmptyChannelWarning and
TestTheConvertDescription hold them. Each reads its passage with a pattern
that has to match the whole passage, so a reworded passage FAILS here, with a
message that says so, and the pattern is then changed on purpose with the
text. That is the price of reading the facts out of the prose and not typing
them a second time. What each class holds, in which direction, and what it
cannot see is in its docstring.

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
    tool set: the rnvizion.dev homepage, /resume/, /bio/, the maintained
    resume files, and Brand Book section 5. A change to the tool set reaches
    them through a same-session note to the Architect chat (Build Runbook,
    Locked scope), which carries the reason and the release shape. Since
    2026-09-30 a second route exists: rnv-brand's drift check
    (profile.json, facts.color_mcp_tools) parses this repository's server.py
    and fails by name when the count or the set moves, for the homepage,
    /resume/ and /bio/. It runs on rnv-brand's schedule, not on a push here,
    and does not read the resume files or the Brand Book, so the note stays
    first. (Until 2026-09-30 this line listed four surfaces and said "only";
    /bio/ was missed upstream and inherited here.);
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
import inspect
import json
import math
import pathlib
import re

import pytest

import api
from engine.color_harmony import HARMONY_SCHEMES
from engine.color_math import ColorMath
from engine.resolve import CSS_NAMES, RNV_BRAND, UnknownColor, resolve_color
from engine.text_transform import TransformMode

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
    """Names passed as `api.<name>` to `mcp.tool(...)` calls in server.py.

    This call form is read outside this repository too: rnv-brand's
    verify_tool_sets parses server.py the same way (since 2026-09-30). A new
    registration style fails here first, through the positive control; tell
    Brand Infrastructure in the same session, because theirs fails too.
    """
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


def tool_description(source: str, name: str) -> str:
    """The description `mcp.tool(api.<name>, description=...)` registers,
    read with ast. Exactly one registration must carry one."""
    found = [
        ast.literal_eval(keyword.value)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and node.args
        and ast.unparse(node.func) == "mcp.tool" and ast.unparse(node.args[0]) == f"api.{name}"
        for keyword in node.keywords if keyword.arg == "description"
    ]
    assert len(found) == 1, (name, len(found))
    return found[0]


def one_match(pattern: str, text: str, what: str) -> re.Match:
    """The single place `pattern` matches in `text`. None, or more than one,
    fails with `what`: a passage that was reworded, or said twice, has to be
    looked at again and not read by half."""
    found = list(re.finditer(pattern, text))
    assert found, (
        f"{what}: not found as this file reads it. The passage was reworded, or it no longer "
        f"starts a sentence and ends one where the pattern expects. If the text changed on "
        f"purpose, change the pattern in this file with it.")
    assert len(found) == 1, f"{what}: found {len(found)} times; it should be said once."
    return found[0]


def word_list(text: str) -> list[str]:
    """'a, b and c' -> ['a', 'b', 'c']; 'a and b' -> ['a', 'b']; 'a' -> ['a']."""
    return re.split(r", | and ", text)


#: A sentence starts at the beginning of the text or after a full stop and a
#: space, so a passage cannot be read out of the middle of another sentence
#: ("It is not true that ...", "In one tool only: ...").
_START = r"(?:^|(?<=\. ))"
_LIST = r"((?:\w+, )*\w+(?: and \w+)?)"

REFUSAL = (_START + r"Unknown color names are refused, and unknown " + _LIST
           + r" are refused with the valid choices, never guessed\.$")

ADVICE = (_START + r"Reach for (\w+) when BLENDING brand colors into a new one, and (\w+) when "
          r"SAMPLING between them: (\w+) returns the point between its ingredients, which is "
          r"right for finding a midpoint; (\w+) models mixing them as pigments, which makes a "
          r"different color\. ")

WARNING = (_START + _LIST + r" works? per RGB channel, so an ingredient with an empty channel "
           r"\(pure digital primaries such as (#[0-9a-f]{6}) or (#[0-9a-f]{6})\) dominates that "
           r"channel: at equal weights (\S+) \+ (\S+) comes out black in (\w+) and near-black "
           r"\((#[0-9a-f]{6})\) in (\w+), where (\w+) gives green\. Weight shifts this in (\w+) "
           r"and hardly in (\w+): (\S+) \+ (\S+) at (\d+):(\d+) is (#[0-9a-f]{6}) in (\w+) and "
           r"(#[0-9a-f]{6}) in (\w+)\. ")

FORMATS = (_START + r"With `to` set to one of ([\w/]+), returns just that format; leave `to` out "
           r"to get all of them\. hsv and hsl are fractions from 0 to 1, hue included "
           r"\(multiply hue by 360 for degrees\)\. ")


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

    def test_the_description_reader_reads_a_description_whole(self):
        """From its first words to its last, past every implicit join."""
        description = tool_description(_read("server.py"), "mix_colors")
        assert description.startswith("Blend up to 12 colors into one.")
        assert description.endswith("use color_difference.")
        known = 'mcp.tool(api.a, description=("one " "two"))\nmcp.tool(api.b, description="b")\n'
        assert tool_description(known, "a") == "one two"

    def test_a_word_list_is_split_at_commas_and_at_and(self):
        assert word_list("a, b and c") == ["a", "b", "c"]
        assert word_list("a and b") == ["a", "b"]
        assert word_list("a") == ["a"]

    GOOD_REFUSAL = ("Offers x. Unknown color names are refused, and unknown a, b and c are "
                    "refused with the valid choices, never guessed.")

    def test_the_refusal_pattern_reads_a_known_sentence(self):
        match = one_match(REFUSAL, self.GOOD_REFUSAL, "control")
        assert word_list(match.group(1)) == ["a", "b", "c"]

    @pytest.mark.parametrize("text", [
        GOOD_REFUSAL + " And one thing more.",                       # not the last sentence
        GOOD_REFUSAL.replace("Offers x. ", "Offers x. In one tool only: "),  # not a whole sentence
        GOOD_REFUSAL.replace("Offers x. ", "Offers x. It is false that "),
        GOOD_REFUSAL.replace("a, b and c", "a, b, and c"),           # not the list form it reads
        "Offers x.",
    ])
    def test_the_refusal_pattern_refuses_what_it_cannot_read_whole(self, text):
        with pytest.raises(AssertionError):
            one_match(REFUSAL, text, "control")

    GOOD_WARNING = ("Intro, lab is the default. paint and cmy work per RGB channel, so an "
                    "ingredient with an empty channel (pure digital primaries such as #0000ff or "
                    "#ffff00) dominates that channel: at equal weights yellow + css:blue comes "
                    "out black in paint and near-black (#070707) in cmy, where ryb gives green. "
                    "Weight shifts this in cmy and hardly in paint: white + css:blue at 10:1 is "
                    "#8484ff in cmy and #0202fe in paint. Next sentence.")

    def test_the_warning_pattern_reads_a_known_sentence(self):
        match = one_match(WARNING, self.GOOD_WARNING, "control")
        assert word_list(match.group(1)) == ["paint", "cmy"]
        assert match.groups()[1:] == (
            "#0000ff", "#ffff00", "yellow", "css:blue", "paint", "#070707", "cmy", "ryb",
            "cmy", "paint", "white", "css:blue", "10", "1", "#8484ff", "cmy", "#0202fe", "paint")

    @pytest.mark.parametrize("old, new", [
        ("paint and cmy work", "It is not true that paint and cmy work"),    # not a sentence start
        ("paint and cmy work", "Neither paint nor cmy works"),
        ("in cmy, where", "in cmy and in hsv, where"),
        ("comes out black", "never comes out black"),
        ("dominates that channel", "is ignored in that channel"),
        ("Weight shifts this", "Weight never shifts this"),
        ("and hardly in paint", "and just as much in paint"),
        ("in paint. Next", "in paint, on a good day. Next"),                 # not a sentence end
    ])
    def test_the_warning_pattern_refuses_a_sentence_that_says_something_else(self, old, new):
        assert old in self.GOOD_WARNING
        with pytest.raises(AssertionError):
            one_match(WARNING, self.GOOD_WARNING.replace(old, new), "control")

    GOOD_ADVICE = ("First. Reach for paint when BLENDING brand colors into a new one, and lab when "
                   "SAMPLING between them: lab returns the point between its ingredients, which is "
                   "right for finding a midpoint; paint models mixing them as pigments, which makes "
                   "a different color. RNV's example follows.")

    def test_the_advice_pattern_reads_a_known_sentence(self):
        assert one_match(ADVICE, self.GOOD_ADVICE, "control").groups() == ("paint", "lab", "lab", "paint")

    @pytest.mark.parametrize("old, new", [
        ("First. Reach", "First, it is wrong to say: Reach"),                # not a sentence start
        ("Reach for paint", "Never reach for paint"),
        ("which makes a different color", "which makes the same color"),
        ("is right for finding a midpoint", "is wrong for finding a midpoint"),
        ("returns the point between", "never returns the point between"),
        ("a different color. RNV", "a different color, or so it is said. RNV"),  # not a sentence end
    ])
    def test_the_advice_pattern_refuses_a_sentence_that_says_something_else(self, old, new):
        assert old in self.GOOD_ADVICE
        with pytest.raises(AssertionError):
            one_match(ADVICE, self.GOOD_ADVICE.replace(old, new), "control")

    GOOD_FORMATS = ("Convert a color. With `to` set to one of a/b/c, returns just that format; "
                    "leave `to` out to get all of them. hsv and hsl are fractions from 0 to 1, hue "
                    "included (multiply hue by 360 for degrees). Read-only.")

    def test_the_formats_pattern_reads_a_known_sentence(self):
        assert one_match(FORMATS, self.GOOD_FORMATS, "control").group(1).split("/") == ["a", "b", "c"]

    @pytest.mark.parametrize("old, new", [
        ("Convert a color. With", "Convert a color, but never: With"),       # not a sentence start
        ("leave `to` out to get all of them", "otherwise returns all of them"),
        ("fractions from 0 to 1", "percentages from 0 to 100"),
        ("hue included", "hue excluded"),
        ("multiply hue by 360", "multiply hue by 100"),
        ("for degrees). Read-only.", "for degrees), more or less. Read-only."),  # not a sentence end
    ])
    def test_the_formats_pattern_refuses_a_sentence_that_says_something_else(self, old, new):
        assert old in self.GOOD_FORMATS
        with pytest.raises(AssertionError):
            one_match(FORMATS, self.GOOD_FORMATS.replace(old, new), "control")

    def test_a_passage_said_twice_is_refused(self):
        """one_match reads a passage only when it is there once. The refusal
        sentence cannot be there twice, because it has to end the text."""
        for pattern, good in ((WARNING, self.GOOD_WARNING), (ADVICE, self.GOOD_ADVICE),
                              (FORMATS, self.GOOD_FORMATS)):
            assert one_match(pattern, good, "control")
            with pytest.raises(AssertionError):
                one_match(pattern, good + " " + good.split(". ", 1)[1], "control")

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


#: Each kind of choice the instructions' last sentence may list, with the
#: tool and parameter it stands for, arguments that make the tool callable,
#: a value the parameter accepts, and values it must refuse. The first is
#: nothing like a choice. The rest are near misses of real ones, each a way
#: a selector could start to guess. The second is the start of one name and
#: no other, and the third the end of one name and no other;
#: test_the_second_and_third_near_misses_fit_one_name_only holds those two
#: to what they are said to be. After them, in no fixed order: a longer
#: word; a start or an end that several names share; another separator or a
#: space inside; another word for it; and a name with quotes or a full stop
#: around it. One that came back as an answer would be a guess.
REFUSED = {
    "modes": ("mix_colors", "mode", {"colors": ["#d2bc93", "#1a1a1a"]}, "lab",
              ["no-such-choice", "pai", "int", "la", "labs", "r", "la-b", "r_g_b", "l ab",
               "pigment", "km", "'lab'", "lab."]),
    "formats": ("convert_color", "to", {"color": "#d2bc93"}, "hex",
                ["no-such-choice", "he", "ex", "hexa", "hs", "h-s-l", "h_s_l", "h sl",
                 "hsb", "cielab", "'hex'", "hex."]),
    "schemes": ("generate_harmony", "scheme", {"base": "#d2bc93"}, "triadic",
                ["no-such-choice", "tri", "ogous", "triadics", "adic", "split_complementary",
                 "splitcomplementary", "tri adic", "triad", "complement", "'triadic'", "triadic."]),
    "operations": ("transform_text", "operation", {"text": "the honest machine"}, "UPPERCASE",
                   ["no-such-choice", "UPPER", "PERCASE", "UPPERCASES", "case", "snake-case",
                    "kebab_case", "upper case", "caps", "'UPPERCASE'", "UPPERCASE."]),
    "methods": ("color_difference", "method", {"color1": "#d2bc93", "color2": "#1a1a1a"}, "cie76",
                ["no-such-choice", "cied", "76", "cie766", "cie", "cie-76", "cie_76", "cie 76",
                 "de00", "de2000", "'cie76'", "cie76."]),
}

#: The names each selector accepts, as the code holds them.
CHOICES = {
    "modes": lambda: list(api._MIX_MODES),
    "formats": lambda: list(api.convert_color("#d2bc93")),
    "schemes": lambda: list(HARMONY_SCHEMES),
    "operations": lambda: [mode.value for mode in TransformMode],
    "methods": lambda: list(api._DIFFERENCE_METHODS),
}

#: Strings that are no colour: nothing like one, near misses of real names,
#: and the `css:` escape with a name CSS does not have.
UNKNOWN_COLOR_NAMES = ["no-such-color", "reddish", "re", "golds", "brand golden", "css:nosuch"]

def _mix_with(position: int, of: int):
    """A call that mixes `of` colours with the one under test at `position`."""
    def call(name):
        colors = (["#1a1a1a", "#d2bc93"] * of)[:of]
        colors[position] = name
        return api.mix_colors(colors)
    return call


#: Every position in which a read-only tool takes a colour. mix_colors is
#: tried at each position of a mix of two, of three, and of as many as it
#: takes; every other position is tried in one call.
#: test_the_table_covers_every_tool_that_resolves_a_color holds the tools,
#: and test_no_table_is_short the number of calls for each. Neither can tell
#: that two calls of a row reach two different positions, and a tool that
#: gains a second colour parameter is not found by this table.
COLOR_POSITIONS = {
    "convert_color": [lambda n: api.convert_color(n)],
    "mix_colors": [_mix_with(position, of) for of in (2, 3, api.MAX_MIX_COLORS)
                   for position in range(of)],
    "place_lightness": [lambda n: api.place_lightness(n, [50.0])],
    "generate_harmony": [lambda n: api.generate_harmony(n, "triadic")],
    "color_difference": [lambda n: api.color_difference(n, "#1a1a1a"),
                         lambda n: api.color_difference("#1a1a1a", n)],
    "contrast_check": [lambda n: api.contrast_check(n, "#1a1a1a"),
                       lambda n: api.contrast_check("#1a1a1a", n)],
}


class TestWhatIsRefused:
    """The instructions end by telling a model what is refused and never
    guessed. Until the change written on 2026-10-06 (US Eastern) the sentence
    listed names, schemes and operations; modes, formats and methods were
    refused too.

    What is held. The kinds of choice the sentence lists are exactly the keys
    of REFUSED, both ways. Each key's parameter exists on a registered tool
    and accepts the value given for it. Each value listed as unknown is
    refused with a list of choices; most are near misses, so a selector that
    began to guess in one of those ways would fail here. An unknown colour
    name is refused in every position of every read-only tool that takes a
    colour: mix_colors in mixes of two, of three and of twelve, the others
    in one call each.

    What this cannot see.
      - A selector added to a tool: REFUSED is kept by hand.
        test_selector_refusals.py is where a new selector would be found,
        and it says what it cannot find.
      - Whether the list a refusal carries is the right list. The classes in
        test_selector_refusals.py hold that.
      - Every guess. The near misses are a dozen or so strings a selector,
        picked by the ways a guess is usually made. A guess of another kind
        can pass: letters swapped, a leading article, a synonym not listed,
        and for some of the selectors a plural or a doubled letter. A word that is also a hex
        colour without its # (bad, fed, facade) is a colour and resolves;
        that is the hex form, not a name guessed.
      - save_palette, the one tool that writes. It refuses an unknown colour
        by position; test_palette_contract.py holds that.
      - A colour swallowed only under some other argument: with weights, in
        another mode, with another scheme or method, or in a mix of four to
        eleven colours.
      - A tool that reaches the resolver through a helper. The table is held
        to the tools whose own source names resolve_color, so a new tool
        that resolved through a function of its own would not be asked for
        a row.
      - Other refusals the sentence does not list: a mix weight, a palette's
        swatch number, more colours than mix_colors takes. And get_palette
        answers null for a palette name it does not have, which is a lookup
        and not a refusal; the sentence says colour names.
      - The tool layer. These call the functions the tools wrap. Through the
        tool, a value of the wrong type is stopped by the schema with the
        schema's own message, which lists no choices."""

    @staticmethod
    def sentence() -> re.Match:
        return one_match(REFUSAL, server_instructions(_read("server.py")),
                         "the instructions' last sentence, on what is refused")

    def test_the_sentence_lists_exactly_the_kinds_the_table_holds(self):
        listed = word_list(self.sentence().group(1))
        assert len(listed) == len(set(listed)), listed
        assert set(listed) == set(REFUSED), sorted(set(listed) ^ set(REFUSED))

    @pytest.mark.parametrize("kind", sorted(REFUSED))
    def test_each_kind_is_a_parameter_that_accepts_its_example(self, kind, tools):
        """The control: the call the refusals below are made with reaches a
        real result when the value is a real choice, so each refusal is for
        the value. And the row's tool is registered and has the parameter."""
        tool, parameter, arguments, good, _ = REFUSED[kind]
        assert tool in tools, (kind, tool)
        assert parameter in inspect.signature(getattr(api, tool)).parameters, (kind, tool, parameter)
        assert getattr(api, tool)(**arguments, **{parameter: good}), (kind, good)

    @pytest.mark.parametrize("kind, unknown", [
        (kind, unknown) for kind in sorted(REFUSED) for unknown in REFUSED[kind][4]])
    def test_an_unknown_one_is_refused_with_choices_and_never_guessed(self, kind, unknown):
        tool, parameter, arguments, _, _ = REFUSED[kind]
        with pytest.raises(ValueError) as refusal:
            getattr(api, tool)(**arguments, **{parameter: unknown})
        message = str(refusal.value)
        # In quotes, so that a string which is part of a real name ('tri' in
        # 'triadic') is found as itself and not inside the list of choices.
        assert f"'{unknown}'" in message or repr(unknown) in message, message
        assert re.search(r"Choose from \[[^\]]+\]", message), message

    @pytest.mark.parametrize("kind", sorted(REFUSED))
    def test_the_second_and_third_near_misses_fit_one_name_only(self, kind):
        """A selector that resolved a start or an end only when it fits ONE
        name would pass a near miss that fits several. So in each row the
        second string begins exactly one accepted name and the third ends
        exactly one, compared as the selector compares them, in lower case."""
        names = [name.lower() for name in CHOICES[kind]()]
        assert len(names) >= 2, kind
        start, end = (text.lower() for text in REFUSED[kind][4][1:3])
        assert [name for name in names if name.startswith(start) and name != start] != []
        assert len([name for name in names if name.startswith(start)]) == 1, (kind, start)
        assert len([name for name in names if name.endswith(end)]) == 1, (kind, end)
        assert start not in names and end not in names

    def test_no_table_is_short(self):
        """A parametrized test with nothing to run is green, and so is a loop
        over nothing. Each table has to hold what the docstring says it
        holds for the tests around it to mean anything."""
        assert len(UNKNOWN_COLOR_NAMES) == len(set(UNKNOWN_COLOR_NAMES)) == 6
        for kind, row in REFUSED.items():
            assert len(row[4]) == len(set(row[4])) >= 11, kind
        assert api.MAX_MIX_COLORS == 12
        assert {tool: len(calls) for tool, calls in COLOR_POSITIONS.items()} == {
            "convert_color": 1, "mix_colors": 2 + 3 + 12, "place_lightness": 1,
            "generate_harmony": 1, "color_difference": 2, "contrast_check": 2}

    def test_the_table_covers_every_tool_that_resolves_a_color(self, tools):
        """Every registered tool whose function names resolve_color is in
        COLOR_POSITIONS, except the one that writes, and no other tool is."""
        resolving = {name for name in tools
                     if "resolve_color" in inspect.getsource(getattr(api, name))}
        assert resolving - {"save_palette"} == set(COLOR_POSITIONS), (
            sorted(resolving ^ set(COLOR_POSITIONS)))
        assert "save_palette" in resolving

    def test_each_color_position_accepts_a_color(self):
        """The control: every call in the table reaches a result when the
        colour is real, so a refusal below is for the name."""
        for tool, calls in COLOR_POSITIONS.items():
            for call in calls:
                assert call("brand gold"), tool

    @pytest.mark.parametrize("name", UNKNOWN_COLOR_NAMES)
    def test_an_unknown_color_name_is_refused(self, name):
        for calls in COLOR_POSITIONS.values():
            for call in calls:
                with pytest.raises(UnknownColor):
                    call(name)


class TestTheMixAdvice:
    """mix_colors' description says when to reach for paint and when for lab,
    and gives each a reason: lab returns the point between its ingredients;
    paint models mixing them as pigments, which makes a different color.
    Until the change written on 2026-10-06 (US Eastern) the reason given was
    that lab averages chroma toward the centroid, which held for the teal's
    ingredients and not for the blue's.

    What is held. Which mode the advice gives to which use, and which mode
    each reason is about. For every pair of brand colours, lab's mix is
    within one unit of the mean of the two in CIELAB, and paint's mix is a
    different colour from lab's for nearly all of them.

    What this cannot see.
      - A lab mix whose mean falls outside sRGB. The engine clamps it, and
        the result is then not the point between: red + white lands about 8
        units from it. No pair of brand colours does this today, and the
        description does not say it.
      - Whether paint is what real pigments would make. Nothing here
        compares with a measured pigment.
      - That the advice is good advice. The example the description gives
        after it is held in test_mix_outputs.py."""

    @staticmethod
    def brand_pairs():
        values = sorted({value.lower() for value in RNV_BRAND.values()})
        return [(a, b) for i, a in enumerate(values) for b in values[i + 1:]]

    def test_the_advice_gives_paint_to_blending_and_lab_to_sampling(self):
        match = one_match(ADVICE, tool_description(_read("server.py"), "mix_colors"),
                          "mix_colors' advice on paint and lab")
        assert match.groups() == ("paint", "lab", "lab", "paint")

    def test_there_are_enough_brand_pairs_to_mean_something(self):
        assert len(self.brand_pairs()) >= 45

    def test_lab_returns_the_point_between_its_ingredients(self):
        lab = lambda colour: ColorMath.rgb_to_lab(ColorMath.hex_to_rgb(colour))
        for a, b in self.brand_pairs():
            mixed = api.mix_colors([a, b], mode="lab")["hex"]
            middle = [(x + y) / 2 for x, y in zip(lab(a), lab(b))]
            assert math.dist(lab(mixed), middle) < 1.0, (a, b, mixed)

    def test_the_point_between_is_not_where_the_ingredients_are(self):
        """The control for the test above: its measure can tell the middle
        from an end. For every pair of brand colours each ingredient is
        further from the middle than the one unit the test allows."""
        lab = lambda colour: ColorMath.rgb_to_lab(ColorMath.hex_to_rgb(colour))
        for a, b in self.brand_pairs():
            assert math.dist(lab(a), lab(b)) / 2 > 1.5, (a, b)

    def test_paint_makes_a_different_color(self):
        pairs = self.brand_pairs()
        same = [(a, b) for a, b in pairs
                if api.mix_colors([a, b], mode="paint")["hex"] == api.mix_colors([a, b], mode="lab")["hex"]]
        assert len(same) <= len(pairs) // 10, same


class TestTheEmptyChannelWarning:
    """mix_colors' description warns that paint and cmy work per RGB channel,
    so an ingredient with an empty channel dominates it; gives yellow +
    css:blue at equal weights as the example; and says weight shifts this in
    cmy and hardly in paint, with one mix at ten to one as the case. Like the
    paint figures above, this pins a LIMITATION: when a model stops
    collapsing, this fails, and the warning changes with it.

    What is held. The modes the warning names are exactly the modes in which
    its own example comes out near-black, both ways. Each named mode does
    work one channel at a time. Each colour it calls a pure digital primary
    has an empty channel. Its example, read from the text, gives black in the
    first mode it names, the quoted figure in the second, and a green in the
    third. Its weighted case, read from the text, gives the two figures it
    quotes, and those figures bear the sentence out: the empty channel is
    at 100 of 255 or above in the mode it says shifts, and within two steps
    of empty in the mode it says hardly does.

    What this cannot see.
      - "work per RGB channel" in the other direction: rgb works one channel
        at a time as well and is not named, because an empty channel does not
        dominate there. The warning names the modes where it does.
      - Weight beyond the one case the sentence gives. Measured on
        2026-10-07 for white against css:blue: cmy lifts the channel to 23
        of 255 at 2:1, 132 at 10:1 and 237 at 100:1; paint to 0, 2 and 21.
        Against a darker colour cmy lifts less. And "hardly" is about a
        channel that is exactly empty: one at 5 of 255 comes up to 40 in
        paint at 10:1.
      - The rest of the description's prose. A false sentence added beside
        the passage is not read by anything here."""

    @staticmethod
    def warning() -> re.Match:
        return one_match(WARNING, tool_description(_read("server.py"), "mix_colors"),
                         "mix_colors' warning about an empty channel")

    @staticmethod
    def channels(colors, mode, weights=None):
        return api.mix_colors(colors, weights=weights, mode=mode)["rgb"]

    def collapsed(self) -> set[str]:
        """The modes in which the warning's own example comes out near-black:
        every channel below 16 of 255."""
        example = list(self.warning().group(4, 5))
        return {mode for mode in api._MIX_MODES if max(self.channels(example, mode)) < 16}

    def test_some_modes_collapse_and_some_do_not(self):
        """The control: the measure separates the modes, so the equality
        below is not two empty sets or two full ones."""
        assert self.collapsed() and self.collapsed() < set(api._MIX_MODES)

    def test_the_description_speaks_of_working_per_channel_once(self):
        """The pattern reads one passage. A second sentence that named other
        modes as working per RGB channel would not be read by it, so there
        must not be one."""
        description = tool_description(_read("server.py"), "mix_colors")
        assert description.count("per RGB channel") == 1

    def test_the_warning_names_exactly_the_modes_that_collapse(self):
        named = word_list(self.warning().group(1))
        assert len(named) == len(set(named)) and set(named) <= set(api._MIX_MODES), named
        assert set(named) == self.collapsed(), (sorted(named), sorted(self.collapsed()))

    #: Pairs to mix, and other colours whose channels are swapped in around
    #: the one under test.
    PAIRS = [((200, 30, 90), (10, 180, 250)), ((255, 255, 0), (0, 0, 255)), ((17, 99, 203), (240, 120, 33))]
    OTHERS = [((1, 2, 3), (250, 251, 252)), ((128, 64, 32), (8, 16, 24))]

    def crossings(self, mode) -> int:
        """How often an output channel moves when only the OTHER channels of
        the ingredients change. 0 means the mode works one channel at a time
        on these colours."""
        hexes = lambda *colours: ["#%02x%02x%02x" % tuple(c) for c in colours]
        moved = 0
        for a, b in self.PAIRS:
            base = self.channels(hexes(a, b), mode)
            for k in range(3):
                for a_other, b_other in self.OTHERS:
                    a2, b2 = list(a_other), list(b_other)
                    a2[k], b2[k] = a[k], b[k]
                    moved += self.channels(hexes(a2, b2), mode)[k] != base[k]
        return moved

    def test_each_named_mode_works_one_channel_at_a_time(self):
        for mode in word_list(self.warning().group(1)):
            assert self.crossings(mode) == 0, mode

    def test_the_channel_probe_can_tell_a_mode_that_does_not(self):
        """The control for the test above."""
        assert self.crossings("lab") > 0 and self.crossings("hsv") > 0

    def test_each_primary_it_names_has_an_empty_channel(self):
        for primary in self.warning().group(2, 3):
            assert 0 in ColorMath.hex_to_rgb(primary), primary

    def test_its_example_gives_what_it_says_in_each_mode(self):
        match = self.warning()
        example = list(match.group(4, 5))
        black_mode, figure, figure_mode, green_mode = match.group(6, 7, 8, 9)
        assert {black_mode, figure_mode} == set(word_list(match.group(1)))
        assert api.mix_colors(example, mode=black_mode)["hex"] == "#000000"
        assert api.mix_colors(example, mode=figure_mode)["hex"] == figure
        assert figure != "#000000" and max(ColorMath.hex_to_rgb(figure)) < 16, "near-black, and not black"
        red, green, blue = self.channels(example, green_mode)
        assert green >= 100 and red < 16 and blue < 16, (green_mode, red, green, blue)

    def test_its_weighted_case_gives_the_figures_it_quotes(self):
        match = self.warning()
        shifts, hardly = match.group(10, 11)
        colors, weights = list(match.group(12, 13)), [int(w) for w in match.group(14, 15)]
        first_figure, first_mode, second_figure, second_mode = match.group(16, 17, 18, 19)
        assert {shifts, hardly} == set(word_list(match.group(1)))
        assert (first_mode, second_mode) == (shifts, hardly)
        assert api.mix_colors(colors, weights=weights, mode=shifts)["hex"] == first_figure
        assert api.mix_colors(colors, weights=weights, mode=hardly)["hex"] == second_figure

    def test_the_figures_bear_the_sentence_out(self):
        """The case is read from the text: the heavier colour has every
        channel full, and the lighter one has a channel that is empty. At
        equal weights that channel is near empty in both modes. With the
        weight, it is past 100 of 255 in the mode said to shift and within
        two steps of empty in the mode said hardly to."""
        match = self.warning()
        shifts, hardly = match.group(10, 11)
        colors, weights = list(match.group(12, 13)), [int(w) for w in match.group(14, 15)]
        heavy, light = (ColorMath.hex_to_rgb(resolve_color(c)) for c in colors)
        assert weights[0] > weights[1] and min(heavy) == 255 and 0 in light
        empty = light.index(0)
        for mode in (shifts, hardly):
            assert self.channels(colors, mode)[empty] <= 7, mode
        assert self.channels(colors, shifts, weights)[empty] >= 100
        assert self.channels(colors, hardly, weights)[empty] <= 2


class TestTheConvertDescription:
    """convert_color's description names the formats, says how to get them
    all, and says what hsv and hsl hold.

    What is held. The formats it names are exactly the ones returned, both
    ways. Leaving `to` out returns them all. Over 222 colours every hsv and
    hsl component is from 0 to 1, and for the six pure hues hue times 360 is
    the angle everyone uses.

    What this cannot see: the ORDER of the hsv and hsl components, which the
    description leaves to the names. The other script of this series adds
    tests/test_convert_outputs.py, which holds the order to the definitions;
    where that script has not landed, nothing does, and `hsl` is still hue,
    lightness, saturation."""

    @staticmethod
    def passage() -> re.Match:
        return one_match(FORMATS, tool_description(_read("server.py"), "convert_color"),
                         "convert_color's sentence on formats and on hsv and hsl")

    def test_the_formats_it_names_are_exactly_the_ones_returned(self):
        named = self.passage().group(1).split("/")
        assert len(named) == len(set(named))
        assert set(named) == set(api.convert_color("#d2bc93")), named

    def test_leaving_to_out_returns_all_of_them(self):
        """Left out, and given as null, which is how a client that sends
        every argument leaves it out. Each has to return a value under every
        name, not only the names."""
        named = self.passage().group(1).split("/")
        left_out = api.convert_color("#d2bc93")
        assert sorted(left_out) == sorted(named) and all(left_out.values())
        assert api.convert_color("#d2bc93", to=None) == left_out

    def test_hsv_and_hsl_are_fractions_from_0_to_1(self):
        self.passage()
        steps = range(0, 256, 51)
        colours = [(r, g, b) for r in steps for g in steps for b in steps]
        colours += [(1, 0, 0), (0, 0, 1), (254, 255, 255), (255, 0, 1), (251, 251, 252), (130, 132, 131)]
        assert len(colours) == 222
        for rgb in colours:
            out = api.convert_color("#%02x%02x%02x" % rgb)
            assert all(0.0 <= x <= 1.0 for x in out["hsv"] + out["hsl"]), (rgb, out)

    @pytest.mark.parametrize("colour, degrees", [
        ("#ff0000", 0), ("#ffff00", 60), ("#00ff00", 120),
        ("#00ffff", 180), ("#0000ff", 240), ("#ff00ff", 300),
    ])
    def test_hue_times_360_is_degrees(self, colour, degrees):
        self.passage()
        out = api.convert_color(colour)
        assert out["hsv"][0] * 360 == pytest.approx(degrees, abs=1e-9)
        assert out["hsl"][0] * 360 == pytest.approx(degrees, abs=1e-9)


class TestRegistryMetadata:
    def test_description_fits_the_registry_schema(self):
        """server.schema.json (2025-10-17) caps description at 100 characters;
        an overlong one fails publish-mcp.yml at tag time, after the tag is
        pushed. Checked here, before."""
        meta = json.loads(_read("server.json"))
        assert meta["$schema"].endswith("/2025-10-17/server.schema.json")
        assert 1 <= len(meta["description"]) <= 100, len(meta["description"])
