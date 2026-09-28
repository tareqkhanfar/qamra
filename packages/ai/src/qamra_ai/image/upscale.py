"""Upscalers: generated art (~1K) → print size (Addendum 3 §2.1).

Default: fal SeedVR2 (`fal-ai/seedvr/upscale/image`, $0.001 per output megapixel, factor 1–10).
Also supported: `fal-ai/recraft/upscale/crisp` ($0.004 per image, PNG input) and any fal endpoint that takes
`image_url`. The exact print size is reached afterwards with a local crop + Lanczos fit (see
`pipeline.printimg`), so the upscaler only needs to get at or above it.
"""

import io
import math
from dataclasses import dataclass
from typing import Any, Protocol

import fal_client
import httpx
from PIL import Image

from qamra_ai.cost import FAL_MEGAPIXEL, CostEntry, fal_cost, fal_unknown_price
from qamra_ai.errors import ProviderConfigError, ProviderError
from qamra_ai.image.fal import (
    PRIVACY_HEADERS,
    FalClient,
    data_uri,
    fetch_output,
    image_size,
    raise_for_fal,
)


@dataclass(frozen=True)
class Upscaled:
    data: bytes
    mime: str
    cost: CostEntry


class Upscaler(Protocol):
    name: str
    model: str

    async def upscale(self, data: bytes, *, step: str, target: tuple[int, int]) -> Upscaled: ...


def needed_factor(src: tuple[int, int], target: tuple[int, int], step: float = 0.1) -> float:
    """Smallest factor (rounded up to `step`) so that the source covers the target in both axes."""
    raw = max(target[0] / src[0], target[1] / src[1], 1.0)
    return math.ceil(raw / step - 1e-9) * step


def _png(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()


def _jpeg(data: bytes, quality: int = 95) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return buf.getvalue()


class FalUpscaler:
    name = "fal"

    def __init__(self, api_key: str | None, model: str, *, client: FalClient | None = None) -> None:
        if client is None:
            if not api_key:
                raise ProviderConfigError("fal key is not set (admin → settings → AI keys)")
            client = fal_client.AsyncClient(key=api_key, default_timeout=300)
        self._client = client
        self.model = model

    def build(self, data: bytes, target: tuple[int, int]) -> dict[str, Any]:
        src = image_size(data)
        if "seedvr" in self.model:
            return {
                "image_url": data_uri(_jpeg(data), "image/jpeg"),
                "upscale_mode": "factor",
                "upscale_factor": round(needed_factor(src, target), 2),
                "output_format": "png",
                "sync_mode": True,
            }
        if "recraft" in self.model:  # needs PNG input
            return {"image_url": data_uri(_png(data), "image/png"), "sync_mode": True}
        return {"image_url": data_uri(_jpeg(data), "image/jpeg"), "sync_mode": True}

    async def upscale(self, data: bytes, *, step: str, target: tuple[int, int]) -> Upscaled:
        args = self.build(data, target)
        try:
            result = await self._client.subscribe(self.model, arguments=args, headers=PRIVACY_HEADERS)
        except (fal_client.FalClientError, httpx.HTTPError) as e:
            raise_for_fal(e, self.model)
            raise
        image = result.get("image") if isinstance(result, dict) else None
        if not image and isinstance(result, dict) and result.get("images"):
            image = result["images"][0]
        if not image or not image.get("url"):
            raise ProviderError(f"fal upscaler returned no image ({self.model})")
        out, mime = await fetch_output(image["url"])
        w, h = image_size(out)
        usd = fal_cost(self.model, out_px=(w, h))
        cost = CostEntry(
            step=step,
            provider=self.name,
            model=self.model,
            units={
                "output_megapixels": round(w * h / FAL_MEGAPIXEL, 2),
                "factor": float(args.get("upscale_factor", 0)),
            },
            usd=usd if usd is not None else fal_unknown_price("upscale"),
            estimated=True,
        )
        return Upscaled(out, mime, cost)


class LocalUpscaler:
    """Lanczos only, $0. Used offline (tests, sketch samples) and as the `2k` A/B arm's final fit."""

    name = "local"
    model = "lanczos"

    async def upscale(self, data: bytes, *, step: str, target: tuple[int, int]) -> Upscaled:
        with Image.open(io.BytesIO(data)) as img:
            factor = needed_factor(img.size, target)
            size = (math.ceil(img.size[0] * factor), math.ceil(img.size[1] * factor))
            out = img.convert("RGB").resize(size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        units = {"out_px": float(size[0]), "out_py": float(size[1])}  # for cost projections
        return Upscaled(buf.getvalue(), "image/png", CostEntry(step, self.name, self.model, units, 0.0))
