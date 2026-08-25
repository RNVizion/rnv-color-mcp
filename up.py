#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

Re-pin the brand mirror in rnv-color-mcp from rnv-brand@60bd56d1 (2026-08-22)
to rnv-brand@361c0e2 (2026-08-24).

    python up.py             # apply, then verify
    python up.py --verify    # verify only, change nothing
    python up.py --finish    # delete this file

DO NOT NAME THIS FILE mcp.py. The working directory is on sys.path, so it
would shadow the `mcp` package fastmcp imports and take the whole suite down
with an error that names the dependency, not the file. The script refuses to
run under that name.

WHAT MOVES

  engine/brand_vocab.py   the mirrored-from SHA, plus a paragraph recording
                          what upstream gained after the old pin that this
                          file deliberately does not carry
  tests/test_brand_mirror.py   SYNCED_SHA, so the guard still guards

WHAT DOES NOT MOVE, AND WHY THAT IS THE POINT

No value changes. Every one of the six constants and all sixteen RNV_BRAND
keys and values diff clean between the two pins -- verified by importing
upstream's engine/brand.py and comparing objects, not by reading the diff.

So this re-pin buys TRUTH IN LABELLING and nothing else. That is worth a
commit on its own terms: the file's own docstring says a mirror whose
contents moved and whose SHA did not is worse than one that is plainly
stale, because the SHA asserts it is current. The converse costs something
too -- a pin two commits behind invites the next reader to re-derive the
comparison this commit already did.

WHAT UPSTREAM GAINED THAT THIS MIRROR DOES NOT CARRY

  BRAND_STILL_GOLD    #9b907a   the seventh permanent, registered not derived
  BRAND_STANDBY_GOLD  #ae986f   lighten(BRAND_GOLD, -36)

Neither is in upstream's RNV_BRAND, which is the only thing this file
mirrors. Upstream's own resolver refuses "still gold" exactly as this one
does; the mirror is faithful, not lagging. That asymmetry -- a colour in
PERMANENT and not in RNV_BRAND -- is upstream's to rule on, and it has been
sent back. Nothing here should anticipate the ruling.

WHAT IS DELIBERATELY NOT IN THIS SCRIPT

Upstream renamed BRAND_GOLD_HOVER to BRAND_HOVER_GOLD in 996eade (2026-08-23)
under a new naming convention. This mirror does not carry a hover gold in any
spelling, so the rename cannot reach it. The five desktop apps DO carry it,
and they are not being renamed yet -- BRAND_COLORS.md rev 18 still publishes
the old spelling, and the convention has no spelling for the mode-qualified
state golds that two of the apps ship. Renaming ahead of that ruling would
mean renaming twice.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

TOOL_MARKER = "RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP"

OLD_SHA = "60bd56d1bf5cec15942332a1c8db543134f5ad4f"
NEW_SHA = "361c0e2a4b0ecb9109f358b5714ce8a630b75d69"
NEW_DATE = "2026-08-24"

VOCAB = "engine/brand_vocab.py"
GUARD = "tests/test_brand_mirror.py"

# The six constants and the resolver map, as they must read at the new pin.
EXPECTED_VALUES = {
    "BRAND_GOLD": "#d2bc93",
    "BRAND_DARK_GOLD": "#8c7337",
    "BRAND_BLACK": "#1a1a1a",
    "TRUE_BLACK": "#000000",
    "WHITE": "#ffffff",
    "WEB_BLACK": "#0a0a0f",
}
EXPECTED_WIRE_KEYS = 16

OLD_PIN_BLOCK = """Mirrored from rnv-brand@60bd56d1bf5cec15942332a1c8db543134f5ad4f, 2026-08-22.
Previously rnv-brand@c4d479dbf16b, 2026-08-10, which carried the
gold retired on 2026-08-17. A mirror whose contents moved and whose
SHA did not is worse than one that is plainly stale: the SHA asserts
it is current."""

NEW_PIN_BLOCK = """Mirrored from rnv-brand@361c0e2a4b0ecb9109f358b5714ce8a630b75d69, 2026-08-24.
Previously rnv-brand@60bd56d1bf5c, 2026-08-22, and before that
rnv-brand@c4d479dbf16b, 2026-08-10, which carried the gold retired on
2026-08-17. A mirror whose contents moved and whose SHA did not is worse
than one that is plainly stale: the SHA asserts it is current.

Nothing this file carries moved between those two pins. The six constants
and every RNV_BRAND key and value diff clean against both; the re-pin buys
truth in labelling, not a corrected value.

WHAT UPSTREAM GAINED AFTER 60bd56d1 AND THIS FILE DELIBERATELY DOES NOT
CARRY: BRAND_STILL_GOLD (#9b907a, the seventh permanent, registered) and
BRAND_STANDBY_GOLD (#ae986f, derived). Neither is in upstream's RNV_BRAND,
so upstream's own resolver refuses "still gold" exactly as this one does.
The mirror is faithful, not lagging. If a future sync adds either constant
without adding the key, the resolver's behaviour is unchanged and this note
is the record of why; if upstream adds the KEY, the wire-format guard in
tests/test_brand_mirror.py fails until WIRE_KEYS is updated on purpose."""

OLD_GUARD_LINE = f'SYNCED_SHA = "{OLD_SHA}"'
NEW_GUARD_LINE = f'SYNCED_SHA = "{NEW_SHA}"'


