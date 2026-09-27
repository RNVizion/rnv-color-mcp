"""
Published input limits are enforced, not just published.

mix_colors has said "up to 12 colors" in its tool description, the README and
the Runbook since Phase 0, and until 2026-09-27 accepted any count. A limit
that is documented and not enforced is a claim the code does not back: a
caller who reads the description and a caller who does not get different
servers. Now the code refuses a thirteenth color with the count and a remedy.

The limit is asserted against the constant AND against the description text,
so moving one without the other fails here.

TestPositiveControl is the diagnostic: exactly the limit must mix. If it
fails, the refusal below is passing because mixing is broken, not because the
limit works.
"""
from __future__ import annotations

import re

import pytest

import api


class TestPositiveControl:
    def test_exactly_the_limit_mixes(self):
        out = api.mix_colors(["#d2bc93"] * api.MAX_MIX_COLORS, mode="lab")
        assert out["hex"] == "#d2bc93"


class TestMixColorsLimit:
    def test_one_over_the_limit_is_refused_with_the_count(self):
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["#d2bc93"] * (api.MAX_MIX_COLORS + 1))
        message = str(exc.value)
        assert f"up to {api.MAX_MIX_COLORS}" in message
        assert f"got {api.MAX_MIX_COLORS + 1}" in message

    def test_the_limit_is_checked_before_anything_is_resolved(self):
        """A refusal for the count must not be masked by a refusal for a
        color: the caller should learn the structural problem first."""
        with pytest.raises(ValueError) as exc:
            api.mix_colors(["not-a-color"] * (api.MAX_MIX_COLORS + 1))
        assert "up to" in str(exc.value)

    def test_the_description_states_the_limit_the_code_enforces(self):
        """Read the model-facing text from the source, so this does not depend
        on how the framework exposes descriptions."""
        import pathlib
        src = pathlib.Path(api.__file__).with_name("server.py").read_text(encoding="utf-8")
        start = src.index("api.mix_colors,")
        described = re.search(r"Blend up to (\d+) colors", src[start:start + 400])
        assert described, "mix_colors' description no longer states a limit"
        assert int(described.group(1)) == api.MAX_MIX_COLORS
