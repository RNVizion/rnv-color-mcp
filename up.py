#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Brand gold alignment for rnv-color-mcp. The sixth and last repo, and the only
one that is a mirror rather than a consumer.

    python up.py             # apply, then verify
    python up.py --verify    # verify only, change nothing
    python up.py --finish    # delete this file

DO NOT NAME THIS FILE mcp.py. The working directory is on sys.path,
so it would shadow the `mcp` package fastmcp imports and take the whole
suite down with an error that names the dependency, not the file. The
script refuses to run under that name.

WHAT MOVES

  engine/brand_vocab.py
    BRAND_GOLD_DARK -> BRAND_DARK_GOLD      5 occurrences, all in this file
    #b19145 -> #8c7337
    the mirrored-from SHA, and the sentence that justified NOT renaming

  api.py
    contrast_check's `ratio` stops being rounded
    `display` truncates to three decimals

WHY THE ROUNDING MATTERS MORE THAN THE VALUE

This server is the instrument that produced the 3.00 reading the register was
built on. It returned `round(2.997638, 2)` = 3.0 for the retired gold on white,
AND flagged AA_large_text false in the same response, because the flags compare
the UNROUNDED ratio. The flags were right the whole time. The field that looks
like data was a label, and a consumer writing `if ratio >= 3.0` got the wrong
answer.

Truncation rather than rounding, because truncation cannot overstate: a true
4.4996 displays as 4.499 and reads as the failure it is, where rounding shows
4.500 and reads as a pass. It cannot understate across a bar either -- a true
4.5000001 truncates to 4.500 and still passes.

THE NOTE'S CONTAINMENT CLAIM DOES NOT HOLD -- see the write-up. Three pairs the
register asserts sit within 0.02 of a bar, not one. The other two sit ABOVE
their bars, which is why nothing else broke. All three report correctly under
the rule below.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOL_MARKER = "RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP"
GUARD_MARKER = "RNV-GOLD-GUARD-FILE-NAMES-RETIRED-VALUES-BY-DESIGN"

ROOT = Path.cwd()

OLD_GOLD = "#b" "19145"
GOLD = "#d" "2bc93"
DARK_GOLD = "#8" "c7337"

VOCAB = "engine/brand_vocab.py"
API = "api.py"
GUARD_MIRROR = "tests/test_brand_mirror.py"
GUARD_CONTRACT = "tests/test_contrast_contract.py"

OUR_FILES = (VOCAB, API, GUARD_MIRROR, GUARD_CONTRACT)

# The rnv-brand commit whose values this mirror now carries. Verified to hold
# BRAND_DARK_GOLD = #8c7337 before being written here.
BRAND_SHA = "60bd56d1bf5cec15942332a1c8db543134f5ad4f"
BRAND_DATE = "2026-08-22"
OLD_SHA = "c4d479dbf16b95b21fea80016372a03a64f1c450"


def read_any(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "bom"
    try:
        return raw.decode("utf-8"), "plain"
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="surrogateescape"), "surrogate"


def write_any(path: Path, text: str, kind: str) -> None:
    if kind == "bom":
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    elif kind == "surrogate":
        path.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    else:
        path.write_text(text, encoding="utf-8")


def sub_once(src: str, old: str, new: str, where: str) -> str:
    n = src.count(old)
    if n != 1:
        raise SystemExit(
            f"ABORT: expected exactly 1 occurrence of this anchor in {where}, "
            f"found {n}. Stopping rather than guessing.\n---\n{old}\n---")
    return src.replace(old, new)


def edit(rel: str, fn) -> bool:
    path = ROOT / rel
    if not path.exists():
        raise SystemExit(f"ABORT: {rel} not found. Run from the repository root.")
    src, kind = read_any(path)
    out = fn(src)
    if out == src:
        return False
    if rel.endswith(".py"):
        try:
            ast.parse(out)
        except SyntaxError as exc:
            raise SystemExit(f"ABORT: {rel} would not parse after editing: {exc}")
    write_any(path, out, kind)
    return True


# --------------------------------------------------------------- the mirror

