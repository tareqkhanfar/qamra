"""Google Gemini image adapter (google-genai SDK, `generate_content` with IMAGE modality)."""

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from qamra_ai.cost import CostEntry, gemini_cost
from qamra_ai.errors import ContentBlocked, ProviderConfigError, ProviderError
from qamra_ai.image.base import GeneratedImage, ImageRequest, Resolution

# The direct Gemini API offers 1K/2K/4K; the 0.5K preview tier maps to 1K here.
_SIZE: dict[Resolution, str] = {"0.5K": "1K", "1K": "1K", "2K": "2K", "4K": "4K"}


class GeminiImageProvider:
    name = "gemini"

    def __init__(self, api_key: str | None, model: str, max_size: str = "4K") -> None:
        if not api_key:
            raise ProviderConfigError("Gemini key is not set (admin → settings → AI keys)")
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self._max = max_size

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        size = min(_SIZE[req.resolution], self._max, key=lambda v: int(v[0]))
        contents: list[types.PartUnion] = []
        for i, ref in enumerate(req.refs, start=1):
            contents.append(f"Reference image {i}: {ref.label}")
            contents.append(types.Part.from_bytes(data=ref.data, mime_type=ref.mime))
        contents.append(req.prompt)
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=req.aspect, image_size=size),
            seed=req.seed,
        )
        try:
            resp = await self._client.aio.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except genai_errors.ClientError as e:  # 4xx
            if e.code == 429:
                raise ProviderError(f"gemini rate limited: {e.message}") from e
            raise ProviderConfigError(f"gemini rejected request: {e.code} {e.message}") from e
        except (genai_errors.ServerError, genai_errors.APIError) as e:
            raise ProviderError(f"gemini error: {e}") from e

        if resp.prompt_feedback and resp.prompt_feedback.block_reason:
            raise ContentBlocked(f"gemini blocked prompt: {resp.prompt_feedback.block_reason}")
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else None) or []:
                if part.inline_data and part.inline_data.data:
                    cost = CostEntry(
                        step=req.step,
                        provider=self.name,
                        model=self.model,
                        units={"images": 1, "input_images": len(req.refs)},
                        usd=gemini_cost(self.model, size, 1, len(req.refs)),
                    )
                    return GeneratedImage(
                        data=part.inline_data.data,
                        mime=part.inline_data.mime_type or "image/png",
                        cost=cost,
                        params={
                            "provider": self.name,
                            "model": self.model,
                            "size": size,
                            "seed": req.seed,
                        },
                    )
        reason = resp.candidates[0].finish_reason if resp.candidates else "no candidates"
        if str(reason).upper().endswith(("SAFETY", "PROHIBITED_CONTENT", "IMAGE_SAFETY")):
            raise ContentBlocked(f"gemini returned no image: {reason}")
        raise ProviderError(f"gemini returned no image: {reason}")
