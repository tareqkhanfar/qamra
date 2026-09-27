"""Per-step cost ledger. Every provider call records a `CostEntry` (stored later as `GenerationCost`)."""

import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PRICING_FILE = Path(__file__).parent / "pricing.yaml"


@lru_cache
def pricing() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(PRICING_FILE.read_text(encoding="utf-8"))
    return data


@dataclass(frozen=True)
class CostEntry:
    step: str  # e.g. "story", "page:3", "character", "judge:3"
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
        """Totals per step family ("page:3" → "page")."""
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


def anthropic_cost(model: str, usage: dict[str, int]) -> float:
    p = pricing()["anthropic"].get(model)
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


def fal_cost(model: str, megapixels: float) -> float:
    p = pricing()["fal"].get(model)
    if p is None:
        return 0.0
    mp = math.ceil(megapixels)
    return float(p["first_mp"] + max(0, mp - 1) * p["extra_mp"])
