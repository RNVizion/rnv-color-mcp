"""
Selector refusals: an unknown scheme, operation or method is refused, never
defaulted.

These tools take a selector: mix_colors (`mode`), convert_color (`to`),
generate_harmony (`scheme`), transform_text (`operation`) and color_difference
(`method`). The first two refused an unknown one from the start, and nothing
tested that they did before the tests written here on 2026-10-05 (US
Eastern). Two things about them changed with those tests. `mode` refused a
name over its capitals or outer spaces, and `to` over outer spaces: "LAB" can
only mean lab and " hex " can only mean hex, and both resolve now, as a
scheme or an operation written that way already did. One thing did not
change then: an empty `to` was read as not given and returned every format,
where an empty mode, scheme, operation or method was refused. That was pinned
as it stood and left to the owner, who decided on 2026-10-06 (US Eastern)
that it is refused. Only a `to` that is left out means every format now, and
the refusal says so.

The other three did not refuse, and each failed OPEN. generate_harmony
returned [base] for a scheme it did not know -- a one-colour "harmony" for a
typo -- and transform_text returned the input unchanged for an operation it
did not know, as a `result` that reads like success. Both were reproduced on
the live server on 2026-09-27 (`tridic`, `uppercase`) and fixed that day.

color_difference's `method` was the same defect, and the scan of 2026-09-27
missed it: as written until 2026-10-05, this docstring said "Four tools take a
selector", a count that left this one out and had nothing to hold it. The
engine computes cie76 for that exact string and CIEDE2000 for anything else,
and the tool returned the caller's own string as `method`. So `cie94` came
back as a CIEDE2000 figure labelled cie94, and `CIE76`, as the README writes
it, came back 3.9372 labelled CIE76 for a pair whose CIE76 is 6.5389.
Reproduced on the live server on 2026-10-05. It was found by accident, by
trying spellings of the method while checking another project's figures.

The resolver's rule is the server's rule: resolve or refuse, never guess. These
pin it for the selectors that were guessing, at the api seam where the other
checks already live.

TestPositiveControl is the diagnostic: if the documented schemes, operations
and methods do not produce real results, the engine or the import is wrong and
every refusal below is passing for the wrong reason. Read it first.

TestEverySelectorWithADefault is the check that would have found it. It does
not keep a list of selectors; it finds them. A parameter of a tool whose
default is a non-empty string names one choice out of several, so an unknown
value for it must be refused with the choices. What it cannot see: a selector
with no default (scheme, operation) and one whose default is None
(convert_color's `to`). Those are held by the classes named for them below,
and a new one of either kind is still found only by reading.

TestAnEmptySelector holds the rule the five now share: a selector that is
empty, or only spaces, is refused. Its table is held to the tools' own
signatures by parameter name, in both directions, so a row cannot be dropped
without the name being dropped too. The names are kept by hand: a sixth
selector under a new name is found by the discovery test only if it has a
named default.
"""
from __future__ import annotations

import ast
import inspect
import math
import pathlib
import re

import pytest

import api
from engine.color_harmony import HARMONY_SCHEMES
from engine.color_math import ColorMath
from engine.text_transform import TransformMode

# Hand-transcribed from the tool descriptions in server.py -- a second copy of
# the contract on purpose, so drift in either direction fails (§3.2.1a). The
# aliases are what the engine accepts beyond what the description advertises.
DOCUMENTED_SCHEMES = {
    "complementary", "analogous", "triadic", "split-complementary",
    "tetradic", "square", "monochromatic", "compound",
}
UNDOCUMENTED_ALIASES = {"split complementary", "rectangle"}

DOCUMENTED_OPERATIONS = [
    "UPPERCASE", "lowercase", "Title Case", "Sentence case", "camelCase",
    "PascalCase", "snake_case", "CONSTANT_CASE", "kebab-case", "dot.case",
    "iNVERTED cASE",
]

DOCUMENTED_METHODS = {"ciede2000", "cie76"}

DOCUMENTED_FORMATS = {"hex", "rgb", "hsv", "hsl", "lab"}

#: Two colours the two methods measure differently, so each name is shown to
#: reach its own arithmetic: 6.5389 in cie76, 3.9372 in ciede2000. It is the
#: pair the brand register corrected on 2026-10-05, where a published 6.5 was
#: CIE76 in a register whose default is CIEDE2000.
METHOD_PAIR = ("#a885ae", "#ad85a3")

