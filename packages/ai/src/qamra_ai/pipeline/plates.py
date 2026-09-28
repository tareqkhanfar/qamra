"""Background-plate cache (Addendum 3 §2.2): child-free scenes are drawn once per theme and reused.

The key covers everything that changes the picture: image model, theme + version, page, art style,
house-style version, resolution tier and book language (the text area's side depends on the binding). The
model is part of it so placeholder art from offline runs can never end up in a real book.
"""

import re
from pathlib import Path
from typing import Protocol


class PlateStore(Protocol):
    def get(self, key: str) -> bytes | None: ...

    def put(self, key: str, data: bytes) -> None: ...


def plate_key(
    *,
    model: str,
    theme: str,
    theme_version: int,
    beat: int,
    style: str,
    house_version: str,
    resolution: str,
    lang: str,
) -> str:
    slug = re.sub(r"[^a-z0-9.-]+", "-", model.lower()).strip("-")
    return (
        f"plates/{slug}/{theme}/v{theme_version}/{style}/h{house_version}/{lang}-{resolution}/p{beat:02d}.png"
    )


class DirPlateStore:
    """Local directory store (scripts, sample books)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, key: str) -> bytes | None:
        path = self.root / key
        return path.read_bytes() if path.is_file() else None

    def put(self, key: str, data: bytes) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
