import base64
import json
from typing import Any

import fal_client
import httpx
import pytest
from tests_helpers import png

from qamra_ai.errors import ContentBlocked, ProviderConfigError, ProviderError
from qamra_ai.image.base import ImageRequest, RefImage
from qamra_ai.image.fal import PRIVACY_HEADERS, FalImageProvider, endpoint_for, fetch_output
from qamra_ai.image.upscale import FalUpscaler, LocalUpscaler, needed_factor


def _uri(data: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


class FakeFal:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.result = (
            result if result is not None else {"images": [{"url": _uri(png("blue", (64, 64)))}], "seed": 7}
        )
        self.error = error

    async def subscribe(
        self, application: str, arguments: dict[str, Any], *, headers: dict[str, str] | None = None
    ) -> Any:
        self.calls.append({"endpoint": application, "args": arguments, "headers": headers})
        if self.error:
            raise self.error
        return self.result


def _refs(n: int) -> list[RefImage]:
    return [RefImage(png("red", (300, 200)), "image/png", f"ref {i}") for i in range(n)]


def _http_error(status: int, detail: Any) -> fal_client.FalClientHTTPError:
    resp = httpx.Response(
        status, json={"detail": detail}, request=httpx.Request("POST", "https://queue.fal.run/x")
    )
    return fal_client.FalClientHTTPError(
        json.dumps(detail) if not isinstance(detail, list) else detail, status, {}, resp
    )  # type: ignore[arg-type]


def test_endpoint_pairs() -> None:
    assert endpoint_for("fal-ai/nano-banana-2", True) == "fal-ai/nano-banana-2/edit"
    assert endpoint_for("fal-ai/nano-banana-2/edit", False) == "fal-ai/nano-banana-2"
    assert endpoint_for("fal-ai/flux-2-pro/edit", False) == "fal-ai/flux-2-pro"
    assert endpoint_for("fal-ai/flux-2-pro", True) == "fal-ai/flux-2-pro/edit"
    assert endpoint_for("someone/model", True) == "someone/model"


async def test_nano_banana_request_shape_and_privacy() -> None:
    fake = FakeFal()
    provider = FalImageProvider(None, "fal-ai/nano-banana-2", client=fake)
    img = await provider.generate(
        ImageRequest(step="page:1:a1", prompt="P", refs=_refs(2), aspect="16:9", resolution="1K", seed=5)
    )
    call = fake.calls[0]
    assert call["endpoint"] == "fal-ai/nano-banana-2/edit"
    args = call["args"]
    assert args["aspect_ratio"] == "16:9" and args["resolution"] == "1K" and args["num_images"] == 1
    assert args["sync_mode"] is True and args["seed"] == 5 and args["limit_generations"] is True
    assert all(u.startswith("data:image/jpeg;base64,") for u in args["image_urls"])  # inline, never uploaded
    assert args["prompt"].startswith("Image 1: ref 0\nImage 2: ref 1\n\nP")
    assert call["headers"] == PRIVACY_HEADERS and call["headers"]["X-Fal-Store-IO"] == "0"
    assert (
        json.loads(call["headers"]["X-Fal-Object-Lifecycle-Preference"])["expiration_duration_seconds"] <= 900
    )
    assert img.cost.usd == pytest.approx(0.08) and img.cost.model == "fal-ai/nano-banana-2/edit"
    assert img.params["seed"] == 7 and img.params["size"] == "64x64"


async def test_nano_banana_without_refs_uses_text_to_image_and_preview_price() -> None:
    fake = FakeFal()
    provider = FalImageProvider(None, "fal-ai/nano-banana-2", client=fake)
    img = await provider.generate(ImageRequest(step="plate", prompt="P", resolution="0.5K"))
    assert fake.calls[0]["endpoint"] == "fal-ai/nano-banana-2"
    assert "image_urls" not in fake.calls[0]["args"]
    assert img.cost.usd == pytest.approx(0.06)


async def test_references_are_capped_per_family() -> None:
    fake = FakeFal()
    await FalImageProvider(None, "fal-ai/flux-2-pro/edit", client=fake).generate(
        ImageRequest(step="s", prompt="P", refs=_refs(12))
    )
    assert len(fake.calls[0]["args"]["image_urls"]) == 9


async def test_flux_uses_pixel_size() -> None:
    fake = FakeFal()
    await FalImageProvider(None, "fal-ai/flux-2-pro/edit", client=fake).generate(
        ImageRequest(step="s", prompt="P", refs=_refs(1), aspect="3:2", resolution="1K")
    )
    args = fake.calls[0]["args"]
    assert args["image_size"] == {"width": 1024, "height": 688}
    assert args["enable_safety_checker"] is True and "resolution" not in args


async def test_generic_endpoint_gets_minimal_arguments() -> None:
    fake = FakeFal()
    img = await FalImageProvider(None, "someone/new-model", client=fake).generate(
        ImageRequest(step="s", prompt="P", refs=_refs(1), seed=1)
    )
    assert set(fake.calls[0]["args"]) == {"prompt", "sync_mode", "image_urls", "seed"}
    assert img.cost.usd == pytest.approx(0.15)  # conservative budget price for unknown endpoints


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            _http_error(422, [{"type": "content_policy_violation", "msg": "flagged", "input": "SECRET"}]),
            ContentBlocked,
        ),
        (_http_error(503, [{"type": "runner_server_error", "msg": "down"}]), ProviderError),
        (_http_error(429, "slow down"), ProviderError),
        (_http_error(422, [{"type": "no_media_generated", "msg": "none"}]), ProviderError),
        (_http_error(400, [{"type": "bad_request", "msg": "bad", "input": "SECRET"}]), ProviderConfigError),
        (fal_client.FalClientTimeoutError(timeout=1.0), ProviderError),
    ],
)
async def test_errors_are_mapped_without_echoing_input(error: Exception, expected: type[Exception]) -> None:
    provider = FalImageProvider(None, "fal-ai/nano-banana-2", client=FakeFal(error=error))
    with pytest.raises(expected) as e:
        await provider.generate(ImageRequest(step="s", prompt="P"))
    assert "SECRET" not in str(e.value)


