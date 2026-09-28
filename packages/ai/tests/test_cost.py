import pytest

from qamra_ai.cost import CostEntry, CostLedger, anthropic_cost, fal_cost, gemini_cost, openai_image_cost


def test_anthropic_cost() -> None:
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000}
    assert anthropic_cost("claude-sonnet-5", usage) == pytest.approx(2.0 + 1.0)
    assert anthropic_cost("unknown-model", usage) == 0.0


def test_anthropic_cost_accepts_dated_ids_and_cache_usage() -> None:
    usage = {
        "input_tokens": 1000,
        "cache_read_input_tokens": 4000,
        "cache_creation_input_tokens": 0,
        "output_tokens": 300,
    }
    expected = (1000 * 1.0 + 4000 * 0.10 + 300 * 5.0) / 1e6
    assert anthropic_cost("claude-haiku-4-5-20251001", usage) == pytest.approx(expected)


def test_nano_banana_price_by_resolution() -> None:
    for endpoint in ("fal-ai/nano-banana-2", "fal-ai/nano-banana-2/edit"):
        assert fal_cost(endpoint, resolution="1K") == pytest.approx(0.08)
        assert fal_cost(endpoint, resolution="0.5K") == pytest.approx(0.06)
        assert fal_cost(endpoint, resolution="2K") == pytest.approx(0.12)
        assert fal_cost(endpoint, resolution="4K") == pytest.approx(0.16)


def test_flux_price_counts_megapixels_rounded_up() -> None:
    # fal page: "a 1024x1024 image will cost $0.03, and a 1920x1080 image will cost $0.045"
    assert fal_cost("fal-ai/flux-2-pro", out_px=(1024, 1024)) == pytest.approx(0.03)
    assert fal_cost("fal-ai/flux-2-pro", out_px=(1920, 1080)) == pytest.approx(0.045)
    # the edit endpoint also bills input megapixels
    assert fal_cost("fal-ai/flux-2-pro/edit", out_px=(1024, 1024), in_megapixels=2.4) == pytest.approx(
        0.03 + 3 * 0.015
    )


def test_upscaler_prices() -> None:
    assert fal_cost("fal-ai/seedvr/upscale/image", out_px=(2560, 2560)) == pytest.approx(0.00625, abs=1e-5)
    assert fal_cost("fal-ai/recraft/upscale/crisp", out_px=(4096, 4096)) == pytest.approx(0.004)


def test_unknown_fal_endpoint_is_none() -> None:
    assert fal_cost("someone/new-model") is None


def test_gemini_and_openai_costs() -> None:
    assert gemini_cost("gemini-3.1-flash-image", "2K", 1, 2) == pytest.approx(0.101 + 0.0022)
    assert openai_image_cost("gpt-image-2.5-sunburst", 1000, 2000, 5000) == pytest.approx(
        (1000 * 5 + 2000 * 8 + 5000 * 30) / 1e6
    )


def test_ledger_groups() -> None:
    ledger = CostLedger()
    ledger.add(CostEntry("page:1:a1", "fal", "g", {}, 0.1))
    ledger.add(CostEntry("page:2:a1", "fal", "g", {}, 0.1))
    ledger.add(CostEntry("story", "anthropic", "c", {}, 0.05))
    assert ledger.total_usd == pytest.approx(0.25)
    assert ledger.by_group() == {"page": 0.2, "story": 0.05}
    assert ledger.to_dict()["by_provider"] == {"anthropic/c": 0.05, "fal/g": 0.2}
