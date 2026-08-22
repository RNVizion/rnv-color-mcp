#!/usr/bin/env python3
"""
RNV-GOLD-ALIGNMENT-TOOL-DO-NOT-SWEEP

rnv-color-mcp: put files where AI_ENGINEERING_PRACTICES.md 6 says they go.

    python up2.py            # apply, then verify
    python up2.py --check    # dry run, writes nothing
    python up2.py --verify   # verify only
    python up2.py --finish   # delete this file

Named up2.py because up.py is one of the files being moved. This script does
NOT move itself; it is the tool, and 6.3 says a delivery script committed for
provenance says so in its docstring. That is this paragraph.

WHAT MOVES

    up.py                 ->  scripts/up.py           delivery script (6.3)
    requirements-dev.txt  ->  tests/requirements-dev.txt   test dependencies
    conftest.py           ->  tests/conftest.py       test harness

Moved with `git mv`, so history follows the file.

Three references to requirements-dev.txt are rewritten in the same pass:
.github/workflows/tests.yml, .github/workflows/sync-hf.yml, README.md. A move
that leaves a reference behind is a broken build, not a tidier tree.

WHAT DELIBERATELY STAYS, AND WHY IT WAS TESTED RATHER THAN ASSUMED

  pytest.ini stays at the root. It is test-associated, so it looks like it
  belongs in tests/ -- but it carries `asyncio_mode = auto` and defines the
  rootdir. Moved into tests/, `python -m pytest` from the root loses both:
  MEASURED, 1 failed and 11 errors, every async auth test erroring. It stays.

  conftest.py DOES move, and its own docstring said it should not. It read
  "pytest loads a root conftest.py first, which makes this the correct place
  for it." Measured with it in tests/: 32 passed. The ordering claim is true;
  the placement conclusion did not follow, because a tests/conftest.py is also
  loaded before the modules in tests/ are imported. The docstring is corrected
  in this pass rather than left asserting a rule the layout no longer follows.

  tests/smoke_test.py, tests/server_test.py and tests/gen_test_key.py stay in
  tests/. They are never collected -- `--collect-only` returns only the four
  test_*.py files -- and by the placement table they read as scripts. They are
  test-associated, and test-associated files belong with the tests. Recorded
  here so their exclusion is not read as an oversight.

  api.py, server.py, server.json, glama.json, the Dockerfile and the ignore
  files stay at the root: they are the application and its manifests, not
  scripts.

NOT COMMITTED. The working tree is left for review.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

# (source, destination, why, required). `required=False` means the file may
# legitimately be absent -- up.py is deleted by its own --finish, so a tree
# without it is further along, not unexpected.
MOVES = (
    ("up.py", "scripts/up.py",
     "delivery script -- 6.3: a delivery script in the repository root is misfiled",
     False),
    ("requirements-dev.txt", "tests/requirements-dev.txt",
     "test dependencies belong with the tests", True),
    ("conftest.py", "tests/conftest.py",
     "test harness; proven to work from tests/ -- 32 passed", True),
)

# (file, old, new). Every reference to the moved requirements file.
REWRITES = (
    (".github/workflows/tests.yml",
     "pip install -r requirements-dev.txt",
     "pip install -r tests/requirements-dev.txt"),
    (".github/workflows/sync-hf.yml",
     "pip install -r requirements-dev.txt",
     "pip install -r tests/requirements-dev.txt"),
    ("README.md",
     "pip install -r requirements-dev.txt",
     "pip install -r tests/requirements-dev.txt"),
)

STAYS = (
    ("pytest.ini", "carries asyncio_mode and defines the rootdir; moved into "
                   "tests/ the suite gives 1 failed and 11 errors -- measured"),
    ("tests/smoke_test.py", "never collected, but test-associated -- stays with the tests"),
    ("tests/server_test.py", "never collected, but test-associated -- stays with the tests"),
    ("tests/gen_test_key.py", "test key generator; referenced by SECURITY.md at its "
                              "current path"),
    ("api.py", "application module, not a script"),
    ("server.py", "application entry point"),
    ("server.json", "MCP registry manifest -- root by convention"),
    ("glama.json", "registry manifest -- root by convention"),
    ("Dockerfile", "build definition -- root by convention"),
)

CONFTEST_OLD = """server.py builds its auth provider at import time from environment variables,
so the environment must be set BEFORE server is imported. pytest loads a
root conftest.py first, which makes this the correct place for it."""

CONFTEST_NEW = """server.py builds its auth provider at import time from environment variables,
so the environment must be set BEFORE server is imported. A conftest.py is
loaded before the modules beside it are imported, which is what makes this
work.

