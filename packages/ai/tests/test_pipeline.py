import asyncio

import pytest
from tests_helpers import png

from qamra_ai.cost import CostEntry
from qamra_ai.errors import ContentBlocked, InvalidOutput
from qamra_ai.image.base import GeneratedImage, ImageRequest
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.pipeline.book import BookRequest, generate_book
from qamra_ai.pipeline.companion import DrawingRejected, generate_companion_options
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.models import (
    CompanionSpec,
    DrawingReview,
    PageReview,
    SafetyVerdict,
    StoryOut,
    StoryPageOut,
)
from qamra_ai.pipeline.pages import Cast, generate_page, generate_pages, page_request
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import validate_story, write_story


def _sheet(tag: str) -> GeneratedImage:
    return GeneratedImage(png(), "image/png", CostEntry(tag, "fake", "m", {}, 0.0))


def _companion() -> CompanionSpec:
    return CompanionSpec(name="بوبو", description_en="purple blob with three eyes", from_drawing=True)


def test_page_prompt_includes_both_references(child, style, theme) -> None:  # type: ignore[no-untyped-def]
    cast = Cast(child, style, _sheet("c"), _companion(), _sheet("comp"))
    req = page_request(cast, theme.pages[0], 1, 12, 1)
    assert len(req.refs) == 2
    assert "HERO" in req.refs[0].label and "COMPANION" in req.refs[1].label
    assert "reference 1" in req.prompt and "reference 2" in req.prompt
    assert "بوبو" in req.prompt and theme.pages[0].companion_action in req.prompt
    assert "She is a girl" in req.prompt


def test_page_prompt_default_companion_has_no_second_ref(child, style, theme) -> None:  # type: ignore[no-untyped-def]
    comp = CompanionSpec(name="قمّور", description_en="tiny moon creature")
    cast = Cast(child, style, _sheet("c"), comp, None)
    req = page_request(cast, theme.pages[0], 1, 12, 1)
    assert len(req.refs) == 1
    assert "reference 2" not in req.prompt and "tiny moon creature" in req.prompt


def test_cover_prompt_reserves_title_space(child, style, theme) -> None:  # type: ignore[no-untyped-def]
    req = page_request(Cast(child, style, _sheet("c")), theme.cover, 0, 12, 1)
    assert req.step == "cover:a1" and "FRONT COVER" in req.prompt


async def test_story_is_adapted_and_validated(rt: Runtime, theme, child) -> None:  # type: ignore[no-untyped-def]
    story = await write_story(rt, theme, child, "ar", _companion())
    assert [p.index for p in story.pages] == list(range(1, 13))
    assert "سلمى" in story.title
    assert "شَعَرَتْ" in story.pages[3].text  # feminine variant chosen
    steps = [e.step for e in rt.ledger.entries]
    assert steps == ["story", "story:safety"]


def test_validate_story_rejects_missing_pages() -> None:
    story = StoryOut(title="t", dedication="d", pages=[StoryPageOut(index=1, text="a")])
    with pytest.raises(InvalidOutput):
        validate_story(story, 12)


async def test_unsafe_story_is_blocked(rt: Runtime, theme, child) -> None:  # type: ignore[no-untyped-def]
    rt.text.responders["SafetyVerdict"] = lambda *_: SafetyVerdict(safe=False, reasons=["p3: scary"])  # type: ignore[attr-defined]
    with pytest.raises(ContentBlocked):
        await write_story(rt, theme, child, "ar", None)


async def test_page_redrawn_once_then_flagged(rt: Runtime, child, style, theme) -> None:  # type: ignore[no-untyped-def]
    rt.text.responders["PageReview"] = lambda *_: PageReview(  # type: ignore[attr-defined]
        safe=True,
        hero_recognizable=False,
        companion_present=True,
        has_text_artifacts=False,
        notes="x",
    )
    result = await generate_page(rt, Cast(child, style, _sheet("c")), theme.pages[0], 1, 12)
    assert result.status == "needs_regeneration"
    assert result.attempts == 2 and result.image is not None
    assert result.first_attempt_recognizable is False


