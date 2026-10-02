"""Generic fal.ai image provider: works with any fal endpoint (Addendum 3 §1).

Argument shapes verified against fal's OpenAPI schemas (2026-09-28):
- Nano Banana 2: `fal-ai/nano-banana-2` (text-to-image) and `fal-ai/nano-banana-2/edit` (up to 14
  reference images). Takes `resolution` (0.5K/1K/2K/4K) and `aspect_ratio`. The admin sets the base
  endpoint; `/edit` is used automatically whenever references are passed.
- FLUX.2 (`fal-ai/flux-2-pro/edit`, up to 9 references / 9 MP): `image_size` {width, height}.
- FLUX.2 [klein] (`fal-ai/flux-2/klein/4b/edit`, the Classic hero edit): up to 4 references, `image_size`
  {width, height}, `enable_safety_checker`, `output_format`, `num_images`; no `safety_tolerance`. Billed per
  megapixel of input and output, so references are sent at most 1 MP each (fal resizes them to 1 MP anyway).
- Any other endpoint: prompt + image_urls + seed + sync_mode. The admin chose it, the budget guard prices
  it conservatively (pricing.yaml `fal_unknown_image_usd`).

Privacy (child photos, drawings, pages):
- references go inline as data URIs, never uploaded to fal's CDN;
- `X-Fal-Store-IO: 0` stops fal keeping request/response payloads (30 days by default);
- results come back inline (`sync_mode`); any file fal still writes expires after 15 minutes.
Error payloads from fal echo our input, so only the error `type`/`msg` are ever logged or raised.
"""

import base64
import io
import json
from typing import Any, Literal, Protocol, cast

import fal_client
import httpx
from PIL import Image

from qamra_ai.cost import FAL_MEGAPIXEL, CostEntry, fal_cost, fal_unknown_price
from qamra_ai.errors import ContentBlocked, ProviderConfigError, ProviderError
from qamra_ai.image.base import TIER_PX, GeneratedImage, ImageRequest, RefImage, aspect_px

PRIVACY_HEADERS: dict[str, str] = {
    "X-Fal-Store-IO": "0",
    "X-Fal-Object-Lifecycle-Preference": json.dumps({"expiration_duration_seconds": 900}),
}
Family = Literal["nano-banana", "flux-2", "flux-2-klein", "generic"]
MAX_REFS: dict[Family, int] = {"nano-banana": 14, "flux-2": 9, "flux-2-klein": 4, "generic": 8}
REF_MAX_SIDE = 1536  # references are downscaled before sending: faster, cheaper, same guidance
KLEIN_REF_MAX_SIDE = 1024  # klein bills input megapixels: never send more than 1 MP per reference
_MAX_DOWNLOAD = 60 * 1024 * 1024
_ALLOWED_HOSTS = (".fal.media", ".fal.run", ".fal.ai")


class FalClient(Protocol):
    async def subscribe(
        self, application: str, arguments: dict[str, Any], *, headers: dict[str, str] = ...
    ) -> Any: ...


def family_of(endpoint: str) -> Family:
    if "nano-banana" in endpoint:
        return "nano-banana"
    if "flux-2" in endpoint and "klein" in endpoint:
        return "flux-2-klein"
    if "flux-2" in endpoint:
        return "flux-2"
    return "generic"


def endpoint_for(endpoint: str, has_refs: bool) -> str:
    """Nano Banana 2 and FLUX.2 pair a text-to-image endpoint with an `/edit` one (verified schemas:
    `fal-ai/nano-banana-2[/edit]`, `fal-ai/flux-2-pro[/edit]`, `fal-ai/flux-2/klein/4b[/edit]`): pick by
    whether references are passed."""
    if family_of(endpoint) in ("nano-banana", "flux-2", "flux-2-klein"):
        base = endpoint.removesuffix("/edit")
        return f"{base}/edit" if has_refs else base
    return endpoint


def data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _has_transparency(img: Image.Image) -> bool:
    if img.mode == "P":
        return "transparency" in img.info
    if img.mode in ("RGBA", "LA"):
        extrema = cast(tuple[int, int], img.getchannel("A").getextrema())
        return extrema[0] < 255
    return False


def encode_ref(ref: RefImage, max_side: int = REF_MAX_SIDE) -> tuple[str, float]:
    """(data URI, megapixels) — downscaled; JPEG unless the image really uses transparency."""
    img = Image.open(io.BytesIO(ref.data))
    img.load()
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    if _has_transparency(img):
        img.convert("RGBA").save(buf, format="PNG", optimize=True)
        mime = "image/png"
    else:
        img.convert("RGB").save(buf, format="JPEG", quality=92)
        mime = "image/jpeg"
    return data_uri(buf.getvalue(), mime), img.size[0] * img.size[1] / FAL_MEGAPIXEL


def decode_data_uri(uri: str) -> tuple[bytes, str]:
    header, _, payload = uri.partition(",")
    mime = header.removeprefix("data:").split(";")[0] or "image/png"
    return base64.b64decode(payload), mime


def fal_error_summary(e: fal_client.FalClientHTTPError) -> tuple[str | None, str]:
    """(error type, short message) without the echoed input (it can hold our reference images)."""
    detail: Any = e.message
    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        return detail[0].get("type") or e.error_type, str(detail[0].get("msg", ""))[:200]
    if isinstance(detail, dict):
        return detail.get("type") or e.error_type, str(detail.get("msg", ""))[:200]
    return e.error_type, str(detail)[:200]


