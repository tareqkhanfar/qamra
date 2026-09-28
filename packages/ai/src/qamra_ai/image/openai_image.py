"""OpenAI GPT Image adapter (`images.edit` with multiple reference images)."""

import base64
from typing import Literal

import openai

from qamra_ai.cost import CostEntry, openai_image_cost
from qamra_ai.errors import ContentBlocked, ProviderConfigError, ProviderError
from qamra_ai.image.base import TIER_PX, GeneratedImage, ImageRequest, aspect_px

_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
Quality = Literal["low", "medium", "high", "xhigh", "max", "auto"]


class OpenAIImageProvider:
    name = "openai"

    def __init__(self, api_key: str | None, model: str, quality: Quality) -> None:
        if not api_key:
            raise ProviderConfigError("OpenAI key is not set (admin → settings → AI keys)")
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self._quality = quality

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        if not req.refs:
            raise ProviderConfigError("openai adapter uses images.edit and needs ≥ 1 reference")
        w, h = aspect_px(req.aspect, max(1024, TIER_PX[req.resolution]))
        files = [(f"ref{i}.{_EXT.get(r.mime, 'png')}", r.data, r.mime) for i, r in enumerate(req.refs)]
        labels = "\n".join(f"Reference image {i + 1}: {r.label}" for i, r in enumerate(req.refs))
        try:
            resp = await self._client.images.edit(
                model=self.model,
                image=files,
                prompt=f"{labels}\n\n{req.prompt}",
                size=f"{w}x{h}",
                quality=self._quality,
                input_fidelity="high",
                output_format="png",
            )
        except openai.BadRequestError as e:
            if getattr(e, "code", None) == "moderation_blocked":
                raise ContentBlocked(f"openai moderation: {e.message}") from e
            raise ProviderConfigError(f"openai rejected request: {e.message}") from e
        except (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError) as e:
            raise ProviderError(f"openai error: {e}") from e

        if not resp.data or not resp.data[0].b64_json:
            raise ProviderError("openai returned no image")
        u = resp.usage
        text_in = image_in = out = 0
        if u is not None:
            out = u.output_tokens
            details = u.input_tokens_details
            text_in = getattr(details, "text_tokens", 0) or 0
            image_in = getattr(details, "image_tokens", 0) or 0
        cost = CostEntry(
            step=req.step,
            provider=self.name,
            model=self.model,
            units={
                "text_input_tokens": text_in,
                "image_input_tokens": image_in,
                "output_tokens": out,
            },
            usd=openai_image_cost(self.model, text_in, image_in, out),
        )
        return GeneratedImage(
            data=base64.b64decode(resp.data[0].b64_json),
            mime="image/png",
            cost=cost,
            params={
                "provider": self.name,
                "model": self.model,
                "size": f"{w}x{h}",
                "quality": self._quality,
            },
        )