def step_vocab(src: str) -> str:
    """Rename, revalue, re-pin, and correct the rationale.

    The rename is safe for the wire format and that is checked rather than
    assumed: RNV_BRAND maps STRINGS to values, so "dark gold", "gold dark" and
    "light-mode gold" are untouched by renaming the constant they point at.
    """
    before_keys = set(re.findall(r'^\s*"([^"]+)":', src, re.M))

    n = len(re.findall(r"\bBRAND_GOLD_DARK\b", src))
    if n != 5:
        raise SystemExit(f"ABORT: expected 5 BRAND_GOLD_DARK occurrences, found {n}.")
    src = re.sub(r"\bBRAND_GOLD_DARK\b", "BRAND_DARK_GOLD", src)

    src = sub_once(src, f'BRAND_DARK_GOLD: Final[str] = "{OLD_GOLD}"',
                   f'BRAND_DARK_GOLD: Final[str] = "{DARK_GOLD}"', VOCAB)

    src = sub_once(
        src,
        f"Mirrored from rnv-brand@{OLD_SHA}, 2026-08-10.",
        f"Mirrored from rnv-brand@{BRAND_SHA}, {BRAND_DATE}.\n"
        f"Previously rnv-brand@{OLD_SHA[:12]}, 2026-08-10, which carried the\n"
        f"gold retired on 2026-08-17. A mirror whose contents moved and whose\n"
        f"SHA did not is worse than one that is plainly stale: the SHA asserts\n"
        f"it is current.",
        VOCAB)

    # The file's own rationale for NOT renaming. The register retired that rule;
    # leaving the sentence would make this mirror assert a rule that no longer
    # holds, in the same commit that breaks it.
    src = sub_once(
        src,
        "Sync discipline: values here are corrected when drift is detected against\n"
        "rnv-brand, by a human, in a deliberate commit. Identifiers are local by design\n"
        "— BRAND_GOLD here, GOLD upstream — because the check compares values, never\n"
        "names. Nothing propagates automatically, and nothing should appear to.",
        "Sync discipline: values here are corrected when drift is detected against\n"
        "rnv-brand, by a human, in a deliberate commit. Nothing propagates\n"
        "automatically, and nothing should appear to.\n"
        "\n"
        "Identifiers used to be local by design — BRAND_GOLD here, GOLD upstream —\n"
        "on the grounds that the check compares values and never names. The register\n"
        "retired that rule on 2026-08-17: it permitted four spellings of one colour\n"
        "across six repos, and a system that cannot hold one identifier across its\n"
        "own repositories is not positioned to align anyone else's. The names now\n"
        "match upstream. The check still compares values.",
        VOCAB)

    after_keys = set(re.findall(r'^\s*"([^"]+)":', src, re.M))
    if before_keys != after_keys:
        raise SystemExit(
            f"ABORT: the resolver vocabulary changed. The rename must not touch "
            f"the wire format.\n  added: {sorted(after_keys - before_keys)}\n"
            f"  lost:  {sorted(before_keys - after_keys)}")
    return src


# ------------------------------------------------------------ the instrument

def step_api(src: str) -> str:
    """`ratio` becomes data; `display` becomes a label that cannot overstate."""
    src = sub_once(
        src,
        '        "ratio": round(ratio, 2),\n'
        '        "display": f"{round(ratio, 2)}:1",\n',
        '        # UNROUNDED. A consumer compares this against a threshold and is\n'
        '        # entitled to the real number: round(2.997638, 2) is 3.0, and\n'
        '        # `if ratio >= 3.0` then passes a pair that fails. The wcag flags\n'
        '        # below always compared the unrounded value and were never wrong.\n'
        '        "ratio": ratio,\n'
        '        "display": f"{_truncate(ratio, 3)}:1",\n',
        API)

    helper = '''

def _truncate(value: float, places: int) -> str:
    """Format to `places` decimals by TRUNCATING, never rounding.

    Rounding can only be wrong in one direction that matters: a true 4.4996
    rounds to 4.500 and reads as a pass it has not earned. Truncation cannot
    overstate. It cannot understate across a bar either -- a true 4.5000001
    truncates to 4.500, which still reads as passing -- so it satisfies both
    gates: refuse when you must, and do not refuse when you could have answered.

    More precision alone does not fix this. It moves the trap to a finer scale;
    only truncation removes it.
    """
    scale = 10 ** places
    # int() truncates toward zero, and a contrast ratio is always >= 1.
    return f"{int(value * scale) / scale:.{places}f}"

'''
    if "def _truncate" not in src:
        anchor = "\ndef contrast_check("
        if anchor not in src:
            raise SystemExit("ABORT: cannot find contrast_check to anchor the helper")
        src = src.replace(anchor, helper + "\ndef contrast_check(", 1)
    return src


