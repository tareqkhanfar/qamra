"""Offline image provider for tests and dry runs: draws a labelled placeholder with ref thumbnails."""

import hashlib
import io

from PIL import Image, ImageDraw

from qamra_ai.cost import CostEntry
from qamra_ai.image.base import GeneratedImage, ImageRequest, aspect_px


class FakeImageProvider:
    name = "fake"
    model = "fake-image-1"

    def __init__(self, long_side: int = 1024) -> None:
        self._long_side = long_side
        self.requests: list[ImageRequest] = []

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        self.requests.append(req)
        w, h = aspect_px(req.aspect, self._long_side)
        digest = hashlib.sha256(req.prompt.encode()).digest()
        sky = (34 + digest[0] % 40, 48 + digest[1] % 40, 106 + digest[2] % 60)
        img = Image.new("RGB", (w, h), sky)
        draw = ImageDraw.Draw(img)
        # moon + ground so pages look like "scenes" in the PDF
        r = w // 10
        draw.ellipse((w - 2 * r - w // 12, h // 10, w - w // 12, h // 10 + 2 * r), fill="#F2B33D")
        draw.rectangle((0, int(h * 0.72), w, h), fill=(62 + digest[3] % 30, 107, 77))
        thumb = w // 4
        for i, ref in enumerate(req.refs):
            t = Image.open(io.BytesIO(ref.data)).convert("RGB")
            t.thumbnail((thumb, thumb))
            img.paste(t, (w // 16 + i * (thumb + w // 32), int(h * 0.45)))
        draw.text((w // 16, int(h * 0.9)), f"{req.step}", fill="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        cost = CostEntry(req.step, self.name, self.model, {"images": 1}, 0.0)
        return GeneratedImage(buf.getvalue(), "image/png", cost, {"provider": self.name})