# ------------------------------------------------------------------ plumbing
def _this_script() -> str:
    return os.path.relpath(
        os.path.realpath(__file__), os.path.realpath(os.getcwd())
    ).replace(os.sep, "/")


def refuse_to_shadow() -> None:
    """`mcp.py` in the working directory shadows the package fastmcp imports."""
    name = Path(__file__).name
    if name == "mcp.py":
        sys.exit(
            "refusing to run as mcp.py -- the working directory is on "
            "sys.path and this file would shadow the `mcp` package. "
            "Rename it to up.py and run again."
        )


def sub_once(src: str, old: str, new: str, where: str) -> str:
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"{where}: expected exactly 1 occurrence, found {n}")
    return src.replace(old, new)


class Tree:
    """Every edit lands here first. Disk is written only after all pass."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.files: dict[str, str] = {}

    def read(self, rel: str) -> str:
        if rel not in self.files:
            p = self.root / rel
            if not p.exists():
                raise SystemExit(f"missing file: {rel}")
            self.files[rel] = p.read_text(encoding="utf-8")
        return self.files[rel]

    def write(self, rel: str, text: str) -> None:
        self.files[rel] = text

    def flush(self) -> list[str]:
        touched = []
        for rel, text in self.files.items():
            p = self.root / rel
            if p.read_text(encoding="utf-8") != text:
                p.write_text(text, encoding="utf-8")
                touched.append(rel)
        return touched


# --------------------------------------------------------------------- steps
def step_vocab(tree: Tree) -> None:
    src = tree.read(VOCAB)
    if NEW_SHA in src:
        raise SystemExit(f"{VOCAB}: already pinned at {NEW_SHA[:7]} -- nothing to do")
    src = sub_once(src, OLD_PIN_BLOCK, NEW_PIN_BLOCK, f"{VOCAB} pin block")
    tree.write(VOCAB, src)


def step_guard(tree: Tree) -> None:
    src = tree.read(GUARD)
    src = sub_once(src, OLD_GUARD_LINE, NEW_GUARD_LINE, f"{GUARD} SYNCED_SHA")
    tree.write(GUARD, src)


def check_no_value_moved(tree: Tree) -> None:
    """The re-pin claims no value moved. Prove it from the post-edit text.

    Reads the tree, not the disk, so --check rehearses the real thing.
    """
    src = tree.read(VOCAB)
    for name, value in EXPECTED_VALUES.items():
        pat = rf'^{name}:\s*Final\[str\]\s*=\s*"{re.escape(value)}"'
        if not re.search(pat, src, re.M):
            raise SystemExit(f"{VOCAB}: {name} is not {value} after the edit")
    keys = re.findall(r'^\s{4}"([^"]+)":', src, re.M)
    if len(keys) != EXPECTED_WIRE_KEYS:
        raise SystemExit(
            f"{VOCAB}: RNV_BRAND has {len(keys)} keys, expected "
            f"{EXPECTED_WIRE_KEYS}. A re-pin must not move the wire format."
        )


def check_sha_is_stated_once(tree: Tree) -> None:
    """Two pins in one docstring is how a mirror starts lying quietly."""
    src = tree.read(VOCAB)
    found = re.findall(r"Mirrored from rnv-brand@([0-9a-f]{40})", src)
    if found != [NEW_SHA]:
        raise SystemExit(f"{VOCAB}: expected exactly one 40-char pin, found {found}")
    if OLD_SHA in src:
        raise SystemExit(
            f"{VOCAB}: the full old SHA survives. It should appear "
            f"abbreviated in the history line, never at full length."
        )
    guard = tree.read(GUARD)
    if guard.count(NEW_SHA) != 1 or OLD_SHA in guard:
        raise SystemExit(f"{GUARD}: SYNCED_SHA was not moved cleanly")


# ----------------------------------------------------------------- execution
def run(label: str, args: list[str]) -> tuple[int, str]:
    print(f"  {label} ...", flush=True)
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def verify() -> int:
    code, out = run("pytest", [sys.executable, "-m", "pytest", "-q"])
    tail = "\n".join(out.strip().splitlines()[-12:])
    print(tail)
    if code != 0:
        print("\nFAILED -- the suite is not green. Nothing was committed.")
    return code


def apply(check_only: bool) -> int:
    root = Path.cwd()
    if not (root / VOCAB).exists():
        raise SystemExit(
            "run this from the root of a rnv-color-mcp checkout "
            f"(no {VOCAB} here)"
        )
    tree = Tree(root)
    step_vocab(tree)
    step_guard(tree)
    check_no_value_moved(tree)
    check_sha_is_stated_once(tree)

    if check_only:
        print("--check: both edits compose and every guard passes. "
              "Nothing written.")
        return 0

    touched = tree.flush()
    print("wrote: " + ", ".join(touched) if touched else "no change needed")
    print(f"pinned at {NEW_SHA[:7]} ({NEW_DATE})\n")
    return verify()


def finish() -> None:
    me = Path(__file__).resolve()
    print(f"removing {me.name}")
    me.unlink()


def main() -> int:
    refuse_to_shadow()
    ap = argparse.ArgumentParser(description="re-pin the rnv-color-mcp brand mirror")
    ap.add_argument("--check", action="store_true",
                    help="rehearse every edit in memory, write nothing")
    ap.add_argument("--verify", action="store_true",
                    help="run the suite only, change nothing")
    ap.add_argument("--finish", action="store_true",
                    help="delete this script")
    args = ap.parse_args()

    if args.finish:
        finish()
        return 0
    if args.verify:
        return verify()
    return apply(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
