"""
The release check, and the release workflow's promise never to push.

A release is a tag `vX.Y.Z`. `publish-mcp.yml` runs
`scripts/check_release_version.py` before it publishes, and that script refuses
unless the tag and `server.json` name the same version. Since 2026-10-02 `main`
takes only pull requests, so the workflow can no longer push a stamped
`server.json` back; the version is set in the release's pull request and
checked here instead.

Two things are held:

  1. THE CHECK. It passes only for a tag `vX.Y.Z` over a `server.json` saying
     `X.Y.Z`, and every refusal says what it found. The repository's own
     `server.json` must already be in the form the check accepts, or no tag
     could ever match it.

  2. THE WORKFLOW'S SHAPE, read as text. It runs the check before it publishes,
     it never commits or pushes, and it asks for no write permission. A push
     added back would be refused by the ruleset AFTER the registry publish had
     succeeded, which is the failure this change removed.

What this file cannot see, and who can:
  - whether the ruleset on `main` is on: GitHub's settings; the public rules
    page shows it;
  - whether the tagged commit is on `main`: the workflow's own second step,
    which needs git history and runs only on GitHub;
  - whether the registry accepts the publish, or already holds the version:
    the publish step itself;
  - whether a tag matches `server.json` TODAY. No tag exists until a release
    is cut, and the suite stays offline. That comparison is the workflow's.

TestPositiveControl is the diagnostic: a matching pair passes and the script
is the file the workflow names. If it fails, the harness is wrong, not the
check.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_release_version.py"
WORKFLOW = ROOT / ".github" / "workflows" / "publish-mcp.yml"

_spec = importlib.util.spec_from_file_location("check_release_version", SCRIPT)
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)


def server_json(tmp_path: Path, version=...) -> Path:
    """A server.json holding `version`; with no version, the key is absent."""
    meta = {"name": "io.github.RNVizion/rnv-color-mcp"}
    if version is not ...:
        meta["version"] = version
    path = tmp_path / "server.json"
    path.write_text(json.dumps(meta), encoding="utf-8")
    return path


def workflow_steps() -> str:
    """The workflow with comment lines removed, so a word in the explanation
    of what it no longer does is not mistaken for the thing itself."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


class TestPositiveControl:
    """If this fails, the harness or a path is wrong, not the check."""

    def test_a_matching_tag_and_file_pass(self, tmp_path):
        code, message = release.check("tag", "v1.3.1", server_json(tmp_path, "1.3.1"))
        assert code == 0, message
        assert "1.3.1" in message

    def test_the_workflow_runs_this_script(self):
        # The reader strips comments; prove it still sees the steps, and that
        # the step it sees names the file under test.
        steps = workflow_steps()
        assert "mcp-publisher publish" in steps
        assert f"scripts/{SCRIPT.name}" in steps


class TestTheCheckRefuses:
    def test_a_mismatch_names_both_versions(self, tmp_path):
        path = server_json(tmp_path, "1.3.0")
        code, message = release.check("tag", "v1.3.1", path)
        assert code == 1
        assert "v1.3.1 says 1.3.1" in message
        assert f"{path} says 1.3.0" in message
        assert "Nothing was published" in message

    def test_a_branch_is_not_a_release(self, tmp_path):
        # A manual run started from main, not from a tag.
        code, message = release.check("branch", "main", server_json(tmp_path, "1.3.0"))
        assert code == 1
        assert "branch 'main'" in message

    @pytest.mark.parametrize("tag", [
        "1.3.1",          # no v
        "v1.3",           # two parts
        "v1.3.1-rc1",     # a pre-release suffix: not accepted until one is wanted
        "v01.3.1",        # a leading zero
    ])
    def test_a_tag_that_is_not_a_version_is_refused_by_name(self, tmp_path, tag):
        code, message = release.check("tag", tag, server_json(tmp_path, "1.3.1"))
        assert code == 1
        assert repr(tag) in message

    @pytest.mark.parametrize("version", [..., None, 130, "1.3", "v1.3.1"])
    def test_a_file_without_a_plain_version_is_refused(self, tmp_path, version):
        code, message = release.check("tag", "v1.3.1", server_json(tmp_path, version))
        assert code == 1
        assert "server.json" in message

    def test_a_missing_or_broken_file_is_refused_not_raised(self, tmp_path):
        path = tmp_path / "server.json"
        code, message = release.check("tag", "v1.3.1", path)
        assert code == 1 and "does not exist" in message
        path.write_text("{not json", encoding="utf-8")
        code, message = release.check("tag", "v1.3.1", path)
        assert code == 1 and "could not be read as JSON" in message


class TestThroughTheCommandLine:
    """The workflow runs the script as a command, so the exit code is the
    contract. Once through the real entry point, both ways."""

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              capture_output=True, text=True, cwd=ROOT)

    def test_exit_codes(self, tmp_path):
        path = server_json(tmp_path, "1.3.1")
        ok = self.run("tag", "v1.3.1", "--file", str(path))
        assert ok.returncode == 0 and "agree" in ok.stdout
        bad = self.run("tag", "v1.3.2", "--file", str(path))
        assert bad.returncode == 1 and "Refused" in bad.stderr


class TestTheRepositoryCanBeReleased:
    def test_server_json_holds_a_version_the_check_accepts(self):
        version = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))["version"]
        code, message = release.check("tag", f"v{version}", ROOT / "server.json")
        assert code == 0, message


class TestTheWorkflowNeverPushes:
    def test_the_check_comes_before_the_publish(self):
        steps = workflow_steps()
        assert steps.index(f"scripts/{SCRIPT.name}") < steps.index("mcp-publisher publish")

    def test_it_neither_commits_nor_pushes(self):
        found = re.findall(r"git\s+(?:push|commit|add)\b", workflow_steps())
        assert not found, found

    def test_it_asks_for_no_write_access_to_the_repository(self):
        permissions = re.findall(r"^\s*contents:\s*(\w+)", workflow_steps(), flags=re.M)
        assert permissions == ["read"], permissions