This file used to sit at the repository root and say that a ROOT conftest.py
was therefore the correct place for it. The ordering claim was true; the
placement conclusion did not follow. Measured from tests/: 32 passed. It lives
with the tests it serves. If a test is ever added outside tests/, this has to
move back up -- that is the condition, not the directory."""


def sh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True)


def tracked(rel: str) -> bool:
    return sh("git", "ls-files", "--error-unmatch", rel).returncode == 0


def refuse_unexpected_base() -> str:
    """Fingerprint the tree. A half-applied move is worse than a refused one."""
    if not (ROOT / ".git").exists():
        raise SystemExit("ABORT: not a git repository. Run from the repo root.")
    if sh("git", "rev-parse", "--show-toplevel").stdout.strip() != str(ROOT.resolve()):
        raise SystemExit("ABORT: run this from the repository root, not a subdirectory.")

    done = [src for src, dst, _, req in MOVES
            if req and tracked(dst) and not tracked(src)]
    todo = [src for src, dst, _, req in MOVES if req and tracked(src)]
    if done and todo:
        raise SystemExit(
            f"ABORT: half applied. Already moved: {done}. Still at root: {todo}. "
            f"Resolve by hand rather than letting this guess.")
    if done and not todo:
        return "already-applied"

    missing = [src for src, _, _, req in MOVES if req and not tracked(src)]
    if missing:
        raise SystemExit(
            f"ABORT: expected these at the root and git does not track them: "
            f"{missing}. This is not the tree this script was built against.")
    return "pending"


def do_moves(check: bool) -> int:
    moved = 0
    for src, dst, why, req in MOVES:
        if not tracked(src):
            if not req and not tracked(dst):
                print(f"     {src} -- not present; already deleted by its "
                      f"own --finish, so nothing to move")
            else:
                print(f"     {src} -> already at {dst}")
            continue
        if check:
            print(f"     would move {src} -> {dst}   ({why})")
            moved += 1
            continue
        (ROOT / dst).parent.mkdir(parents=True, exist_ok=True)
        proc = sh("git", "mv", src, dst)
        if proc.returncode != 0:
            raise SystemExit(f"ABORT: git mv {src} {dst} failed:\n{proc.stderr}")
        print(f"     {src} -> {dst}   ({why})")
        moved += 1
    return moved


def do_rewrites(check: bool) -> int:
    """Rewrite every reference to the moved requirements file.

    Exact-match and count-checked: a reference that matches more than once, or
    not at all, aborts rather than guessing which one was meant.
    """
    n = 0
    for rel, old, new in REWRITES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"ABORT: {rel} not found; cannot update its reference.")
        text = path.read_text(encoding="utf-8")
        if new in text and old not in text.replace(new, ""):
            print(f"     {rel}: already points at tests/")
            continue
        hits = text.count(old)
        if hits != 1:
            raise SystemExit(
                f"ABORT: expected exactly 1 '{old}' in {rel}, found {hits}. "
                f"Scoping it by hand is safer than guessing.")
        if check:
            print(f"     would rewrite {rel}: {old} -> {new}")
        else:
            path.write_text(text.replace(old, new), encoding="utf-8")
            print(f"     {rel}: {old} -> {new}")
        n += 1
    return n


def do_conftest_docstring(check: bool) -> bool:
    """The moved file said it belonged where it no longer is."""
    path = ROOT / "tests" / "conftest.py"
    if not path.exists():
        path = ROOT / "conftest.py"
    text = path.read_text(encoding="utf-8")
    if CONFTEST_NEW.splitlines()[3].strip() in text:
        print("     conftest docstring: already corrected")
        return False
    if CONFTEST_OLD not in text:
        raise SystemExit(
            "ABORT: the conftest docstring is not the text this expects. It may "
            "have been edited; correct it by hand rather than letting this "
            "rewrite something it does not recognise.")
    if check:
        print("     would correct the conftest placement docstring")
        return True
    path.write_text(text.replace(CONFTEST_OLD, CONFTEST_NEW, 1), encoding="utf-8")
    print("     conftest docstring corrected: it no longer claims the root")
    return True


def verify() -> int:
    print("\nverifying\n")
    failures = []

    for src, dst, _, req in MOVES:
        if not req and not tracked(src) and not tracked(dst):
            continue
        if tracked(src):
            failures.append(f"{src} is still tracked at the root")
        if not tracked(dst):
            failures.append(f"{dst} is not tracked")
    if not failures:
        print("  every move landed, and git tracks the new paths")

    # No reference may still point at the old location.
    stale = []
    listing = sh("git", "ls-files").stdout.split()
    for rel in listing:
        path = ROOT / rel
        if path.suffix.lower() not in (".yml", ".yaml", ".md", ".txt", ".py", ".json"):
            continue
        if rel in ("scripts/up.py", Path(__file__).name):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in re.finditer(r"(?<!tests/)requirements-dev\.txt", text):
            line = text.count("\n", 0, m.start()) + 1
            stale.append(f"{rel}:{line}")
    if stale:
        failures.append("references still pointing at the old path: " + ", ".join(stale))
    else:
        print("  no reference still points at the old requirements-dev.txt")

    if not (ROOT / "pytest.ini").exists():
        failures.append("pytest.ini left the root -- it carries asyncio_mode")
    else:
        print("  pytest.ini is still at the root, as intended")

    proc = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                          cwd=str(ROOT), capture_output=True, text=True)
    # -q prints "tests/test_auth.py: 12" per file, not one id per line. A
    # pattern fitted to the id form counts zero and reads as "nothing to
    # collect" while the suite runs fine -- so parse the form it actually
    # emits, and assert the number is not zero.
    per_file = re.findall(r"^(tests/\S+\.py): (\d+)$", proc.stdout, re.M)
    collected = sum(int(n) for _, n in per_file)
    if not per_file:
        collected = len(re.findall(r"^tests/\S+::", proc.stdout, re.M))
    print(f"  collection: {collected} tests across {len(per_file) or '?'} files")
    if proc.returncode != 0:
        failures.append("pytest could not collect after the move")
    if collected == 0:
        failures.append("collection returned zero -- either the move broke it, "
                        "or this counter is reading the wrong output format")

    print("\n--- full suite ---")
    proc = subprocess.run([sys.executable, "-m", "pytest"],
                          cwd=str(ROOT), capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    line = [l for l in out.splitlines() if " passed" in l or " failed" in l]
    print(line[-1] if line else out.strip()[-300:])
    if proc.returncode != 0:
        failures.append("the suite does not pass after the move")

    print("\n  left alone, deliberately:")
    for rel, why in STAYS:
        print(f"     {rel:<26} {why}")

    if failures:
        print("\nNOT CLEAN:")
        for f in failures:
            print("   ", f)
        print("\nNothing was reverted. Fix and re-run.")
        return 1
    print("\nPASS -- everything moved, every reference followed, the suite is green.")
    print("Nothing was committed. The working tree is yours to review.")
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
    parser.add_argument("--check", action="store_true",
                        help="dry run; writes nothing")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--finish", action="store_true")
    args = parser.parse_args()

    if args.finish:
        finish()
        return 0

    state = refuse_unexpected_base()
    if args.verify:
        return verify()

    if state == "already-applied":
        print("Everything is already in place. Re-running changes nothing.\n")
        return verify()

    print("rnv-color-mcp: file placement, per AI_ENGINEERING_PRACTICES 6\n")
    if args.check:
        print("  DRY RUN -- nothing will be written\n")
    print("  moves:")
    do_moves(args.check)
    print("\n  references:")
    do_rewrites(args.check)
    print("\n  docstring:")
    do_conftest_docstring(args.check)

    if args.check:
        print("\n  would leave alone:")
        for rel, why in STAYS:
            print(f"     {rel:<26} {why}")
        print("\nDRY RUN complete. Nothing was written.")
        return 0
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
