"""
RNV Color MCP - Palette Store

Server-side persistence for named palettes. Single JSON file, keyed by palette name.
Adopts the desktop app's PaletteMetadata schema so palettes stay portable (interop by
format, not by shared database). Single-user to start; multi-user scoping is deferred.

Atomic writes (temp file + replace) so a crash mid-write can't corrupt the store.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from engine.palette_metadata import PaletteMetadata

DEFAULT_AUTHOR = "RNVizion"


class PaletteStore:
    """A tiny name-keyed palette store backed by a single JSON file.

    On-disk shape:
        {
          "<name>": {
            "colors": ["#0a0a0f", "#d2bc93", ...],
            "metadata": { name, description, author, created_at, modified_at }
          },
          ...
        }
    """

    def __init__(self, path: str | os.PathLike[str] = "palettes.json") -> None:
        self.path = Path(path)
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    # ---- persistence ----------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: dump to a temp file in the same dir, then replace.
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

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
        self._save()
        return {"name": name, "colors": colors, "saved": True}

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