def raise_for_fal(e: Exception, endpoint: str) -> None:
    if isinstance(e, fal_client.FalClientTimeoutError):
        raise ProviderError(f"fal timeout on {endpoint}") from e
    if isinstance(e, fal_client.FalClientHTTPError):
        kind, msg = fal_error_summary(e)
        text = f"fal {e.status_code} {kind or ''} on {endpoint}: {msg}"
        if kind == "content_policy_violation":
            raise ContentBlocked(text) from e
        if e.status_code == 429 or e.status_code >= 500 or kind == "no_media_generated":
            raise ProviderError(text) from e
        raise ProviderConfigError(text) from e
    if isinstance(e, httpx.HTTPError):
        raise ProviderError(f"fal network error on {endpoint}: {type(e).__name__}") from e
    raise e


async def fetch_output(url: str) -> tuple[bytes, str]:
    """Inline data URI (sync_mode) or, if an endpoint ignores sync_mode, a fal CDN URL."""
    if url.startswith("data:"):
        return decode_data_uri(url)
    parsed = httpx.URL(url)
    if parsed.scheme != "https" or not parsed.host.endswith(_ALLOWED_HOSTS):
        raise ProviderError(f"fal returned an unexpected file location ({parsed.host})")
    async with httpx.AsyncClient(timeout=60, follow_redirects=False) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        if len(resp.content) > _MAX_DOWNLOAD:
            raise ProviderError("fal output too large")
        return resp.content, resp.headers.get("content-type", "image/png").split(";")[0]


def image_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as img:
        return img.size


class FalImageProvider:
    name = "fal"

    def __init__(self, api_key: str | None, model: str, *, client: FalClient | None = None) -> None:
        if client is None:
            if not api_key:
                raise ProviderConfigError("fal key is not set (admin → settings → AI keys)")
            client = fal_client.AsyncClient(key=api_key, default_timeout=300)
        self._client = client
        self.model = model
        self.family = family_of(model)

    @property
    def max_refs(self) -> int:
        return MAX_REFS[self.family]

    def build(self, req: ImageRequest) -> tuple[str, dict[str, Any], float]:
        """(endpoint, arguments, input megapixels) for this request."""
        refs = req.refs[: MAX_REFS[self.family]]
        max_side = KLEIN_REF_MAX_SIDE if self.family == "flux-2-klein" else REF_MAX_SIDE
        encoded = [encode_ref(r, max_side) for r in refs]
        in_mp = sum(mp for _, mp in encoded)
        endpoint = endpoint_for(self.model, bool(refs))
        labels = "\n".join(f"Image {i + 1}: {r.label}" for i, r in enumerate(refs))
        prompt = f"{labels}\n\n{req.prompt}" if refs else req.prompt
        args: dict[str, Any] = {"prompt": prompt, "sync_mode": True}
        if refs:
            args["image_urls"] = [uri for uri, _ in encoded]
        if req.seed is not None:
            args["seed"] = req.seed
        if self.family == "nano-banana":
            # Nano Banana Pro has no 0.5K tier (1K/2K/4K, fal schema checked 2026-10-02)
            pro_floor = "nano-banana-pro" in endpoint and req.resolution == "0.5K"
            args |= {
                "aspect_ratio": req.aspect,
                "resolution": "1K" if pro_floor else req.resolution,
                "num_images": 1,
                "output_format": "png",
                "limit_generations": True,
            }
        elif self.family in ("flux-2", "flux-2-klein"):
            w, h = req.size or aspect_px(req.aspect, TIER_PX[req.resolution])
            args |= {
                "image_size": {"width": w, "height": h},
                "output_format": "png",
                "enable_safety_checker": True,
            }
            if self.family == "flux-2":
                args["safety_tolerance"] = "2"
            else:
                args["num_images"] = 1
        return endpoint, args, in_mp

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        endpoint, args, in_mp = self.build(req)
        try:
            result = await self._client.subscribe(endpoint, arguments=args, headers=PRIVACY_HEADERS)
        except (fal_client.FalClientError, httpx.HTTPError) as e:
            raise_for_fal(e, endpoint)
            raise  # unreachable: raise_for_fal always raises
        if not isinstance(result, dict):
            raise ProviderError(f"fal returned an unexpected payload on {endpoint}")
        if any(result.get("has_nsfw_concepts") or []):
            raise ContentBlocked(f"fal safety checker flagged the output on {endpoint}")
        images = result.get("images") or ([result["image"]] if result.get("image") else [])
        if not images:
            raise ProviderError(f"fal returned no image on {endpoint}")
        data, mime = await fetch_output(images[0]["url"])
        w, h = image_size(data)
        usd = fal_cost(endpoint, resolution=req.resolution, out_px=(w, h), in_megapixels=in_mp)
        cost = CostEntry(
            step=req.step,
            provider=self.name,
            model=endpoint,
            units={
                "images": 1,
                "input_megapixels": round(in_mp, 2),
                "output_megapixels": round(w * h / FAL_MEGAPIXEL, 2),
            },
            usd=usd if usd is not None else fal_unknown_price(),
            estimated=True,  # fal bills per request; we price it from the published table
        )
        return GeneratedImage(
            data=data,
            mime=mime,
            cost=cost,
            params={
                "provider": self.name,
                "model": endpoint,
                "resolution": req.resolution,
                "aspect": req.aspect,
                "size": f"{w}x{h}",
                "seed": result.get("seed", req.seed),
            },
        )
