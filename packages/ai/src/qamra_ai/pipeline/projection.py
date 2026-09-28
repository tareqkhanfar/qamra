"""What a run would cost on the real providers (Addendum 3 report: cost per book before keys exist).

Image and upscale calls are priced exactly from pricing.yaml. Claude calls are priced from typical token
sizes (below), because offline runs have no real usage; real runs record the provider's reported usage.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from qamra_ai.config import Settings
from qamra_ai.cost import CostLedger, anthropic_cost, fal_cost

# Typical usage per call (tokens), measured on prompt sizes; replace with real usage after the first runs.
TYPICAL = {
    "story": {"input_tokens": 3500, "cache_creation_input_tokens": 2000, "output_tokens": 6000},
    "story:safety": {"input_tokens": 5000, "output_tokens": 300},
    "qa_first": {"input_tokens": 1500, "cache_creation_input_tokens": 4200, "output_tokens": 250},
    "qa_cached": {"input_tokens": 1500, "cache_read_input_tokens": 4200, "output_tokens": 250},
    "check": {"input_tokens": 3000, "output_tokens": 300},
}


def _tier(px: float) -> str:
    return "0.5K" if px <= 600 else "1K" if px <= 1200 else "2K" if px <= 2400 else "4K"


@dataclass
class Projection:
    lines: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def total(self) -> float:
        return round(sum(self.lines.values()), 4)

    def add(self, key: str, usd: float) -> None:
        self.lines[key] += usd
        self.counts[key] += 1


def project(ledger: CostLedger, settings: Settings) -> Projection:
    out = Projection()
    qa_seen = False
    image_model = settings.fal_image_model
    for e in ledger.entries:
        group = e.step.split(":")[0]
        if group in ("cover", "page", "character", "companion") and "px" in e.units:
            has_refs = group != "page" or e.units.get("refs", 1) > 0
            endpoint = (
                f"{image_model.removesuffix('/edit')}/edit" if has_refs else image_model.removesuffix("/edit")
            )
            price = fal_cost(endpoint, resolution=_tier(e.units["px"])) or 0.0
            out.add("per-child sheets" if group in ("character", "companion") else "page images", price)
        elif group == "upscale" and "out_px" in e.units:
            side = e.units["out_px"]
            out.add(
                "upscale",
                fal_cost(settings.fal_upscale_model, out_px=(int(side), int(e.units.get("out_py", side))))
                or 0.0,
            )
        elif group == "qa":
            usage = TYPICAL["qa_cached" if qa_seen else "qa_first"]
            qa_seen = True
            out.add("page QA (Haiku)", anthropic_cost(settings.text_model_fast, usage))
        elif e.step == "story":
            out.add("story (Sonnet)", anthropic_cost(settings.text_model, TYPICAL["story"]))
        elif e.step == "story:safety":
            out.add("safety (Haiku)", anthropic_cost(settings.text_model_fast, TYPICAL["story:safety"]))
        elif group == "companion" or e.step.startswith("companion:"):
            out.add("per-child sheets", anthropic_cost(settings.text_model_fast, TYPICAL["check"]))
    return out
