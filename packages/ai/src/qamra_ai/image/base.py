"""Image provider interface. Every model sits behind `ImageProvider`; switch via admin settings."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from qamra_ai.cost import CostEntry

Aspect = Literal["1:1", "3:2", "16:9"]
Resolution = Literal["0.5K", "1K", "2K", "4K"]

# Long side in px per resolution tier (fal Nano Banana 2 tiers; used by providers that take pixels).
TIER_PX: dict[Resolution, int] = {"0.5K": 512, "1K": 1024, "2K": 2048, "4K": 4096}


@dataclass(frozen=True)
class RefImage:
    data: bytes
    mime: str
    label: str  # what the model should treat it as, e.g. "THE HERO — character reference sheet"


@dataclass(frozen=True)
class ImageRequest:
    step: str
    prompt: str
    refs: list[RefImage] = field(default_factory=list)
    aspect: Aspect = "1:1"
    resolution: Resolution = "1K"
    seed: int | None = None
    # Exact output (width, height) for models that take pixels (FLUX.2, self-hosted); overrides aspect and
    # resolution there. The Classic hero edit uses it: a crop keeps its own shape, often portrait.
    size: tuple[int, int] | None = None


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
    """(width, height), both multiples of 16. Landscape for 3:2 and 16:9."""
    if aspect == "1:1":
        return long_side, long_side
    ratio = 2 / 3 if aspect == "3:2" else 9 / 16
    return long_side, round(long_side * ratio / 16) * 16