#: Arguments that make a tool callable, so the discovery test can reach its
#: selector. A tool that gains a named default and has no entry here fails by
#: name; it is never skipped.
CALLABLE_WITH = {
    "mix_colors": {"colors": ["#d2bc93", "#1a1a1a"]},
    "color_difference": {"color1": METHOD_PAIR[0], "color2": METHOD_PAIR[1]},
}

#: The parameter names that select one choice out of several. Kept by hand;
#: the module docstring says what that leaves unseen.
SELECTOR_NAMES = {"mode", "to", "scheme", "operation", "method"}

#: The selectors, each with one value it accepts and the arguments that make
#: its tool callable.
SELECTORS = [
    ("mix_colors", "mode", "lab", {"colors": ["#d2bc93", "#1a1a1a"]}),
    ("convert_color", "to", "hex", {"color": "#d2bc93"}),
    ("generate_harmony", "scheme", "triadic", {"base": "#d2bc93"}),
    ("transform_text", "operation", "UPPERCASE", {"text": "the honest machine"}),
    ("color_difference", "method", "cie76",
     {"color1": METHOD_PAIR[0], "color2": METHOD_PAIR[1]}),
]


def tool_description(name):
    """The description server.py registers a tool with, read from the source,
    so that no test imports the server."""
    source = pathlib.Path(api.__file__).with_name("server.py").read_text(encoding="utf-8")
    found = [
        ast.literal_eval(keyword.value)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and node.args
        and ast.unparse(node.func) == "mcp.tool" and ast.unparse(node.args[0]) == f"api.{name}"
        for keyword in node.keywords if keyword.arg == "description"
    ]
    assert len(found) == 1, (name, len(found))
    return found[0]


def named_defaults():
    """Every (tool, parameter, default) where the default is a non-empty
    string, read from the functions the server registers."""
    return [
        (name, parameter.name, parameter.default)
        for name in api.__all__
        for parameter in inspect.signature(getattr(api, name)).parameters.values()
        if isinstance(parameter.default, str) and parameter.default
    ]


class TestPositiveControl:
    """If this fails, the harness or the engine is wrong, not the guard."""

    def test_every_documented_scheme_returns_more_than_the_base(self):
        for scheme in DOCUMENTED_SCHEMES:
            out = api.generate_harmony("#d2bc93", scheme)
            assert len(out) >= 2, (scheme, out)

    def test_every_documented_operation_transforms(self):
        assert api.transform_text("the honest machine", "UPPERCASE")["result"] == "THE HONEST MACHINE"
        assert api.transform_text("the honest machine", "snake_case")["result"] == "the_honest_machine"
        for op in DOCUMENTED_OPERATIONS:
            assert "result" in api.transform_text("the honest machine", op)

    def test_the_two_methods_are_two_computations(self):
        """For an equality the control is a pair known to differ. cie76 is the
        straight-line distance in Lab, worked here without the engine's
        delta_e, and ciede2000 gives another figure for the same pair."""
        cie76 = api.color_difference(*METHOD_PAIR, method="cie76")
        ciede2000 = api.color_difference(*METHOD_PAIR, method="ciede2000")
        assert (cie76["display"], ciede2000["display"]) == ("6.5389", "3.9372")
        first, second = (ColorMath.rgb_to_lab(ColorMath.hex_to_rgb(h)) for h in METHOD_PAIR)
        assert cie76["delta_e"] == pytest.approx(math.dist(first, second), abs=1e-12)

    def test_the_description_reader_reads_the_description(self):
        """The control for a check that reads server.py: the reader has to
        find one registration, and return its string whole, from the first
        words to the last."""
        description = tool_description("color_difference")
        assert description.startswith("Perceptual difference (Delta-E) between two colors.")
        assert description.endswith("use contrast_check instead.")

    def test_discovery_finds_the_selectors_with_a_default(self):
        """Equality, so another parameter with a named default fails here
        until someone has looked at it."""
        assert sorted(named_defaults()) == [
            ("color_difference", "method", "ciede2000"),
            ("mix_colors", "mode", "lab"),
        ]