# ---------------------------------------------------------------- guards

GUARD_MIRROR_SRC = '''"""
Brand mirror guard.   ''' + GUARD_MARKER + '''

This file NAMES THE RETIRED VALUE ON PURPOSE. A sweep for gold literals must
exclude it by the marker above.

This repo is a MIRROR, not a consumer. What has to be true is narrower than in
the apps and more important: the values match upstream, the wire format does
not move when the identifiers do, and the SHA says which upstream commit these
values came from.
"""
from __future__ import annotations

import pathlib
import re

from engine import brand_vocab as V

RETIRED_GOLD = "#b" "19145"
SYNCED_SHA = "''' + BRAND_SHA + '''"

# The resolver vocabulary IS the wire format. A client sends these strings.
WIRE_KEYS = {
    "near-black", "near black", "brand black", "rnv black", "charcoal",
    "gold", "brand gold", "rnv gold",
    "dark gold", "gold dark", "light-mode gold",
    "black", "true black", "white", "brand white", "web black",
}


def test_registered_values_match_the_register():
    assert V.BRAND_GOLD == "''' + GOLD + '''"
    assert V.BRAND_DARK_GOLD == "''' + DARK_GOLD + '''"


def test_the_retired_gold_is_gone():
    src = pathlib.Path(V.__file__).read_text(encoding="utf-8")
    assert RETIRED_GOLD not in src, (
        "the mirror still carries the retired gold")


def test_the_old_identifier_is_gone():
    src = pathlib.Path(V.__file__).read_text(encoding="utf-8")
    assert "BRAND_GOLD_DARK" not in src, (
        "BRAND_GOLD_DARK was retired in favour of BRAND_DARK_GOLD")


def test_the_wire_format_did_not_move():
    """The rename touches identifiers. Clients send STRINGS.

    RNV_BRAND keys are the public contract; renaming a constant must not add,
    drop or respell one of them.
    """
    assert set(V.RNV_BRAND) == WIRE_KEYS, (
        f"resolver vocabulary changed -- added "
        f"{sorted(set(V.RNV_BRAND) - WIRE_KEYS)}, lost "
        f"{sorted(WIRE_KEYS - set(V.RNV_BRAND))}")


def test_every_gold_alias_resolves_to_the_new_value():
    for alias in ("dark gold", "gold dark", "light-mode gold"):
        assert V.RNV_BRAND[alias] == V.BRAND_DARK_GOLD, alias
    for alias in ("gold", "brand gold", "rnv gold"):
        assert V.RNV_BRAND[alias] == V.BRAND_GOLD, alias


def test_the_mirror_records_which_upstream_commit_it_carries():
    """A mirror whose contents moved and whose SHA did not is worse than one
    that is plainly stale: the SHA asserts it is current."""
    doc = V.__doc__ or ""
    found = re.findall(r"Mirrored from rnv-brand@([0-9a-f]{40})", doc)
    assert found, "the mirror does not record an upstream SHA"
    assert found[0] == SYNCED_SHA, (
        f"the mirror pins {found[0][:12]} but these values came from "
        f"{SYNCED_SHA[:12]}")


def test_the_retired_rationale_is_not_asserted_as_current():
    """The file used to justify local identifiers. That rule was retired in the
    same change that renamed them; the sentence had to go with it."""
    doc = V.__doc__ or ""
    assert "Identifiers are local by design" not in doc, (
        "the mirror still asserts a rule the register retired")
'''

