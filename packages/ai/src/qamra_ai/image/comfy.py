"""Self-hosted image provider: our own ComfyUI server over HTTP (Addendum 4 §8), for Classic template edits.

Prepared, not active. It runs only a workflow whose model has a commercial license recorded in
docs/licenses.md and approved by Tareq: `APPROVED_WORKFLOWS` starts empty, and any other workflow is a
configuration error, so the fallback (fal) draws instead. The server is ours and private: requests carry a
bearer token, and docs/runbooks/self-hosted-gpu.md keeps its inputs and outputs on a wiped tmpfs.

ComfyUI's HTTP API: POST /upload/image (references), POST /prompt (queue a workflow graph), GET
/history/{id} (outputs), GET /view (the image), POST /history {"delete": [...]} (forget the job), and GET
/system_stats (health).
"""

import asyncio
import json
import secrets
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from qamra_ai.cost import CostEntry
from qamra_ai.errors import InvalidOutput, ProviderConfigError, ProviderError
from qamra_ai.image.base import TIER_PX, GeneratedImage, ImageRequest, RefImage, aspect_px, sniff_mime

WORKFLOWS_DIR = Path(__file__).parent / "comfy_workflows"
# Workflow file name (without .json) → its model and license. Add one only after Tareq approves the license
# in docs/licenses.md (Addendum 4 §8). FLUX.2 [klein] 4B (Apache 2.0) is the only candidate so far.
APPROVED_WORKFLOWS: dict[str, str] = {}
_MAX_IMAGE = 40 * 1024 * 1024

Sleep = Callable[[float], Awaitable[None]]


def fill(node: Any, values: dict[str, Any]) -> Any:
    """Put the request into a workflow graph: a string that is exactly "{{name}}" becomes the value itself
    (numbers stay numbers); "{{name}}" inside a longer string is replaced by its text."""
    if isinstance(node, dict):
        return {k: fill(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [fill(v, values) for v in node]
    if isinstance(node, str):
        for key, value in values.items():
            token = "{{" + key + "}}"
            if node == token:
                return value
            node = node.replace(token, str(value))
    return node


def load_workflow(name: str, folder: Path | None = None) -> dict[str, Any]:
    if name not in APPROVED_WORKFLOWS:
        raise ProviderConfigError(f"workflow {name!r} has no approved commercial license (docs/licenses.md)")
    path = (folder or WORKFLOWS_DIR) / f"{name}.json"
    if not path.is_file():
        raise ProviderConfigError(f"workflow file {path.name} is missing")
    graph: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return graph


class ComfyImageProvider:
    """One image per request; references are uploaded as `{{image_1}}`, `{{image_2}}`… for the workflow."""

    name = "self_hosted"

    def __init__(
        self,
        base_url: str | None,
        token: str | None,
        workflow: str,
        *,
        folder: Path | None = None,
        timeout: float = 180.0,
        poll: float = 1.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if not base_url:
            raise ProviderConfigError("the self-hosted image server URL is not set")
        self.base_url = base_url.rstrip("/")
        self.model = workflow
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._graph = load_workflow(workflow, folder)
        self._timeout, self._poll = timeout, poll
        self._transport, self._sleep = transport, sleep

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, headers=self._headers, timeout=30.0, transport=self._transport
        )

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        started = time.monotonic()
        seed = req.seed if req.seed is not None else secrets.randbelow(2**31)
        width, height = req.size or aspect_px(req.aspect, TIER_PX[req.resolution])
        try:
            async with self._client() as http:
                names = [await self._upload(http, ref) for ref in req.refs]
                values: dict[str, Any] = {
                    "prompt": req.prompt,
                    "seed": seed,
                    "width": width,
                    "height": height,
                }
                values |= {f"image_{i}": n for i, n in enumerate(names, 1)}
                prompt_id = await self._queue(http, fill(self._graph, values))
                output = await self._wait(http, prompt_id)
                data = await self._download(http, output)
                await http.post("/history", json={"delete": [prompt_id]})  # forget the job on the server
        except httpx.HTTPError as e:  # down, timed out, refused: the fallback draws instead
            raise ProviderError(f"self-hosted server: {type(e).__name__}") from e
        seconds = round(time.monotonic() - started, 1)
        cost = CostEntry(req.step, self.name, self.model, {"images": 1, "seconds": seconds}, 0.0)
        params = {"provider": self.name, "model": self.model, "seed": seed, "width": width, "height": height}
        return GeneratedImage(data, sniff_mime(data), cost, params)

    async def _upload(self, http: httpx.AsyncClient, ref: RefImage) -> str:
        ext = {"image/png": "png", "image/webp": "webp"}.get(ref.mime, "jpg")
        files = {"image": (f"qamra-{uuid.uuid4().hex}.{ext}", ref.data, ref.mime)}
        r = await http.post("/upload/image", files=files, data={"type": "input", "overwrite": "true"})
        self._check(r, "upload")
        body = r.json()
        sub = body.get("subfolder") or ""
        return f"{sub}/{body['name']}" if sub else str(body["name"])

    async def _queue(self, http: httpx.AsyncClient, graph: dict[str, Any]) -> str:
        r = await http.post("/prompt", json={"prompt": graph, "client_id": "qamra"})
        self._check(r, "prompt")
        prompt_id = r.json().get("prompt_id")
        if not prompt_id:
            raise InvalidOutput("the self-hosted server queued nothing")
        return str(prompt_id)

    async def _wait(self, http: httpx.AsyncClient, prompt_id: str) -> dict[str, str]:
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            r = await http.get(f"/history/{prompt_id}")
            self._check(r, "history")
            job = r.json().get(prompt_id) or {}
            if job.get("status", {}).get("status_str") == "error":
                raise ProviderError("the self-hosted workflow failed")
            for node in (job.get("outputs") or {}).values():
                for image in node.get("images") or []:
                    if image.get("type", "output") == "output":
                        return {k: str(image.get(k, "")) for k in ("filename", "subfolder", "type")}
            await self._sleep(self._poll)
        raise ProviderError("the self-hosted server timed out")

    async def _download(self, http: httpx.AsyncClient, image: dict[str, str]) -> bytes:
        r = await http.get("/view", params=image)
        self._check(r, "view")
        if len(r.content) > _MAX_IMAGE or sniff_mime(r.content) == "application/octet-stream":
            raise InvalidOutput("the self-hosted server returned something that is not an image")
        return r.content

    @staticmethod
    def _check(r: httpx.Response, step: str) -> None:
        if r.status_code >= 500 or r.status_code == 429:
            raise ProviderError(f"self-hosted {step}: HTTP {r.status_code}")
        if r.status_code >= 400:  # a bad workflow or token: not worth retrying here
            raise ProviderConfigError(f"self-hosted {step}: HTTP {r.status_code}")


async def health(
    base_url: str,
    token: str | None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Is the GPU server up? Its GPUs and free memory (ComfyUI /system_stats), for the admin."""
    started = time.monotonic()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers, transport=transport) as http:
            r = await http.get(base_url.rstrip("/") + "/system_stats")
    except httpx.HTTPError as e:
        return {"ok": False, "error": type(e).__name__}
    if r.status_code != 200:
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    devices = [
        {
            "name": str(d.get("name", "")),
            "vram_gb": round(float(d.get("vram_total", 0)) / 2**30, 1),
            "free_gb": round(float(d.get("vram_free", 0)) / 2**30, 1),
        }
        for d in r.json().get("devices", [])
    ]
    return {"ok": True, "latency_ms": round((time.monotonic() - started) * 1000), "devices": devices}
