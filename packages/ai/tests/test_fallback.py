import pytest
from tests_helpers import png

from qamra_ai.cost import CostEntry
from qamra_ai.errors import ContentBlocked, ProviderConfigError, ProviderError
from qamra_ai.image.base import GeneratedImage, ImageRequest
from qamra_ai.image.fallback import FallbackImageProvider


class Scripted:
    """Raises the scripted errors in order, then succeeds."""

    def __init__(self, name: str, errors: list[Exception]) -> None:
        self.name, self.model = name, f"{name}-model"
        self.errors = list(errors)
        self.calls = 0

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return GeneratedImage(
            png(), "image/png", CostEntry(req.step, self.name, self.model, {}, 0.01), {"model": self.model}
        )


def _wrap(primary: Scripted, fallback: Scripted | None) -> tuple[FallbackImageProvider, list[float]]:
    sleeps: list[float] = []

    async def sleep(s: float) -> None:
        sleeps.append(s)

    return FallbackImageProvider(primary, fallback, switch_after=2, sleep=sleep), sleeps


REQ = ImageRequest(step="page:1:a1", prompt="p")


async def test_primary_success_never_touches_fallback() -> None:
    p, f = Scripted("p", []), Scripted("f", [])
    provider, sleeps = _wrap(p, f)
    img = await provider.generate(REQ)
    assert img.params["model"] == "p-model" and f.calls == 0 and provider.switches == 0 and not sleeps


async def test_switches_only_after_two_failures_and_records_it() -> None:
    p = Scripted("p", [ProviderError("503"), ProviderError("503")])
    f = Scripted("f", [])
    provider, sleeps = _wrap(p, f)
    img = await provider.generate(REQ)
    assert p.calls == 2 and f.calls == 1 and provider.switches == 1
    assert img.params["fallback_from"] == "p-model" and len(img.params["primary_errors"]) == 2  # type: ignore[arg-type]
    assert len(sleeps) == 1  # backoff between the two primary attempts


async def test_one_failure_then_success_stays_on_primary() -> None:
    p, f = Scripted("p", [ProviderError("timeout")]), Scripted("f", [])
    provider, _ = _wrap(p, f)
    img = await provider.generate(REQ)
    assert img.params["model"] == "p-model" and f.calls == 0


async def test_content_block_counts_as_failure_without_waiting() -> None:
    p = Scripted("p", [ContentBlocked("filter"), ContentBlocked("filter")])
    f = Scripted("f", [])
    provider, sleeps = _wrap(p, f)
    await provider.generate(REQ)
    assert f.calls == 1 and not sleeps


async def test_fallback_transient_error_is_retried() -> None:
    p = Scripted("p", [ProviderError("x"), ProviderError("x")])
    f = Scripted("f", [ProviderError("y")])
    provider, _ = _wrap(p, f)
    await provider.generate(REQ)
    assert f.calls == 2


async def test_without_fallback_errors_surface() -> None:
    provider, _ = _wrap(Scripted("p", [ProviderError("x"), ProviderError("x")]), None)
    with pytest.raises(ProviderError):
        await provider.generate(REQ)
    blocked = Scripted("p", [ContentBlocked("x")])
    provider, _ = _wrap(blocked, None)
    with pytest.raises(ContentBlocked):
        await provider.generate(REQ)
    assert blocked.calls == 1
    config = Scripted("p", [ProviderConfigError("no key")])
    provider, _ = _wrap(config, None)
    with pytest.raises(ProviderConfigError):
        await provider.generate(REQ)
    assert config.calls == 1
