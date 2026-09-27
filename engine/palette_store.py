"""
RNV Color MCP - Palette Store

Server-side persistence for named palettes. Single JSON file, keyed by palette name.

Durability modes:
  - Local only (default): writes to a local JSON file. On an ephemeral host this resets
    on rebuild. Always-on working copy; used for dev and tests.
  - HF Dataset write-through (set HF_TOKEN; optionally RNV_PALETTE_DATASET): the local file
    is the fast working copy, and every save is also pushed to a PRIVATE Hugging Face Dataset
    repo. The store hydrates from that repo on startup, so palettes survive rebuilds. Free
    durable storage. If RNV_PALETTE_DATASET is unset, the repo id is derived from the token's
    account as "<username>/rnv-color-palettes".

Adopts the desktop app's PaletteMetadata schema so palettes stay portable.
Atomic local writes; HF push is best-effort (a failed sync never loses the local save).

The one thing a best-effort push must never do is overwrite the Dataset with less
than it holds. Hydration at startup is what makes a push safe: the local file is a
superset of the Dataset only if the Dataset was read first. So a startup that could
NOT read the Dataset -- network down, rate-limited, a copy that failed -- leaves the
store local-only for the life of the process, and every save reports `durable: False`
with the reason. Only a confirmed "no palettes.json in the Dataset yet" starts empty
and ready. Before 2026-09-27 both cases were one bare `except: pass`, and a transient
outage at boot followed by a single save would have pushed a one-palette file over
every palette the Dataset held.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from engine.palette_metadata import PaletteMetadata

DEFAULT_AUTHOR = "RNVizion"
HF_FILENAME = "palettes.json"


class PaletteStore:
    def __init__(
        self,
        path: str | os.PathLike[str] = "palettes.json",
        hf_repo: str | None = None,
        hf_token: str | None = None,
    ) -> None:
        self.path = Path(path)
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        self.hf_repo = hf_repo or os.environ.get("RNV_PALETTE_DATASET")
        self._hf_ready = False
        # Why the store is not durable, in the words a caller can act on. Set at
        # startup and overwritten by a failed push; empty means the last save
        # reached the Dataset.
        self.durable_reason = "no HF_TOKEN: local working copy only"
        self._data: dict[str, dict[str, Any]] = {}
        if self.hf_token:
            self._init_hf()
        self._load()

    # ---- HF dataset backend (best-effort) ------------------------------
    def _init_hf(self) -> None:
        """Resolve/create the dataset repo and hydrate the local file from it.

        Three outcomes, and the middle one is the whole point:

        - hydrated: the Dataset's palettes.json is now the local file. Ready.
        - not found: the Dataset has no palettes.json yet. Start empty. Ready.
        - could not look: anything else -- unreachable, rate-limited, a copy
          that failed. NOT ready: a push from here would overwrite the Dataset
          with a file that never contained what the Dataset holds.

        `LocalEntryNotFoundError` is checked BEFORE `EntryNotFoundError`
        because it subclasses it: the hub raises the Local variant for "the
        entry may exist on the Hub, the network did not answer" -- an outage
        wearing the not-found class. Catching the parent first would file an
        outage as an empty Dataset, which is exactly the clobber this guards.
        """
        try:
            from huggingface_hub import HfApi, hf_hub_download
            from huggingface_hub.errors import EntryNotFoundError, LocalEntryNotFoundError

            api = HfApi(token=self.hf_token)
            if not self.hf_repo:
                self.hf_repo = f"{api.whoami()['name']}/rnv-color-palettes"
            api.create_repo(
                self.hf_repo, repo_type="dataset", private=True, exist_ok=True
            )
        except Exception as exc:  # could not even reach or resolve the Dataset
            self._hf_ready = False
            self.durable_reason = f"Dataset unreachable at startup ({type(exc).__name__}): local working copy only"
            return

        try:
            local = hf_hub_download(
                self.hf_repo, HF_FILENAME, repo_type="dataset", token=self.hf_token
            )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local, self.path)
        except LocalEntryNotFoundError as exc:
            # "may exist on the Hub" -- the network did not answer. Not a
            # not-found; a could-not-look. Refuse to be a durable writer.
            self._hf_ready = False
            self.durable_reason = f"Dataset could not be hydrated at startup ({type(exc).__name__}): local working copy only"
            return
        except EntryNotFoundError:
            pass  # confirmed: no palettes.json in the Dataset yet; start empty
        except Exception as exc:
            self._hf_ready = False
            self.durable_reason = f"Dataset could not be hydrated at startup ({type(exc).__name__}): local working copy only"
            return

        self._hf_ready = True
        self.durable_reason = ""

    def _push_hf(self) -> bool:
        if not self._hf_ready:
            return False  # durable_reason already says why, since startup
        try:
            from huggingface_hub import HfApi

            HfApi(token=self.hf_token).upload_file(
                path_or_fileobj=str(self.path),
                path_in_repo=HF_FILENAME,
                repo_id=self.hf_repo,
                repo_type="dataset",
                commit_message="Update palettes",
            )
            self.durable_reason = ""
            return True
        except Exception as exc:
            # local save already succeeded; durability sync failed
            self.durable_reason = f"push to the Dataset failed ({type(exc).__name__}): saved to the local working copy only"
            return False

    # ---- persistence ----------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> bool:
        """Atomic local write, then best-effort HF push. Returns True if durably synced."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return self._push_hf()

    # ---- tool-facing operations ----------------------------------------
    def save_palette(
        self,
        name: str,
        colors: list[str],
        notes: str = "",
        author: str = DEFAULT_AUTHOR,
    ) -> dict[str, Any]:
        """Create or update a named palette. `notes` maps to metadata.description."""
        if not name or not name.strip():
            raise ValueError("Palette name is required.")
        if not colors:
            raise ValueError("A palette needs at least one color.")

        existing = self._data.get(name)
        if existing:
            meta = PaletteMetadata.from_dict(existing.get("metadata", {}))
            meta.description = notes
            meta.author = author or meta.author or DEFAULT_AUTHOR
            meta.touch()
        else:
            meta = PaletteMetadata(name=name, description=notes, author=author)

        self._data[name] = {"colors": colors, "metadata": meta.to_dict()}
        durable = self._save()
        return {
            "name": name,
            "colors": colors,
            "saved": True,
            "durable": durable,
            "durable_reason": "" if durable else self.durable_reason,
        }

    def list_palettes(self) -> list[dict[str, Any]]:
        """Return every saved palette as {name, colors}."""
        return [
            {"name": name, "colors": entry.get("colors", [])}
            for name, entry in self._data.items()
        ]

    def get_palette(self, name: str) -> dict[str, Any] | None:
        """Return one full palette {name, colors, metadata}, or None if missing."""
        entry = self._data.get(name)
        if entry is None:
            return None
        return {
            "name": name,
            "colors": entry.get("colors", []),
            "metadata": entry.get("metadata", {}),
        }


__all__ = ["PaletteStore", "DEFAULT_AUTHOR"]
