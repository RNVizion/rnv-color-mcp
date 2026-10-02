#!/usr/bin/env python3
"""Refuse a release whose tag and server.json disagree about the version.

`publish-mcp.yml` runs this before it publishes to the MCP registry. A release
is cut by pushing a tag `vX.Y.Z`; the version the registry receives is the one
in `server.json` at the tagged commit. This check holds the two equal, so the
tag can never publish a version it does not name.

Why it exists (2026-10-02). Until then the workflow stamped the tag's version
into `server.json`, published, and pushed the stamped file back to `main`.
`main` now takes only pull requests (a ruleset), so that push would be refused
after the publish had already succeeded: a release would go out and the run
would end red, with the repository left saying the old version. Nothing is
pushed any more. The version is set in the release's own pull request, and
this check refuses when the tag says something else.

It refuses, with what it found, when:
  - the ref is not a tag (a manual run from a branch);
  - the tag is not `vX.Y.Z`, three plain numbers;
  - `server.json` is missing, is not JSON, or has no version string;
  - `server.json`'s version is not `X.Y.Z`;
  - the two versions differ.

What it cannot see, and what does:
  - whether the tagged commit is on `main`: the workflow's next step;
  - whether the registry already holds this version: the registry refuses a
    re-published version itself, at the publish step;
  - whether the description fits the registry's schema:
    tests/test_public_surfaces.py, before any tag.

Exit codes: 0 the release may go; 1 refused. Stdlib only, no network.

    python3 scripts/check_release_version.py tag v1.3.1
    python3 scripts/check_release_version.py "$GITHUB_REF_TYPE" "$GITHUB_REF_NAME"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
HOW = ("Set the version in server.json in the release's pull request, merge it, "
       "and tag the merge commit.")


def check(ref_type: str, ref_name: str, path: Path) -> tuple[int, str]:
    """(exit code, message). Never raises on a bad input; a refusal says what
    was observed, not only what was expected."""
    if ref_type != "tag":
        return 1, (f"Refused: this run is on the {ref_type or 'unknown ref'} {ref_name!r}, "
                   f"not on a version tag. A release is published from a tag like v1.3.1.")
    if not ref_name.startswith("v") or not VERSION.fullmatch(ref_name[1:]):
        return 1, (f"Refused: the tag {ref_name!r} is not of the form vX.Y.Z "
                   f"(three plain numbers, such as v1.3.1).")
    tag_version = ref_name[1:]

    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 1, f"Refused: {path} does not exist at this commit."
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return 1, f"Refused: {path} could not be read as JSON ({exc})."
    file_version = meta.get("version") if isinstance(meta, dict) else None
    if not isinstance(file_version, str):
        return 1, f"Refused: {path} has no version string (found {file_version!r})."
    if not VERSION.fullmatch(file_version):
        return 1, (f"Refused: {path} says version {file_version!r}, "
                   f"which is not of the form X.Y.Z.")

    if file_version != tag_version:
        return 1, (f"Refused: the tag {ref_name} says {tag_version}; {path} says "
                   f"{file_version}. Nothing was published. {HOW}")
    return 0, f"Release {tag_version}: the tag {ref_name} and {path} agree."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("ref_type", help="GITHUB_REF_TYPE: 'tag' or 'branch'")
    parser.add_argument("ref_name", help="GITHUB_REF_NAME: e.g. v1.3.1")
    parser.add_argument("--file", default="server.json", type=Path)
    args = parser.parse_args(argv)
    code, message = check(args.ref_type, args.ref_name, args.file)
    print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
