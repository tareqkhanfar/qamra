import pytest
from qamra_ai.cost import (
    CostEntry,
    CostLedger,
    anthropic_cost,
    fal_cost,
    gemini_cost,
    openai_image_cost,
)


def test_anthropic_cost() -> None:
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000}
    assert anthropic_cost("claude-opus-5", usage) == pytest.approx(5.0 + 2.5)
    assert anthropic_cost("unknown-model", usage) == 0.0


def test_gemini_cost() -> None:
    assert gemini_cost("gemini-3.1-flash-image", "2K", 1, 2) == pytest.approx(0.101 + 0.0022)


def test_openai_cost() -> None:
    assert openai_image_cost("gpt-image-2.5-sunburst", 1000, 2000, 5000) == pytest.approx(
        (1000 * 5 + 2000 * 8 + 5000 * 30) / 1e6
    )


def test_fal_cost() -> None:
    assert fal_cost("fal-ai/flux-2-pro/edit", 0.9) == pytest.approx(0.03)
    assert fal_cost("fal-ai/flux-2-pro/edit", 6.2) == pytest.approx(0.03 + 6 * 0.015)


def test_ledger_groups() -> None:
    ledger = CostLedger()
    ledger.add(CostEntry("page:1:a1", "gemini", "g", {}, 0.1))
    ledger.add(CostEntry("page:2:a1", "gemini", "g", {}, 0.1))
    ledger.add(CostEntry("story", "anthropic", "c", {}, 0.05))
    assert ledger.total_usd == pytest.approx(0.25)
    assert ledger.by_group() == {"page": 0.2, "story": 0.05}
    assert ledger.to_dict()["by_provider"] == {"anthropic/c": 0.05, "gemini/g": 0.2}
