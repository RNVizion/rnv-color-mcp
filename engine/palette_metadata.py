"""
RNV Color Palette Manager - Palette Metadata Module
Stores palette name, description, author, and timestamps.

Carried through session save/restore and embedded in export formats
that support metadata (JSON, XML, GPL, ASE, Affinity, CSS, TXT, etc.).

Optimized for Python 3.13.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class PaletteMetadata:
    """
    Metadata attached to a color palette.

    Attributes:
        name: Display name of the palette (shown in UI and exports).
        description: Free-form notes / description.
        author: Creator name (defaults to empty).
        created_at: ISO timestamp of when the palette was first created.
        modified_at: ISO timestamp of last modification.
    """

    name: str = "Untitled Palette"
    description: str = ""
    author: str = ""
    created_at: str = ""
    modified_at: str = ""

    def __post_init__(self) -> None:
        """Set timestamps if not already provided."""
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.modified_at:
            self.modified_at = now

    def touch(self) -> None:
        """Update the modified_at timestamp to now."""
        self.modified_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaletteMetadata:
        """Create from a loaded dictionary (session or import)."""
        return cls(
            name=data.get("name", "Untitled Palette"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            created_at=data.get("created_at", ""),
            modified_at=data.get("modified_at", ""),
        )

    @property
    def display_name(self) -> str:
        """Name suitable for window titles and export filenames."""
        return self.name if self.name else "Untitled Palette"

    @property
    def has_notes(self) -> bool:
        """True if the palette has a description."""
        return bool(self.description.strip())

    @property
    def is_named(self) -> bool:
        """True if the user has given this palette a custom name."""
        return self.name != "Untitled Palette" and bool(self.name.strip())


# ==================== Module Exports ====================

__all__: list[str] = [
    "PaletteMetadata",
]
