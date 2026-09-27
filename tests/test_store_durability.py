"""
Store durability: a push never overwrites the Dataset with less than it holds.

Hydration at startup is what makes a best-effort push safe -- the local file is
a superset of the Dataset only if the Dataset was read first. Before 2026-09-27
the hydrate step was one bare `except: pass`, so a transient failure at boot
(network, rate limit, a failed copy) started the store empty AND ready, and the
next save pushed a one-palette file over every palette the Dataset held.

Now there are three startup outcomes, and only two of them make a durable
writer: hydrated, or a CONFIRMED "no palettes.json yet". Anything else is
"could not look", the store stays local-only for the life of the process, and
every save says so in `durable_reason`.

The hub's own exception hierarchy carries the trap: LocalEntryNotFoundError --
"the network did not answer; the entry may exist on the Hub" -- SUBCLASSES
EntryNotFoundError. Catch the parent first and an outage files as an empty
Dataset. The store checks the subclass first; TestOutageShapedNotFound pins
that order.

No network and no credential: huggingface_hub is faked at the two attributes
the store imports, and the token is a literal. TestPositiveControl proves the
fakes are the thing under test -- if it fails, every green below is a picture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import huggingface_hub
from huggingface_hub.errors import EntryNotFoundError, LocalEntryNotFoundError

from engine.palette_store import HF_FILENAME, PaletteStore

TOKEN = "hf_fake_token_never_used"
REPO = "RNVizion/rnv-color-palettes"


class FakeHub:
    """Records every call the store makes; scripted to hydrate, not-find, or fail."""

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.calls: list[tuple] = []
        self.dataset: dict | None = None          # None = no palettes.json in the Dataset
        self.download_raises: Exception | None = None
        self.create_repo_raises: Exception | None = None
        self.upload_raises: Exception | None = None
        self.pushed: list[dict] = []              # every file content that reached upload_file

    # -- the two attributes the store imports from huggingface_hub ----------
    def HfApi(self, token=None):
        assert token == TOKEN
        hub = self

        class _Api:
            def whoami(self_inner):
                hub.calls.append(("whoami",))
                return {"name": "RNVizion"}

            def create_repo(self_inner, repo_id, repo_type, private, exist_ok):
                hub.calls.append(("create_repo", repo_id, repo_type))
                if hub.create_repo_raises:
                    raise hub.create_repo_raises

            def upload_file(self_inner, path_or_fileobj, path_in_repo, repo_id, repo_type, commit_message):
                hub.calls.append(("upload_file", repo_id, path_in_repo))
                if hub.upload_raises:
                    raise hub.upload_raises
                hub.pushed.append(json.loads(Path(path_or_fileobj).read_text(encoding="utf-8")))

        return _Api()

    def hf_hub_download(self, repo_id, filename, repo_type, token):
        self.calls.append(("hf_hub_download", repo_id, filename, repo_type))
        if self.download_raises:
            raise self.download_raises
        if self.dataset is None:
            raise EntryNotFoundError("404: no palettes.json in the Dataset")
        p = self.tmp_path / "downloaded.json"
        p.write_text(json.dumps(self.dataset), encoding="utf-8")
        return str(p)


@pytest.fixture
def hub(tmp_path, monkeypatch):
    fake = FakeHub(tmp_path)
    monkeypatch.setattr(huggingface_hub, "HfApi", fake.HfApi)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake.hf_hub_download)
    return fake


def make_store(tmp_path) -> PaletteStore:
    return PaletteStore(tmp_path / "data" / "palettes.json", hf_repo=REPO, hf_token=TOKEN)


EXISTING = {"Spring line": {"colors": ["#0a0a0f", "#d2bc93"], "metadata": {"author": "RNVizion"}}}


class TestPositiveControl:
    """The fakes are reached, and a normal boot hydrates and pushes a superset."""

    def test_hydrate_then_save_pushes_old_and_new(self, hub, tmp_path):
        hub.dataset = EXISTING
        store = make_store(tmp_path)
        assert ("hf_hub_download", REPO, HF_FILENAME, "dataset") in hub.calls
        assert store.get_palette("Spring line") is not None, "hydration did not load the Dataset"
        r = store.save_palette("Check", ["#d2bc93"])
        assert r["durable"] is True and r["durable_reason"] == ""
        assert [c for c in hub.calls if c[0] == "upload_file"] == [("upload_file", REPO, HF_FILENAME)]
        assert set(hub.pushed[-1]) == {"Spring line", "Check"}, "the push must carry what the Dataset held"

    def test_no_token_never_touches_the_hub(self, hub, tmp_path, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        store = PaletteStore(tmp_path / "local.json")
        r = store.save_palette("Check", ["#d2bc93"])
        assert hub.calls == []
        assert r["durable"] is False and "no HF_TOKEN" in r["durable_reason"]

    def test_the_reason_reaches_the_tool_result(self, hub, tmp_path, monkeypatch):
        """The api surface carries it too: a false `durable` with no reason
        is the shrug the second gate forbids."""
        import api
        monkeypatch.setattr(api, "_store", PaletteStore(tmp_path / "local.json"))
        r = api.save_palette("Check", ["#0a0a0f"])
        assert r.durable is False
        assert "no HF_TOKEN" in r.durable_reason


class TestConfirmedEmptyDataset:
    def test_not_found_starts_empty_and_ready(self, hub, tmp_path):
        hub.dataset = None  # EntryNotFoundError, the real not-found
        store = make_store(tmp_path)
        assert store.list_palettes() == []
        r = store.save_palette("Check", ["#d2bc93"])
        assert r["durable"] is True
        assert hub.pushed[-1] == {"Check": hub.pushed[-1]["Check"]}


class TestOutageShapedNotFound:
    """LocalEntryNotFoundError subclasses EntryNotFoundError. It must NOT be
    read as an empty Dataset."""

    def test_local_entry_not_found_is_could_not_look(self, hub, tmp_path):
        hub.download_raises = LocalEntryNotFoundError("outgoing traffic disabled; the entry may exist on the Hub")
        store = make_store(tmp_path)
        r = store.save_palette("Check", ["#d2bc93"])
        assert r["durable"] is False
        assert "could not be hydrated" in r["durable_reason"]
        assert "LocalEntryNotFoundError" in r["durable_reason"]
        assert not [c for c in hub.calls if c[0] == "upload_file"], "a push after a failed hydrate is the clobber"

    def test_the_subclass_relationship_this_test_exists_for_still_holds(self):
        """If the hub ever un-nests these classes, the ordering in the store
        becomes unnecessary rather than wrong -- but the reason recorded there
        would be stale, and this names it."""
        assert issubclass(LocalEntryNotFoundError, EntryNotFoundError)


class TestAnyOtherHydrateFailure:
    @pytest.mark.parametrize("exc", [ConnectionError("reset"), OSError("disk"), RuntimeError("rate limited")])
    def test_stays_local_only_and_says_why(self, hub, tmp_path, exc):
        hub.download_raises = exc
        store = make_store(tmp_path)
        r = store.save_palette("Check", ["#d2bc93"])
        assert r["durable"] is False
        assert type(exc).__name__ in r["durable_reason"]
        assert not [c for c in hub.calls if c[0] == "upload_file"]

    def test_dataset_unreachable_at_startup(self, hub, tmp_path):
        hub.create_repo_raises = ConnectionError("no route to hub")
        store = make_store(tmp_path)
        r = store.save_palette("Check", ["#d2bc93"])
        assert r["durable"] is False
        assert "unreachable at startup" in r["durable_reason"]
        assert not [c for c in hub.calls if c[0] in ("hf_hub_download", "upload_file")]


class TestFailedPush:
    def test_a_failed_sync_never_loses_the_local_save(self, hub, tmp_path):
        hub.dataset = EXISTING
        store = make_store(tmp_path)
        hub.upload_raises = ConnectionError("reset during upload")
        r = store.save_palette("Check", ["#d2bc93"])
        assert r["durable"] is False and "push to the Dataset failed" in r["durable_reason"]
        assert store.get_palette("Check") is not None
        on_disk = json.loads(store.path.read_text(encoding="utf-8"))
        assert set(on_disk) == {"Spring line", "Check"}

    def test_the_next_successful_push_clears_the_reason(self, hub, tmp_path):
        hub.dataset = EXISTING
        store = make_store(tmp_path)
        hub.upload_raises = ConnectionError("reset during upload")
        assert store.save_palette("Check", ["#d2bc93"])["durable"] is False
        hub.upload_raises = None
        r = store.save_palette("Check", ["#d2bc93", "#0a0a0f"])
        assert r["durable"] is True and r["durable_reason"] == ""
        assert set(hub.pushed[-1]) == {"Spring line", "Check"}