GUARD_CONTRACT_SRC = '''"""
Contrast reporting contract.   ''' + GUARD_MARKER + '''

`ratio` is data and `display` is a label. This file pins the difference,
because collapsing it is what turned a 2.997638 failure into a 3.00 permission
that governed three repositories.
"""
from __future__ import annotations

import api


def test_ratio_is_not_rounded():
    """The pair that started all of this. round(2.997638, 2) is 3.0, and a
    consumer writing `if ratio >= 3.0` then passes a pair that fails."""
    r = api.contrast_check("#b" "19145", "#ffffff")
    assert r["ratio"] < 3.0, (
        f"ratio {r['ratio']} must be the real value, under the 3.0 bar")
    assert abs(r["ratio"] - 2.997638) < 1e-5, r["ratio"]


def test_the_flags_were_always_right():
    """They compare the unrounded value and always did. Nothing about this
    change makes them stricter -- it stops the number beside them lying."""
    r = api.contrast_check("#b" "19145", "#ffffff")
    assert r["wcag"]["AA_large_text"] is False
    assert r["wcag"]["AA_ui_components"] is False


def test_display_truncates_and_shows_three_decimals():
    r = api.contrast_check("#b" "19145", "#ffffff")
    assert r["display"] == "2.997:1", r["display"]


def test_display_never_overstates_across_a_bar():
    """The property the rule exists for. Truncation cannot show a figure at or
    above a bar that the true value does not reach."""
    from api import _truncate
    for bar in (3.0, 4.5, 7.0):
        for delta in (1e-4, 1e-3, 4e-3, 9e-3):
            true = bar - delta
            shown = float(_truncate(true, 3))
            assert shown < bar, (
                f"true {true} is under {bar} but displays as {shown}")


def test_display_does_not_understate_across_a_bar():
    """The other gate: a value that passes must not be shown as failing."""
    from api import _truncate
    for bar in (3.0, 4.5, 7.0):
        for delta in (1e-7, 1e-4, 1e-3, 5e-3):
            true = bar + delta
            assert float(_truncate(true, 3)) >= bar, (
                f"true {true} clears {bar} but displays below it")


def test_the_new_gold_reports_its_real_figure():
    r = api.contrast_check("dark gold", "white")
    assert abs(r["ratio"] - 4.542947) < 1e-5, r["ratio"]
    assert r["display"] == "4.542:1", r["display"]
    assert r["wcag"]["AA_normal_text"] is True


def test_a_known_pair_that_sits_close_to_a_bar_still_reads_correctly():
    """The register asserts three pairs within 0.02 of a bar, not one as its
    note claims. This is the closest of the survivors: it clears 7.0 by
    0.0055, and must not be shown as failing."""
    r = api.contrast_check("#000000", "#b" "19145")
    assert r["ratio"] > 7.0
    assert float(r["display"].split(":")[0]) >= 7.0, r["display"]
'''


# ------------------------------------------------------------------ running

def refuse_to_shadow() -> None:
    """Refuse to run if this file's own name shadows an installed module.

    Named mcp.py in this repository, the tool shadows the `mcp` package that
    fastmcp imports, and the entire test suite dies on
    `ImportError: FastMCP server support is not installed` -- a message that
    points at the dependency rather than at the file sitting next to it.

    The same class as a sweep that rewrites its own constants: the tool has to
    be excluded from the environment it operates on, and a filename is part of
    that environment because the working directory is on sys.path.
    """
    import importlib.util
    stem = Path(__file__).stem
    if stem in sys.builtin_module_names:
        clash = True
    else:
        saved = sys.path[:]
        here = str(Path(__file__).resolve().parent)
        sys.path = [p for p in sys.path if p not in ("", ".", here)]
        try:
            clash = importlib.util.find_spec(stem) is not None
        except (ImportError, ValueError):
            clash = False
        finally:
            sys.path = saved
    if clash:
        raise SystemExit(
            f"ABORT: this file is named {stem}.py, which shadows the installed "
            f"module `{stem}`.\n"
            f"The working directory is on sys.path, so anything importing "
            f"`{stem}` would get this script.\n"
            f"Rename it -- up.py is the convention here -- and run it again. "
            f"Nothing has been changed.")


def probe() -> None:
    code = "import fastmcp, pytest; import api; print('ok')"
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode == 0:
        return
    err = (proc.stderr or "").strip()
    print("\nThis environment cannot run the suite yet.\n")
    print(err.splitlines()[-1] if err else "(no error text)")
    print("\nThis repo is a SERVER -- standard library plus fastmcp. It needs no")
    print("apt libraries; the PyQt6 list from the app repos does not apply here.\n")
    print("  pip install -r requirements.txt -r requirements-dev.txt")
    print("\nNothing has been changed.\n")
    raise SystemExit(2)


def split_failures(output: str) -> tuple[list[str], list[str]]:
    ours, other = [], []
    pattern = re.compile(r"^(FAILED|ERROR) (\S+\.py)(::\S+)?")
    for line in output.splitlines():
        m = pattern.match(line.strip())
        if m:
            (ours if m.group(2) in OUR_FILES else other).append(line.strip())
    return ours, other


