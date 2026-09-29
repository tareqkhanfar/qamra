"""Per-step cost ledger. Every provider call records a `CostEntry` (stored later as `GenerationCost`)."""

import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PRICING_FILE = Path(__file__).parent / "pricing.yaml"
_DATE_SUFFIX = re.compile(r"-\d{8}$")
FAL_MEGAPIXEL = 1024 * 1024  # fal's unit: "a 1024x1024 image will cost $0.03" (FLUX.2 pricing page)


@lru_cache
def pricing() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(PRICING_FILE.read_text(encoding="utf-8"))
    return data


@dataclass(frozen=True)
class CostEntry:
    step: str  # e.g. "story", "page:3:a1", "cover:a1", "qa:3:a1", "upscale:3"
    provider: str
    model: str
    units: dict[str, float]
    usd: float
    estimated: bool = False  # true when priced from a formula rather than reported usage


@dataclass
class CostLedger:
    entries: list[CostEntry] = field(default_factory=list)

    def add(self, entry: CostEntry) -> None:
        self.entries.append(entry)

    @property
    def total_usd(self) -> float:
        return round(sum(e.usd for e in self.entries), 4)

    def by_group(self) -> dict[str, float]:
        """Totals per step family ("page:3:a1" → "page")."""
        totals: dict[str, float] = defaultdict(float)
        for e in self.entries:
            totals[e.step.split(":")[0]] += e.usd
        return {k: round(v, 4) for k, v in sorted(totals.items())}

    def by_provider(self) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for e in self.entries:
            totals[f"{e.provider}/{e.model}"] += e.usd
        return {k: round(v, 4) for k, v in sorted(totals.items())}

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_usd": self.total_usd,
            "by_group": self.by_group(),
            "by_provider": self.by_provider(),
            "entries": [asdict(e) for e in self.entries],
        }


def _anthropic_prices(model: str) -> dict[str, float] | None:
    table: dict[str, dict[str, float]] = pricing()["anthropic"]
    return table.get(model) or table.get(_DATE_SUFFIX.sub("", model))


def anthropic_cost(model: str, usage: dict[str, int]) -> float:
    p = _anthropic_prices(model)
    if p is None:
        return 0.0
    return (
        float(
            usage.get("input_tokens", 0) * p["input"]
            + usage.get("output_tokens", 0) * p["output"]
            + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
            + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]
        )
        / 1_000_000
    )


def anthropic_estimate(model: str, input_tokens: int, output_tokens: int) -> float:
    """Upper-bound style estimate for the budget guard (no cache discount assumed)."""
    p = _anthropic_prices(model) or {"input": 5.0, "output": 25.0}  # unknown model: assume Opus prices
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def gemini_cost(model: str, size: str, n_output: int, n_input_images: int) -> float:
    p = pricing()["gemini"].get(model)
    if p is None:
        return 0.0
    return float(n_output * p["output"][size] + n_input_images * p["input_image"])


def openai_image_cost(model: str, text_in: int, image_in: int, output: int) -> float:
    p = pricing()["openai"].get(model)
    if p is None:
        return 0.0
    return float(text_in * p["text_input"] + image_in * p["image_input"] + output * p["output"]) / 1e6


def fal_cost(
    endpoint: str,
    *,
    resolution: str | None = None,
    out_px: tuple[int, int] | None = None,
    in_megapixels: float = 0.0,
) -> float | None:
    """Price of one fal call from pricing.yaml, or None when the endpoint is not listed.

    per_image (Nano Banana, Recraft): flat price × resolution multiplier.
    first_mp/extra_mp (FLUX.2): megapixels rounded up; inputs billed when `bill_inputs`.
    per_mp (SeedVR, FLUX.2 [klein]): per output megapixel, plus the input megapixels when `bill_inputs`
    (klein: "per megapixel of input and output", not rounded).
    """
    p: dict[str, Any] | None = pricing()["fal"].get(endpoint)
    if p is None:
        return None
    if "per_image" in p:
        mult = float(p.get("resolution", {}).get(resolution or "1K", 1.0))
        return round(float(p["per_image"]) * mult, 6)
    out_mp = (out_px[0] * out_px[1] / FAL_MEGAPIXEL) if out_px else 1.0
    if "per_mp" in p:
        billed_mp = out_mp + (in_megapixels if p.get("bill_inputs") else 0.0)
        return round(float(p["per_mp"]) * billed_mp, 6)
    billed = math.ceil(out_mp - 1e-9) + (math.ceil(in_megapixels - 1e-9) if p.get("bill_inputs") else 0)
    return round(float(p["first_mp"]) + max(0, billed - 1) * float(p["extra_mp"]), 6)


def fal_unknown_price(kind: str = "image") -> float:
    return float(pricing()["fal_unknown_upscale_usd" if kind == "upscale" else "fal_unknown_image_usd"])