class TestMixMode:
    def test_unknown_mode_is_refused_with_the_list(self):
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#d2bc93", "#1a1a1a"], mode="oil")
        message = str(exc.value)
        assert "Unknown mode 'oil'" in message
        for mode in api._MIX_MODES:
            assert mode in message, f"the refusal must list {mode!r}"

    @pytest.mark.parametrize("bad", ["", "oil", "l a b", "cmyk", None, 3, ["lab"]])
    def test_a_mode_that_is_no_mode_is_refused_and_never_raises_anything_else(self, bad):
        """A list is here because the check used to be `mode not in` a dict,
        which raised TypeError for a value that cannot be hashed."""
        with pytest.raises(ValueError):
            api.mix_colors(["#d2bc93", "#1a1a1a"], mode=bad)

    def test_case_folded_mode_resolves_and_is_named_as_documented(self):
        """'LAB' can only mean lab: folding case is resolution, not a guess,
        because the stored names are their own folded forms (next test).
        Before the change written on 2026-10-05, mode was the one selector
        that refused a name over its capitals. The result names the mode that
        ran."""
        pair = ["#d2bc93", "#1a1a1a"]
        assert api.mix_colors(pair, mode="LAB") == api.mix_colors(pair, mode="lab")
        assert api.mix_colors(pair, mode=" Paint ")["mode"] == "paint"
        assert api.mix_colors(pair, mode=" Paint ") == api.mix_colors(pair, mode="paint")

    def test_mode_names_are_stored_folded(self):
        """The precondition of the fold above: a folded input is looked up
        among the stored names, so each stored name has to be its own folded
        form. Being the keys of one dict, they are already distinct."""
        assert [mode.strip().lower() for mode in api._MIX_MODES] == list(api._MIX_MODES)


class TestConvertFormat:
    def test_unknown_format_is_refused_with_the_list(self):
        with pytest.raises(ValueError) as exc:
            api.convert_color("#d2bc93", to="cmyk")
        message = str(exc.value)
        assert "Unknown format 'cmyk'" in message
        for name in DOCUMENTED_FORMATS:
            assert name in message, f"the refusal must list {name!r}"

    def test_format_is_case_insensitive(self):
        assert api.convert_color("#d2bc93", to="HEX") == {"hex": "#d2bc93"}

    def test_outer_spaces_in_a_format_are_folded(self):
        """' hex ' can only mean hex. Before the change written on 2026-10-05
        `to` refused a name over outer spaces, as `mode` did. Spaces alone
        are still no format."""
        assert api.convert_color("#d2bc93", to=" hex ") == {"hex": "#d2bc93"}
        with pytest.raises(ValueError):
            api.convert_color("#d2bc93", to="   ")

    def test_an_empty_format_is_refused_and_the_refusal_says_how_to_get_them_all(self):
        """Until the change written on 2026-10-06 (US Eastern) an empty `to`
        returned every format, the same as leaving it out, and this test
        pinned that as it stood. The owner decided it is refused. A caller
        who sent "" meaning every format has to be told how to ask for that,
        so the refusal names the way: leave `to` out."""
        with pytest.raises(ValueError) as exc:
            api.convert_color("#d2bc93", to="")
        assert str(exc.value) == (
            "Unknown format ''. Choose from ['hex', 'hsl', 'hsv', 'lab', 'rgb'], "
            "or leave `to` out for all of them.")

    def test_only_a_format_left_out_means_every_format(self):
        """The control for the refusal above: None is still every format, so
        the empty string is refused for being empty and not because nothing
        returns them all."""
        every = api.convert_color("#d2bc93")
        assert set(every) == DOCUMENTED_FORMATS
        assert api.convert_color("#d2bc93", to=None) == every

    @pytest.mark.parametrize("bad", [
        "", "   ", "\n", "\t", "cmyk",
        "h", "hs", "he", "hsla", "hexa", "rgba",        # a prefix, a longer word
        "ex", "ab", "sl", "gb",                         # the end of a name
        "h s l", "he x", "h-s-l", "h_s_l", "hsl,hsv",   # a name with something inside it
        "'hex'", "hex.", "hsl\x00",                     # a name with something around it
        "hsb", "cielab",                                # another word for one
        "\uff28\uff33\uff2c", "h\u017fl",               # HSL in full-width letters; h, long s, l
        "all", "any", "none", "null", "*",              # words that sound like every format
    ])
    def test_a_string_that_is_no_format_is_refused(self, bad):
        """A format is resolved only when the folded string IS its name.
        Anything else would be a guess, and each is refused with the choices
        and with the way to get every format."""
        with pytest.raises(ValueError) as exc:
            api.convert_color("#d2bc93", to=bad)
        assert str(exc.value) == (
            f"Unknown format {bad!r}. Choose from ['hex', 'hsl', 'hsv', 'lab', 'rgb'], "
            f"or leave `to` out for all of them.")

    @pytest.mark.parametrize("bad", [0, 3, 1.5, False, True, [], ["hex"], {}, b"hsl"])
    def test_a_format_that_is_not_a_string_is_refused_and_never_raises_anything_else(self, bad):
        """Reached through the Python function only: the tool's schema stops
        these before they get here. 0, False, an empty list and an empty dict
        are in the list because the check used to be `if to:`, which read
        each as not given and returned every format. 3 and a list with
        something in it used to raise AttributeError."""
        with pytest.raises(ValueError):
            api.convert_color("#d2bc93", to=bad)

    def test_the_documented_formats_are_exactly_the_ones_returned(self):
        """Both directions: with no `to` the tool returns every format, and
        each documented name returns that format alone."""
        assert set(api.convert_color("#d2bc93")) == DOCUMENTED_FORMATS
        for name in DOCUMENTED_FORMATS:
            assert set(api.convert_color("#d2bc93", to=name)) == {name}