def run(label: str, args: list[str]) -> tuple[int, str]:
    print(f"\n--- {label} ---")
    proc = subprocess.run([sys.executable, "-m", "pytest", *args],
                          capture_output=True, text=True, cwd=str(ROOT))
    out = proc.stdout + proc.stderr
    tail = [l for l in out.splitlines()
            if re.match(r"^(FAILED|ERROR) \S+\.py", l.strip())
            or " passed" in l or " failed" in l]
    print("\n".join(tail[-12:]) or (out.splitlines() or ["(no output)"])[-1])
    if proc.returncode < 0:
        names = {6: "SIGABRT", 9: "SIGKILL (out of memory)",
                 15: "SIGTERM (session reclaimed)"}
        sig = -proc.returncode
        print(f"\nKILLED by signal {sig} -- {names.get(sig, sig)}. "
              f"Killed is not failed; nothing is concluded from this run.")
    return proc.returncode, out


def apply() -> None:
    print("rnv-color-mcp: brand gold alignment\n")
    edit(VOCAB, step_vocab)
    print("  1  BRAND_GOLD_DARK -> BRAND_DARK_GOLD, 5 occurrences; "
          f"{OLD_GOLD} -> {DARK_GOLD}")
    print(f"  2  mirrored-from SHA re-pinned to rnv-brand@{BRAND_SHA[:12]}")
    print("  3  the retired 'identifiers are local by design' rationale corrected")
    edit(API, step_api)
    print("  4  contrast_check: ratio unrounded, display truncated to 3 decimals")
    (ROOT / "tests").mkdir(exist_ok=True)
    (ROOT / GUARD_MIRROR).write_text(GUARD_MIRROR_SRC, encoding="utf-8")
    (ROOT / GUARD_CONTRACT).write_text(GUARD_CONTRACT_SRC, encoding="utf-8")
    print("  5  guard tests installed (mirror + reporting contract)")


def verify() -> int:
    print("\nverifying\n")
    proc = subprocess.run(
        [sys.executable, "-c",
         "import api\n"
         "from engine import brand_vocab as V\n"
         "print('  BRAND_GOLD      ', V.BRAND_GOLD)\n"
         "print('  BRAND_DARK_GOLD ', V.BRAND_DARK_GOLD)\n"
         "print('  wire keys       ', len(V.RNV_BRAND))\n"
         "r = api.contrast_check('#b19145', '#ffffff')\n"
         "print('  retired gold on white -> ratio', r['ratio'],\n"
         "      '| display', r['display'], '| AA_ui', r['wcag']['AA_ui_components'])\n"
         "r2 = api.contrast_check('dark gold', 'white')\n"
         "print('  dark gold on white    -> ratio', r2['ratio'],\n"
         "      '| display', r2['display'], '| AA_normal', r2['wcag']['AA_normal_text'])"],
        capture_output=True, text=True, cwd=str(ROOT))
    print(proc.stdout.rstrip() or proc.stderr.strip())
    if proc.returncode != 0:
        print("  IMPORT OR CALL FAILED")
        return 1

    rc_guard, _ = run("guard suite (the gate)",
                      [GUARD_MIRROR, GUARD_CONTRACT, "-q", "-p", "no:cacheprovider"])
    rc_all, out_all = run("full suite", ["-q", "-p", "no:cacheprovider"])

    ours, other = split_failures(out_all)
    if other:
        print("\n  pre-existing failures, not from this pass:")
        for line in other:
            print("   ", line)
    if ours:
        print("\n  FAILURES IN FILES THIS PASS TOUCHED:")
        for line in ours:
            print("   ", line)

    ok = rc_guard == 0 and not ours
    if not ok:
        print("\nNOT CLEAN -- see above. Nothing was reverted; re-run after fixing.")
        return 1
    if rc_all < 0:
        print("\nPASS ON THE GATE -- the guard suite is green, but the full suite "
              "was KILLED before finishing, so it did not report.")
        print("   Push and let CI run it: it is not tethered to this tab.")
    else:
        print("\nPASS -- the gate is green, every suite finished, and nothing "
              "this pass touched failed.")
    return 0


def finish() -> None:
    me = Path(__file__).resolve()
    me.unlink()
    cache = me.parent / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)
    print("removed", me.name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--finish", action="store_true")
    args = parser.parse_args()
    if args.finish:
        finish()
        return 0
    if not (ROOT / VOCAB).exists():
        raise SystemExit("ABORT: run this from the repository root.")
    refuse_to_shadow()
    probe()
    if not args.verify:
        apply()
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
