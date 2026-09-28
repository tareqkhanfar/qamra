import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from qamra_ai.errors import ProviderConfigError, ProviderError
from qamra_ai.image import comfy
from qamra_ai.image.base import ImageRequest, RefImage
from qamra_ai.image.comfy import ComfyImageProvider, fill, health
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.image.fallback import FallbackImageProvider

GRAPH = {
    "3": {"class_type": "KSampler", "inputs": {"seed": "{{seed}}", "steps": 4}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{prompt}}"}},
    "9": {"class_type": "LoadImage", "inputs": {"image": "{{image_1}}"}},
    "12": {"class_type": "EmptyLatentImage", "inputs": {"width": "{{width}}", "height": "{{height}}"}},
}


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "tan").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "klein-edit.json").write_text(json.dumps(GRAPH), encoding="utf-8")
    monkeypatch.setitem(comfy.APPROVED_WORKFLOWS, "klein-edit", "FLUX.2 [klein] 4B — Apache 2.0")
    return tmp_path


class Server:
    """A tiny ComfyUI: the job finishes on the second look at its history."""

    def __init__(self) -> None:
        self.queued: dict[str, object] = {}
        self.looks = 0
        self.forgotten: list[str] = []
        self.auth: set[str] = set()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.auth.add(request.headers.get("authorization", ""))
        path = request.url.path
        if path == "/upload/image":
            return httpx.Response(200, json={"name": "qamra-ref.png", "subfolder": "", "type": "input"})
        if path == "/prompt":
            self.queued = json.loads(request.content)["prompt"]
            return httpx.Response(200, json={"prompt_id": "p1", "number": 1})
        if path == "/history/p1":
            self.looks += 1
            if self.looks < 2:
                return httpx.Response(200, json={})
            outputs = {"20": {"images": [{"filename": "out_00001_.png", "subfolder": "", "type": "output"}]}}
            return httpx.Response(200, json={"p1": {"outputs": outputs, "status": {"status_str": "success"}}})
        if path == "/view":
            return httpx.Response(200, content=png())
        if path == "/history":
            self.forgotten += json.loads(request.content)["delete"]
            return httpx.Response(200, json={})
        return httpx.Response(404)


async def _no_wait(_: float) -> None:
    return None


def test_fill_keeps_numbers_as_numbers() -> None:
    out = fill(GRAPH, {"seed": 7, "prompt": "a girl", "image_1": "ref.png", "width": 1024, "height": 688})
    assert out["3"]["inputs"]["seed"] == 7 and out["12"]["inputs"]["height"] == 688
    assert fill("hero: {{prompt}}!", {"prompt": "ليان"}) == "hero: ليان!"


def test_only_an_approved_workflow_runs(tmp_path: Path) -> None:
    (tmp_path / "klein-edit.json").write_text(json.dumps(GRAPH), encoding="utf-8")
    with pytest.raises(ProviderConfigError, match="approved commercial license"):
        ComfyImageProvider("http://gpu", "t", "klein-edit", folder=tmp_path)
    with pytest.raises(ProviderConfigError, match="URL"):
        ComfyImageProvider("", "t", "klein-edit", folder=tmp_path)


async def test_a_job_is_queued_drawn_downloaded_and_forgotten(approved: Path) -> None:
    server = Server()
    provider = ComfyImageProvider(
        "http://gpu:8188", "secret-token", "klein-edit", folder=approved,
        transport=httpx.MockTransport(server), sleep=_no_wait,
    )  # fmt: skip
    ref = RefImage(png(), "image/png", "the child's portrait")
    out = await provider.generate(
        ImageRequest(step="classic:3", prompt="a girl", refs=[ref], aspect="3:2", seed=42)
    )
    assert out.mime == "image/png" and out.cost.usd == 0.0 and out.cost.provider == "self_hosted"
    assert out.params["seed"] == 42 and out.params["model"] == "klein-edit"
    queued = server.queued
    assert isinstance(queued, dict)
    assert queued["3"]["inputs"]["seed"] == 42 and queued["9"]["inputs"]["image"] == "qamra-ref.png"
    assert server.forgotten == ["p1"] and server.auth == {"Bearer secret-token"}


async def test_when_the_gpu_server_is_down_fal_draws_instead(approved: Path) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider = ComfyImageProvider(
        "http://gpu:8188", None, "klein-edit", folder=approved, transport=httpx.MockTransport(down)
    )
    with pytest.raises(ProviderError):
        await provider.generate(ImageRequest(step="classic:1", prompt="p"))
    both = FallbackImageProvider(provider, FakeImageProvider(), switch_after=1, sleep=_no_wait)
    out = await both.generate(ImageRequest(step="classic:1", prompt="p"))
    assert out.data and both.switches == 1


async def test_health_reports_the_gpus() -> None:
    stats = {"devices": [{"name": "cuda:0 NVIDIA L4", "vram_total": 24 * 2**30, "vram_free": 20 * 2**30}]}
    up = httpx.MockTransport(lambda r: httpx.Response(200, json=stats))
    result = await health("http://gpu:8188", "t", transport=up)
    assert result["ok"] and result["devices"][0] == {
        "name": "cuda:0 NVIDIA L4",
        "vram_gb": 24.0,
        "free_gb": 20.0,
    }
    down = httpx.MockTransport(lambda r: httpx.Response(502))
    assert (await health("http://gpu:8188", None, transport=down)) == {"ok": False, "error": "HTTP 502"}
