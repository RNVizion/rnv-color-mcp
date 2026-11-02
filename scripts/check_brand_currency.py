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
                         gated path. Since Phase 8.12 (2026-11-01) it reads the
                         register INSTALLED at the pin from
                         tests/requirements-dev.txt, as rnv_brand, and checks
                         that pip installed that commit. It makes no network
                         call, so it has no outage to tell from a defect.

  --mode currency        mirror keys vs upstream AT HEAD.
                         A difference is a QUEUE, not a defect: upstream moved
                         and the deliberate human re-pin has not happened yet.
                         Nothing in this repository became wrong. Runs only in
                         a scheduled job that gates nothing, so it can exit
                         non-zero and still block no one.

In currency mode upstream HEAD is fetched over HTTPS and parsed with `ast`,
never imported: that file is whatever upstream holds today, unreviewed here.
Transcription mode imports the register, because it was installed from a commit
this repository names in a line someone reviewed, the way all five desktop apps
read it. Until 8.12 transcription fetched the pin over HTTPS too, and a pin
GitHub stopped serving would have answered HTTP 404, exit 2, and the deploy
gate would have warned and deployed.

`pytest` makes the same transcription comparison (tests/test_brand_mirror.py),
offline and with no credential: every key and value exactly, and the
constants. This mode is kept for the required status check named "mirror
matches its pinned commit" and for running by hand. Until the 8.12 review it
compared values ignoring case and skipped the constants, so this check passed
mirrors the suite failed.
"""

from __future__ import annotations

import argparse
import ast
import sys

# Exit codes are part of this script's contract, because a caller has to be
# able to tell a DEFECT from an OUTAGE. Exit 1 means the comparison ran and
# the answer is bad. Exit 2 means the comparison could not be made at all --
# upstream unreachable, rate-limited, unparseable, or (transcription mode) the
# register not installed. An unreachable remote is not a defect of this
# repository, and a gate that cannot distinguish the two blocks good work
# during someone else's outage, which is the failure mode this project's
# principle 8 exists to prevent. Since 8.12 the gated callers run transcription
# mode only, after installing the register, so they fail on any non-zero exit:
# there a 2 means the install they just ran did not happen.
EXIT_OK = 0
EXIT_BAD = 1
EXIT_UNRESOLVED = 2
import urllib.error
import urllib.request

UPSTREAM_REPO = "RNVizion/rnv-brand"
UPSTREAM_FILE = "engine/brand.py"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
TIMEOUT = 30


def unresolved(msg: str) -> None:
    """Could not answer the question. Not an answer of "no"."""
    print(f"UNRESOLVED: {msg}")
    print("The comparison did not run, so this says nothing about the mirror.")
    raise SystemExit(EXIT_UNRESOLVED)


def fetch(ref: str) -> str:
    url = RAW.format(repo=UPSTREAM_REPO, ref=ref, path=UPSTREAM_FILE)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        unresolved(f"upstream fetch failed, HTTP {e.code} for {url}")
    except (urllib.error.URLError, TimeoutError) as e:
        unresolved(f"upstream unreachable ({e}) for {url}")


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
        unresolved(f"no RNV_BRAND dict found in {where}")

    out: dict[str, str] = {}
    for k, v in zip(target.keys, target.values):
        if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
            unresolved(f"non-literal key in RNV_BRAND ({where})")
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            out[k.value] = v.value
        elif isinstance(v, ast.Name) and v.id in literals:
            out[k.value] = literals[v.id]
        else:
            unresolved(f"cannot resolve value for {k.value!r} ({where})")
    return out


def local_mirror():
    # The repository root, from this file's place in it, so the server's own
    # engine package wins from any working directory. rnv-brand also installs
    # a top-level `engine` for its older consumers.
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from engine import brand_vocab as mirror  # noqa: E402

    import re

    found = re.findall(r"Mirrored from rnv-brand@([0-9a-f]{7,40})", mirror.__doc__ or "")
    if not found:
        unresolved("the mirror records no upstream SHA")
    return mirror, found[0]


def installed_register(pinned: str):
    """The register as pip installed it, and proof it is the pinned commit.

    PEP 610: pip writes direct_url.json into a distribution installed from a
    VCS URL, with the commit it resolved. That is the only record of which
    revision is installed; the package's version says which release.
    """
    import importlib.metadata
    import json

    import pathlib

    try:
        import rnv_brand.brand as register
    except ImportError as e:
        unresolved(f"rnv-brand is not installed as rnv_brand ({e}). "
                   f"Run: pip install -r tests/requirements-dev.txt")
    except Exception as e:  # the register's own import-time checks
        unresolved(f"rnv_brand.brand failed to import: "
                   f"{type(e).__name__}: {e}")
    try:
        dist = importlib.metadata.distribution("rnv-brand")
        raw = dist.read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        dist, raw = None, None
    # The commit below is pip's record of what it installed. It says nothing
    # about a module that came from somewhere else on sys.path, or a file
    # changed after the install, so the module that was imported must be one
    # of that installation's recorded files, with the hash pip recorded.
    import base64
    import hashlib

    loaded = pathlib.Path(register.__file__).resolve()
    record = None
    if dist is not None:
        record = next((f for f in (dist.files or [])
                       if pathlib.Path(dist.locate_file(f)).resolve() == loaded),
                      None)
    if record is None or record.hash is None:
        unresolved(f"rnv_brand.brand was imported from {loaded}, which no "
                   f"installed rnv-brand distribution records as its file. "
                   f"Run: pip install -r tests/requirements-dev.txt")
    digest = base64.urlsafe_b64encode(
        hashlib.new(record.hash.mode, loaded.read_bytes()).digest()
    ).rstrip(b"=").decode()
    if digest != record.hash.value:
        unresolved(f"{loaded} has changed since pip installed it. "
                   f"Run: pip install --force-reinstall -r tests/requirements-dev.txt")
    commit = ((json.loads(raw) if raw else {}).get("vcs_info") or {}).get(
        "commit_id")
    if not commit:
        unresolved("rnv-brand was not installed from a git commit, so nothing "
                   "records which revision is installed. "
                   "Run: pip install -r tests/requirements-dev.txt")
    if commit != pinned:
        print(f"FAIL: the installed register is rnv-brand@{commit[:12]}, and "
              f"the mirror says it carries {pinned[:12]}.")
        print("Either tests/requirements-dev.txt and the mirror's docstring "
              "name different commits, which is this repository being wrong, "
              "or this environment predates the pin: "
              "pip install -r tests/requirements-dev.txt")
        raise SystemExit(EXIT_BAD)
    return register


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

    mirror, pinned_sha = local_mirror()
    mine = dict(mirror.RNV_BRAND)
    constants: list[str] = []
    if args.mode == "transcription":
        ref = pinned_sha
        register = installed_register(pinned_sha)
        up = dict(register.RNV_BRAND)
        source = "installed rnv_brand.brand"
        # Every color constant the mirror defines, read from the module and
        # not from __all__, so dropping a name from __all__ hides nothing.
        names = sorted(n for n, v in vars(mirror).items()
                       if n.isupper() and isinstance(v, str) and v.startswith("#"))
        if not names:
            unresolved("the mirror defines no color constants")
        constants = [
            f"{n}: mirror {getattr(mirror, n)}, register {getattr(register, n, None)}"
            for n in names
            if getattr(mirror, n) != getattr(register, n, None)]
    else:
        ref = args.ref
        up = extract_rnv_brand(fetch(ref), f"{UPSTREAM_REPO}@{ref}:{UPSTREAM_FILE}")
        source = f"{UPSTREAM_REPO}@{ref} over HTTPS"

    missing = {k: up[k] for k in up if k not in mine}
    extra = {k: mine[k] for k in mine if k not in up}
    # Exact: the resolver returns these strings as they are, so a change of
    # case is a change.
    drift = [k for k in mine if k in up and mine[k] != up[k]]

    print(f"mode={args.mode}  upstream={UPSTREAM_REPO}@{ref}  read from {source}")
    print(f"upstream keys={len(up)}  mirror keys={len(mine)}  pinned={pinned_sha[:7]}"
          + (f"  constants compared={len(names)}" if args.mode == "transcription" else ""))

    if args.mode == "transcription":
        if not (missing or extra or drift or constants):
            print("\nPASS: the mirror carries exactly the commit it says it carries.")
            return EXIT_OK
        print("\nFAIL (defect): the mirror does not match its own pinned commit.")
        report(missing, extra, drift, up, mine)
        if constants:
            print(f"\n  constants that differ ({len(constants)}):")
            for line in constants:
                print(f"    {line}")
        print("\nThis repository is wrong. Either the mirror was edited without")
        print("re-pinning, or SYNCED_SHA was moved without syncing the values.")
        return EXIT_BAD

    if not (missing or extra or drift):
        print("\nPASS: the mirror is current with upstream.")
        return EXIT_OK
    print("\nBEHIND (queue): upstream has moved past the pinned mirror.")
    report(missing, extra, drift, up, mine)
    print("\nNothing in this repository is wrong and no publish is blocked.")
    print("The mirror is synced by a human, on purpose, in a deliberate commit:")
    print("  1. add the keys/values to engine/brand_vocab.py")
    print("  2. add the same keys to WIRE_KEYS in tests/test_brand_mirror.py")
    print("  3. re-pin SYNCED_SHA, the docstring SHA and the rnv-brand line in")
    print("     tests/requirements-dev.txt to the synced commit, and reinstall")
    print("\nUntil then the resolver refuses these names. If any of them is a")
    print("PERMANENT brand color, that is worth doing now rather than later.")
    return EXIT_BAD


if __name__ == "__main__":
    raise SystemExit(main())
