"""FLUX via fal.ai (`fal-ai/flux-2-pro/edit`, multi-reference).

Privacy: references are sent inline as data URIs and results requested with `sync_mode`,
so no child photo or page is ever stored on fal's public CDN.
"""

import base64

import fal_client

from qamra_ai.cost import CostEntry, fal_cost
from qamra_ai.errors import ContentBlocked, ProviderConfigError, ProviderError
from qamra_ai.image.base import GeneratedImage, ImageRequest, aspect_px


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _decode_data_uri(uri: str) -> tuple[bytes, str]:
    header, _, payload = uri.partition(",")
    mime = header.removeprefix("data:").split(";")[0] or "image/png"
    return base64.b64decode(payload), mime


class FluxImageProvider:
    name = "flux"

    def __init__(self, api_key: str | None, model: str, long_side: int) -> None:
        if not api_key:
            raise ProviderConfigError("FAL_KEY is not set")
        self._client = fal_client.AsyncClient(key=api_key, default_timeout=300)
        self.model = model
        self._long_side = long_side

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        if not req.refs:
            raise ProviderConfigError("flux edit endpoint needs ≥ 1 reference image")
        w, h = aspect_px(req.aspect, self._long_side)
        labels = "\n".join(f"Image {i + 1}: {r.label}" for i, r in enumerate(req.refs))
        args: dict[str, object] = {
            "prompt": f"{labels}\n\n{req.prompt}",
            "image_urls": [_data_uri(r.data, r.mime) for r in req.refs],
            "image_size": {"width": w, "height": h},
            "output_format": "png",
            "sync_mode": True,
            "enable_safety_checker": True,
            "safety_tolerance": "2",
        }
        if req.seed is not None:
            args["seed"] = req.seed
        try:
            result = await self._client.subscribe(self.model, arguments=args)
        except fal_client.FalClientHTTPError as e:
            if e.status_code in (429,) or e.status_code >= 500:
                raise ProviderError(f"fal error {e.status_code}: {e.message}") from e
            raise ProviderConfigError(f"fal rejected request {e.status_code}: {e.message}") from e
        except fal_client.FalClientTimeoutError as e:
            raise ProviderError("fal timeout") from e

        if not isinstance(result, dict):
            raise ProviderError("fal returned an unexpected payload")
        if any(result.get("has_nsfw_concepts") or []):
            raise ContentBlocked("fal safety checker flagged the output")
        images = result.get("images") or []
        if not images:
            raise ProviderError("fal returned no image")
        data, mime = _decode_data_uri(images[0]["url"])
        # 1 output + input references, all resized to ~1MP by the endpoint
        megapixels = (w * h) / 1e6 + len(req.refs) * 1.0
        cost = CostEntry(
            step=req.step,
            provider=self.name,
            model=self.model,
            units={"megapixels": round(megapixels, 2)},
            usd=fal_cost(self.model, megapixels),
            estimated=True,
        )
        return GeneratedImage(
            data=data,
            mime=mime,
            cost=cost,
            params={
                "provider": self.name,
                "model": self.model,
                "size": f"{w}x{h}",
                "seed": result.get("seed"),
            },
        )
