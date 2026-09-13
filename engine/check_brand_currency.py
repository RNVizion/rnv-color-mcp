#!/usr/bin/env python3
"""Compare the local brand-vocabulary mirror against upstream rnv-brand.

This is the only check in this repository that reads the artifact the mirror
claims to mirror. `tests/test_brand_mirror.py` compares the mirror to constants
that live beside it in the test file, which is a real check -- it catches an
edit to the mirror that nobody meant -- but it is scoped to one side of the
boundary and cannot see upstream at all. That gap ran from 2026-08-25 to
2026-09-12 with seven tests green and eleven keys missing.

Two modes, deliberately separate, because they are two different failures:

  --mode transcription   mirror vs upstream AT ITS OWN PINNED SHA.
                         A mismatch is a DEFECT of this repository: the mirror
                         says it carries that commit and does not. Runs in the
                         gated path.

  --mode currency        mirror keys vs upstream AT HEAD.
                         A difference is a QUEUE, not a defect: upstream moved
                         and the deliberate human re-pin has not happened yet.
                         Nothing in this repository became wrong. Runs only in
                         a scheduled job that gates nothing, so it can exit
                         non-zero and still block no one.

Upstream is parsed with `ast`, never imported. A guard that executes the code
it is guarding is not a guard, and this one runs against a remote file.

Network lives here and not in the test suite on purpose: `pytest` stays
offline and credential-free.
"""

from __future__ import annotations

import argparse
import ast
import sys
import urllib.error
import urllib.request

UPSTREAM_REPO = "RNVizion/rnv-brand"
UPSTREAM_FILE = "engine/brand.py"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
TIMEOUT = 30


def fetch(ref: str) -> str:
    url = RAW.format(repo=UPSTREAM_REPO, ref=ref, path=UPSTREAM_FILE)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        sys.exit(f"UNRESOLVED: upstream fetch failed, HTTP {e.code} for {url}")
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"UNRESOLVED: upstream unreachable ({e}) for {url}")


def extract_rnv_brand(source: str, where: str) -> dict[str, str]:
    """Pull RNV_BRAND out of upstream by parsing, not executing.

    Values are string literals or names bound to string literals at module
    level (BRAND_GOLD and friends). Anything else is refused by name rather
    than guessed at -- the resolver's own rule, applied to the guard.
    """
    tree = ast.parse(source, filename=where)
    literals: dict[str, str] = {}
    target: ast.Dict | None = None

    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        names = (
            [t.id for t in node.targets if isinstance(t, ast.Name)]
            if isinstance(node, ast.Assign)
            else ([node.target.id] if isinstance(node.target, ast.Name) else [])
        )
        value = node.value
        for name in names:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                literals[name] = value.value
            elif name == "RNV_BRAND" and isinstance(value, ast.Dict):
                target = value

    if target is None:
        sys.exit(f"UNRESOLVED: no RNV_BRAND dict found in {where}")

    out: dict[str, str] = {}
    for k, v in zip(target.keys, target.values):
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            sys.exit(f"UNRESOLVED: non-literal key in RNV_BRAND ({where})")
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            out[k.value] = v.value
        elif isinstance(v, ast.Name) and v.id in literals:
            out[k.value] = literals[v.id]
        else:
            sys.exit(f"UNRESOLVED: cannot resolve value for {k.value!r} ({where})")
    return out


def local_mirror() -> tuple[dict[str, str], str]:
    sys.path.insert(0, ".")
    from engine import brand_vocab as mirror  # noqa: E402

    import re

    found = re.findall(r"Mirrored from rnv-brand@([0-9a-f]{7,40})", mirror.__doc__ or "")
    if not found:
        sys.exit("UNRESOLVED: the mirror records no upstream SHA")
    return dict(mirror.RNV_BRAND), found[0]


def report(missing: dict[str, str], extra: dict[str, str], drift: list[str],
           up: dict[str, str], mine: dict[str, str]) -> None:
    if missing:
        print(f"\n  keys upstream has and the mirror does not ({len(missing)}):")
        for k in sorted(missing):
            print(f"    {k:<18} {up[k]}")
    if extra:
        print(f"\n  keys the mirror has and upstream does not ({len(extra)}):")
        for k in sorted(extra):
            print(f"    {k:<18} {mine[k]}")
    if drift:
        print(f"\n  value drift on shared keys ({len(drift)}):")
        for k in sorted(drift):
            print(f"    {k:<18} mirror {mine[k]}  upstream {up[k]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("transcription", "currency"), required=True)
    ap.add_argument("--ref", default="main", help="upstream ref for currency mode")
    args = ap.parse_args()

    mine, pinned_sha = local_mirror()
    ref = pinned_sha if args.mode == "transcription" else args.ref
    up = extract_rnv_brand(fetch(ref), f"{UPSTREAM_REPO}@{ref}:{UPSTREAM_FILE}")

    missing = {k: up[k] for k in up if k not in mine}
    extra = {k: mine[k] for k in mine if k not in up}
    drift = [k for k in mine if k in up and mine[k].lower() != up[k].lower()]

    print(f"mode={args.mode}  upstream={UPSTREAM_REPO}@{ref}")
    print(f"upstream keys={len(up)}  mirror keys={len(mine)}  pinned={pinned_sha[:7]}")

    if args.mode == "transcription":
        if not (missing or extra or drift):
            print("\nPASS: the mirror carries exactly the commit it says it carries.")
            return 0
        print("\nFAIL (defect): the mirror does not match its own pinned commit.")
        report(missing, extra, drift, up, mine)
        print("\nThis repository is wrong. Either the mirror was edited without")
        print("re-pinning, or SYNCED_SHA was moved without syncing the values.")
        return 1

    if not (missing or extra or drift):
        print("\nPASS: the mirror is current with upstream.")
        return 0
    print("\nBEHIND (queue): upstream has moved past the pinned mirror.")
    report(missing, extra, drift, up, mine)
    print("\nNothing in this repository is wrong and no publish is blocked.")
    print("The mirror is synced by a human, on purpose, in a deliberate commit:")
    print("  1. add the keys/values to engine/brand_vocab.py")
    print("  2. add the same keys to WIRE_KEYS in tests/test_brand_mirror.py")
    print("  3. re-pin SYNCED_SHA and the docstring SHA to the synced commit")
    print("\nUntil then the resolver refuses these names. If any of them is a")
    print("PERMANENT brand colour, that is worth doing now rather than later.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