class TestHarmonyScheme:
    def test_unknown_scheme_is_refused_with_the_list(self):
        with pytest.raises(ValueError) as exc:
            api.generate_harmony("brand gold", "tridic")
        message = str(exc.value)
        assert "Unknown scheme 'tridic'" in message
        for scheme in DOCUMENTED_SCHEMES:
            assert scheme in message, f"the refusal must list {scheme!r}"

    def test_unknown_scheme_never_returns_a_one_colour_harmony(self):
        """The old behaviour, stated as the thing that must not happen."""
        with pytest.raises(ValueError):
            api.generate_harmony("brand gold", "")
        with pytest.raises(ValueError):
            api.generate_harmony("brand gold", "complimentary")

    def test_scheme_is_case_insensitive(self):
        assert api.generate_harmony("#d2bc93", "Triadic") == api.generate_harmony("#d2bc93", "triadic")

    def test_the_api_refuses_against_the_table_the_engine_dispatches_on(self):
        """Equality, not subset: a scheme added to the engine without a line in
        the description fails here and names itself."""
        assert set(HARMONY_SCHEMES) == DOCUMENTED_SCHEMES | UNDOCUMENTED_ALIASES, (
            sorted(set(HARMONY_SCHEMES) ^ (DOCUMENTED_SCHEMES | UNDOCUMENTED_ALIASES))
        )


class TestTextOperation:
    def test_unknown_operation_is_refused_with_the_list(self):
        with pytest.raises(ValueError) as exc:
            api.transform_text("the honest machine", "SNAKE CASE")
        message = str(exc.value)
        assert "Unknown operation 'SNAKE CASE'" in message
        for op in DOCUMENTED_OPERATIONS:
            assert op in message, f"the refusal must list {op!r}"

    def test_unknown_operation_never_returns_the_input_unchanged(self):
        """The old behaviour, stated as the thing that must not happen."""
        for bad in ("", "shout", "snake case", "UPPER"):
            with pytest.raises(ValueError):
                api.transform_text("the honest machine", bad)

    def test_case_folded_operation_resolves(self):
        """'uppercase' can only mean UPPERCASE: folding case is resolution, not
        a guess, because the folded spellings are unique (next test)."""
        assert api.transform_text("the honest machine", "uppercase")["result"] == "THE HONEST MACHINE"
        assert api.transform_text("The Honest Machine", "LOWERCASE")["result"] == "the honest machine"
        assert api.transform_text("the honest machine", "kebab-CASE")["result"] == "the-honest-machine"

    def test_folded_operation_names_are_unique(self):
        """The precondition of the fold above. If two modes ever fold to one
        string, folding becomes a guess and this fails before the fold does."""
        folded = [m.value.lower() for m in TransformMode]
        assert len(folded) == len(set(folded)), folded

    def test_the_documented_operations_are_exactly_the_engines(self):
        assert [m.value for m in TransformMode] == DOCUMENTED_OPERATIONS


