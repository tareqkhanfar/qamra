"""Image provider interface. Every model sits behind `ImageProvider`; switch via `IMAGE_PROVIDER`."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from qamra_ai.cost import CostEntry

Aspect = Literal["1:1", "3:2"]


@dataclass(frozen=True)
class RefImage:
    data: bytes
    mime: str
    label: str  # what the model should treat it as, e.g. "hero character sheet"


@dataclass(frozen=True)
class ImageRequest:
    step: str
    prompt: str
    refs: list[RefImage] = field(default_factory=list)
    aspect: Aspect = "1:1"
    seed: int | None = None


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime: str
    cost: CostEntry
    params: dict[str, object] = field(default_factory=dict)  # provider/model/seed for reproducibility


class ImageProvider(Protocol):
    name: str
    model: str

    async def generate(self, req: ImageRequest) -> GeneratedImage: ...


def sniff_mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def aspect_px(aspect: Aspect, long_side: int) -> tuple[int, int]:
    """(width, height), both multiples of 16."""
    if aspect == "1:1":
        return long_side, long_side
    short = round(long_side * 2 / 3 / 16) * 16
    return long_side, short
