"""
Selector refusals: an unknown scheme or operation is refused, never defaulted.

Four tools take a selector. Two refused an unknown one from the start
(mix_colors' `mode`, convert_color's `to`). Two did not, and both failed OPEN:
generate_harmony returned [base] for a scheme it did not know -- a one-colour
"harmony" for a typo -- and transform_text returned the input unchanged for an
operation it did not know, as a `result` that reads like success. Both were
reproduced on the live server on 2026-09-27 (`tridic`, `uppercase`).

The resolver's rule is the server's rule: resolve or refuse, never guess. These
pin it for the two selectors that were guessing, at the api seam where the
other two checks already live.

TestPositiveControl is the diagnostic: if the documented schemes and operations
do not produce real results, the engine or the import is wrong and every
refusal below is passing for the wrong reason. Read it first.
"""
from __future__ import annotations

import pytest

import api
from engine.color_harmony import HARMONY_SCHEMES
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