async def test_blocked_page_is_retried(rt: Runtime, child, style, theme) -> None:  # type: ignore[no-untyped-def]
    calls = 0
    inner = rt.image

    class Flaky:
        name, model = "flaky", "m"

        async def generate(self, req: ImageRequest) -> GeneratedImage:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ContentBlocked("provider filter")
            return await inner.generate(req)

    rt.image = Flaky()
    result = await generate_page(rt, Cast(child, style, _sheet("c")), theme.pages[0], 1, 12)
    assert result.status == "ok" and result.attempts == 2


async def test_pages_respect_concurrency(rt: Runtime, child, style, theme) -> None:  # type: ignore[no-untyped-def]
    in_flight = peak = 0
    inner = rt.image

    class Slow:
        name, model = "slow", "m"

        async def generate(self, req: ImageRequest) -> GeneratedImage:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return await inner.generate(req)

    rt.image = Slow()
    cover, pages = await generate_pages(rt, Cast(child, style, _sheet("c")), theme)
    assert cover.index == 0 and len(pages) == 12
    assert peak <= rt.settings.image_concurrency


async def test_companion_options_from_drawing(rt: Runtime, style) -> None:  # type: ignore[no-untyped-def]
    spec = CompanionSpec(name="بوبو", type_hint="creature")
    result = await generate_companion_options(rt, png("purple"), spec, style)
    assert len(result.options) == 2
    assert result.spec.from_drawing and "three eyes" in result.spec.description_en
    fake = rt.image
    assert isinstance(fake, FakeImageProvider)
    req = fake.requests[0]
    assert "three eyes" in req.prompt and req.refs[0].label == "the child's original drawing"


async def test_unsafe_drawing_rejected(rt: Runtime, style) -> None:  # type: ignore[no-untyped-def]
    rt.text.responders["DrawingReview"] = lambda *_: DrawingReview(  # type: ignore[attr-defined]
        safe=False, is_drawing=True, description_en="", key_features=[], reasons=["weapon"]
    )
    with pytest.raises(DrawingRejected) as e:
        await generate_companion_options(rt, png(), CompanionSpec(name="x"), style)
    assert "رسمة" in e.value.user_message_ar


async def test_book_with_drawing(rt: Runtime, child, style, theme, face_png) -> None:  # type: ignore[no-untyped-def]
    book = await generate_book(
        rt,
        BookRequest(
            child=child,
            lang="ar",
            theme=theme,
            style=style,
            photos=[face_png],
            cleaned_drawing=png("purple"),
            companion=CompanionSpec(name="بوبو"),
            companion_pick=2,
        ),
    )
    assert book.companion and book.companion.from_drawing
    assert book.companion_sheet is book.companion_options.options[1]  # type: ignore[union-attr]
    assert book.companion_fidelity is not None
    assert len(book.pages) == 12 and all(p.status == "ok" for p in book.pages)
    assert book.recognizable_ratio == 1.0
    # every page got both references
    fake = rt.image
    assert isinstance(fake, FakeImageProvider)
    page_reqs = [r for r in fake.requests if r.step.startswith(("page:", "cover"))]
    assert len(page_reqs) == 13 and all(len(r.refs) == 2 for r in page_reqs)


async def test_book_without_drawing_uses_theme_companion(rt: Runtime, child, style, theme, face_png) -> None:  # type: ignore[no-untyped-def]
    book = await generate_book(
        rt, BookRequest(child=child, lang="ar", theme=theme, style=style, photos=[face_png])
    )
    assert book.companion and book.companion.name == "قَمّور" and not book.companion.from_drawing
    assert book.companion_sheet is None and book.companion_fidelity is None


def test_fake_text_provider_is_default_for_fake() -> None:
    assert default_fake_text_provider().name == "fake"
