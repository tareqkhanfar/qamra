"""What every step needs: providers, settings, the cost ledger, the per-book budget and cost callbacks."""

import io
from collections.abc import Callable
from dataclasses import dataclass, field

from PIL import Image

from qamra_ai.config import Settings
from qamra_ai.cost import (
    FAL_MEGAPIXEL,
    CostEntry,
    CostLedger,
    anthropic_estimate,
    fal_cost,
    fal_unknown_price,
)
from qamra_ai.image.base import GeneratedImage, ImageProvider, ImageRequest
from qamra_ai.image.upscale import LocalUpscaler, Upscaled, Upscaler
from qamra_ai.pipeline.budget import Budget
from qamra_ai.text.base import Effort, StructuredResult, System, T, TextProvider, UserPart

# Rough token sizes for the budget guard's reservations (actual usage is recorded afterwards).
ESTIMATES = {
    "story": (9000, 9000),
    "safety": (6000, 600),
    "qa": (8000, 700),
    "check": (4000, 700),
}


def _mp(data: bytes) -> float:
    """Megapixels of an image (fal's unit), read from its header only."""
    with Image.open(io.BytesIO(data)) as img:
        return float(img.size[0] * img.size[1]) / FAL_MEGAPIXEL


@dataclass
class Runtime:
    settings: Settings
    text: TextProvider
    image: ImageProvider
    upscaler: Upscaler = field(default_factory=LocalUpscaler)
    ledger: CostLedger = field(default_factory=CostLedger)
    budget: Budget | None = None  # None: no cap (per-child steps, scripts)
    on_cost: Callable[[CostEntry], None] | None = None  # e.g. write a GenerationCost row right away

    def _record(self, entry: CostEntry) -> None:
        self.ledger.add(entry)
        if self.budget is not None:
            self.budget.add(entry.usd)
        if self.on_cost is not None:
            self.on_cost(entry)

    # ---- estimates --------------------------------------------------------------------------

    def image_estimate(self, req: ImageRequest) -> float:
        if self.image.name in ("fake", "sketch"):
            return 0.0
        model = self.image.model
        if self.image.name == "self_hosted":
            # our own GPU costs nothing per image; budget for the fal fallback in case it has to draw
            fallback = getattr(self.image, "fallback", None)
            if fallback is None or fallback.name != "fal":
                return 0.0
            model = fallback.model
        if self.image.name in ("fal", "self_hosted"):
            from qamra_ai.image.fal import endpoint_for

            model = endpoint_for(model, bool(req.refs))
            if req.size is not None:  # exact size: 1 MP-capped references (klein), known output
                in_mp = sum(min(1.0, _mp(r.data)) for r in req.refs)
                price = fal_cost(model, resolution=req.resolution, out_px=req.size, in_megapixels=in_mp)
            else:
                price = fal_cost(model, resolution=req.resolution, in_megapixels=len(req.refs) * 1.5)
            return price if price is not None else fal_unknown_price()
        return fal_unknown_price()  # direct Gemini/OpenAI: conservative flat estimate

    def upscale_estimate(self, target: tuple[int, int]) -> float:
        if self.upscaler.name == "local":
            return 0.0
        price = fal_cost(self.upscaler.model, out_px=(round(target[0] * 1.1), round(target[1] * 1.1)))
        return price if price is not None else fal_unknown_price("upscale")

    def text_estimate(self, kind: str, fast: bool) -> float:
        if self.text.name == "fake":
            return 0.0
        tokens_in, tokens_out = ESTIMATES[kind]
        model = self.settings.text_model_fast if fast else self.settings.text_model
        return anthropic_estimate(model, tokens_in, tokens_out)

    # ---- calls ------------------------------------------------------------------------------

    async def draw(self, req: ImageRequest) -> GeneratedImage:
        """Image call (retries + fallback live in the provider); cost recorded and budgeted."""
        if self.budget is None:
            result = await self.image.generate(req)
        else:
            async with self.budget.reserve(self.image_estimate(req), req.step):
                result = await self.image.generate(req)
        self._record(result.cost)
        return result

    async def upscale(self, data: bytes, *, step: str, target: tuple[int, int]) -> Upscaled:
        if self.budget is None:
            result = await self.upscaler.upscale(data, step=step, target=target)
        else:
            async with self.budget.reserve(self.upscale_estimate(target), step):
                result = await self.upscaler.upscale(data, step=step, target=target)
        self._record(result.cost)
        return result

    async def ask(
        self,
        *,
        step: str,
        system: System,
        user: list[UserPart],
        schema: type[T],
        fast: bool = False,
        kind: str = "check",
        effort: Effort | None = None,
        max_tokens: int = 16000,
    ) -> T:
        model = self.settings.text_model_fast if fast else self.settings.text_model

        async def call() -> StructuredResult[T]:
            return await self.text.structured(
                step=step,
                model=model,
                system=system,
                user=user,
                schema=schema,
                effort=effort,
                max_tokens=max_tokens,
            )

        if self.budget is None:
            result = await call()
        else:
            async with self.budget.reserve(self.text_estimate(kind, fast), step):
                result = await call()
        self._record(result.cost)
        return result.value