async def test_nsfw_flag_blocks() -> None:
    fake = FakeFal(result={"images": [{"url": _uri(png())}], "has_nsfw_concepts": [True]})
    with pytest.raises(ContentBlocked):
        await FalImageProvider(None, "fal-ai/flux-2-pro/edit", client=fake).generate(
            ImageRequest(step="s", prompt="P", refs=_refs(1))
        )


def test_missing_key_is_a_config_error() -> None:
    with pytest.raises(ProviderConfigError):
        FalImageProvider(None, "fal-ai/nano-banana-2")


async def test_output_urls_must_be_fal_https() -> None:
    with pytest.raises(ProviderError):
        await fetch_output("http://evil.example.com/x.png")
    with pytest.raises(ProviderError):
        await fetch_output("https://evil.example.com/x.png")


def test_needed_factor() -> None:
    assert needed_factor((1024, 1024), (2551, 2551)) == pytest.approx(2.5)
    assert needed_factor((1376, 768), (5031, 2551)) == pytest.approx(3.7)
    assert needed_factor((4000, 4000), (2551, 2551)) == 1.0


async def test_seedvr_upscaler_request() -> None:
    out = png("green", (256, 256))
    fake = FakeFal(result={"image": {"url": _uri(out)}, "seed": 1})
    up = FalUpscaler(None, "fal-ai/seedvr/upscale/image", client=fake)
    result = await up.upscale(png("red", (100, 100)), step="upscale:1", target=(250, 250))
    args = fake.calls[0]["args"]
    assert args["upscale_mode"] == "factor" and args["upscale_factor"] == pytest.approx(2.5)
    assert args["sync_mode"] is True and fake.calls[0]["headers"] == PRIVACY_HEADERS
    assert result.cost.usd == pytest.approx(256 * 256 / (1024 * 1024) * 0.001, abs=1e-6)


async def test_recraft_upscaler_sends_png() -> None:
    fake = FakeFal(result={"image": {"url": _uri(png())}})
    await FalUpscaler(None, "fal-ai/recraft/upscale/crisp", client=fake).upscale(
        png(), step="u", target=(100, 100)
    )
    assert fake.calls[0]["args"]["image_url"].startswith("data:image/png;base64,")


async def test_local_upscaler_covers_target() -> None:
    result = await LocalUpscaler().upscale(png("red", (100, 50)), step="u", target=(260, 120))
    import io

    from PIL import Image

    w, h = Image.open(io.BytesIO(result.data)).size
    assert w >= 260 and h >= 120 and result.cost.usd == 0