class TestDifferenceMethod:
    def test_unknown_method_is_refused_with_the_list(self):
        with pytest.raises(ValueError) as exc:
            api.color_difference(*METHOD_PAIR, method="cie94")
        message = str(exc.value)
        assert "Unknown method 'cie94'" in message
        for method in DOCUMENTED_METHODS:
            assert method in message, f"the refusal must list {method!r}"

    @pytest.mark.parametrize("bad", ["", "cie94", "cie2000", "de2000", "euclidean", "cie 76", None, 76])
    def test_unknown_method_never_returns_a_figure_under_the_callers_label(self, bad):
        """The old behaviour, stated as the thing that must not happen: each
        of these returned 3.9372, the CIEDE2000 figure, with `method` set to
        whatever was passed."""
        with pytest.raises(ValueError):
            api.color_difference(*METHOD_PAIR, method=bad)

    def test_case_folded_method_resolves_and_is_named_as_documented(self):
        """'CIE76' can only mean cie76: folding case is resolution, not a
        guess, because the stored names are folded and distinct (next test).
        The README writes both names in capitals. The result names the method
        that was used, so a caller can see which arithmetic the figure came
        from."""
        folded = api.color_difference(*METHOD_PAIR, method="CIE76")
        assert folded == api.color_difference(*METHOD_PAIR, method="cie76")
        assert (folded["method"], folded["display"]) == ("cie76", "6.5389")
        spaced = api.color_difference(*METHOD_PAIR, method=" CIEDE2000 ")
        assert (spaced["method"], spaced["display"]) == ("ciede2000", "3.9372")

    def test_method_names_are_stored_folded_and_distinct(self):
        """The precondition of the fold above: a folded input is looked up
        among the stored names, so each has to be its own folded form, and no
        two may be the same."""
        names = list(api._DIFFERENCE_METHODS)
        assert [name.strip().lower() for name in names] == names
        assert len(names) == len(set(names))

    def test_the_default_is_ciede2000_and_the_result_says_so(self):
        out = api.color_difference(*METHOD_PAIR)
        assert (out["method"], out["display"]) == ("ciede2000", "3.9372")

    def test_the_documented_methods_are_exactly_the_ones_accepted(self):
        """Both directions, twice. The names the api accepts are the names
        written at the top of this file. And the names color_difference's
        description offers a model, which it writes in single quotes, are
        those names and no others."""
        assert set(api._DIFFERENCE_METHODS) == DOCUMENTED_METHODS
        offered = set(re.findall(r"'([^']+)'", tool_description("color_difference")))
        assert offered == DOCUMENTED_METHODS


class TestAnEmptySelector:
    def test_each_selector_accepts_its_own_example(self):
        """The control: every row of the table reaches a real result, so a
        refusal in the next test is for the value and not for the call."""
        for tool, parameter, good, arguments in SELECTORS:
            assert getattr(api, tool)(**arguments, **{parameter: good}), (tool, parameter)

    def test_the_table_is_every_parameter_with_a_selectors_name(self):
        """The table against the tools' own signatures, in both directions:
        its rows are exactly the parameters of registered tools that carry a
        selector's name. A row dropped from the table fails here, and so does
        a tool that gains a `mode` or a `to`. Every selector the discovery
        test finds must be among them."""
        rows = sorted((tool, parameter) for tool, parameter, _, _ in SELECTORS)
        found = sorted((tool, name) for tool in api.__all__
                       for name in inspect.signature(getattr(api, tool)).parameters
                       if name in SELECTOR_NAMES)
        assert rows == found
        assert len(rows) == len(SELECTOR_NAMES) == 5
        assert {(tool, parameter) for tool, parameter, _ in named_defaults()} <= set(rows)

    @pytest.mark.parametrize("empty", ["", " ", "   ", "\t"])
    def test_an_empty_selector_is_refused_by_all_five(self, empty):
        for tool, parameter, _, arguments in SELECTORS:
            with pytest.raises(ValueError) as refusal:
                getattr(api, tool)(**arguments, **{parameter: empty})
            assert "Unknown" in str(refusal.value) and "Choose from" in str(refusal.value), (
                tool, parameter, str(refusal.value))


class TestEverySelectorWithADefault:
    def test_an_unknown_value_is_refused_and_the_default_is_offered(self):
        for tool, parameter, default in named_defaults():
            assert tool in CALLABLE_WITH, (
                f"{tool}'s {parameter} has a named default and no entry in CALLABLE_WITH")
            with pytest.raises(ValueError) as refusal:
                getattr(api, tool)(**CALLABLE_WITH[tool], **{parameter: "no-such-choice"})
            message = str(refusal.value)
            assert "no-such-choice" in message and default in message, (tool, parameter, message)
