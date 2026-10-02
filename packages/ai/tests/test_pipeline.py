import asyncio
import io
import re

import pytest
from PIL import Image
from tests_helpers import png

from qamra_ai.cost import CostEntry
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderError
from qamra_ai.image.base import GeneratedImage, ImageRequest
from qamra_ai.image.fake import FakeImageProvider
from qamra_ai.image.fallback import FallbackImageProvider
from qamra_ai.pipeline.book import BookInputs, choose_outfits, run_book
from qamra_ai.pipeline.budget import Budget
from qamra_ai.pipeline.companion import DrawingRejected, generate_companion_options
from qamra_ai.pipeline.fakes import default_fake_text_provider, good_page_qa
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.models import Child, CompanionSpec, DrawingReview, PageQA, SafetyVerdict
from qamra_ai.pipeline.pages import BookContext, page_request
from qamra_ai.pipeline.plates import DirPlateStore
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import write_story
from qamra_ai.pipeline.style import house_style
from qamra_ai.text.base import CacheBreak, SystemPart


def _ctx(book_inputs: BookInputs, **kw: object) -> BookContext:
    inp = book_inputs
    return BookContext(
        child=inp.child,
        lang=inp.lang,
        theme=inp.theme,
        style=inp.style,
        house=house_style(),
        plan=plan_book(inp.theme, inp.lang, companion_page=False),
        character_sheet=inp.character_sheet,
        outfits=choose_outfits(inp.theme, inp.child, 1),
        seed=1,
        companion=inp.companion,
        **kw,  # type: ignore[arg-type]
    )


def _size(data: bytes | None) -> tuple[int, int]:
    assert data is not None
    return Image.open(io.BytesIO(data)).size


def _qa_sequence(rt: Runtime, answers: list[PageQA]) -> None:
    queue = list(answers)
    rt.text.responders["PageQA"] = lambda *_: queue.pop(0) if queue else good_page_qa()  # type: ignore[attr-defined]


# ---- prompts ----------------------------------------------------------------------------------


def test_page_prompt_order_and_references(rt: Runtime, book_inputs: BookInputs) -> None:
    ctx = _ctx(book_inputs, cover=png("gold"))
    req = page_request(rt, ctx, 3, 1)  # beat 3 = the family-breakfast spread
    order = ["STYLE", "SETTING", "SCENE", "CHARACTERS", "OUTFIT", "COMPOSITION", "SAFETY", "NEGATIVE"]
    positions = [req.prompt.index(f"\n{h}") if i else req.prompt.index(h) for i, h in enumerate(order)]
    assert positions == sorted(positions)
    assert [r.label.split(":")[0] for r in req.refs] == ["THE HERO", "the book's front cover"]
    assert req.aspect == "16:9" and req.resolution == "1K"
    assert "one illustration across two facing pages" in req.prompt and "TOP-RIGHT quarter" in req.prompt
    assert "limestone" in req.prompt and "cypress" in req.prompt  # setting cues + avoid-list
    assert "Location (it looks exactly like this" in req.prompt and "golden morning light" in req.prompt
    assert ctx.outfits["day"] in req.prompt and "No hijab or head covering" in req.prompt
    assert "قَمّور" not in req.prompt  # names never go into image prompts


def test_hijab_and_glasses_follow_the_parent(rt: Runtime, book_inputs: BookInputs) -> None:
    book_inputs.child = Child(name="ليان", gender="f", age=5, hijab=True, glasses=True)
    ctx = _ctx(book_inputs, cover=png("gold"))
    ctx.outfits = choose_outfits(ctx.theme, book_inputs.child, 1)
    prompt = page_request(rt, ctx, 1, 1).prompt
    assert "hijab" in ctx.outfits["sleep"] and "No hijab" not in prompt and "the same glasses" in prompt


def test_plate_prompt_has_no_hero(rt: Runtime, book_inputs: BookInputs) -> None:
    req = page_request(rt, _ctx(book_inputs, cover=png()), 5, 1)
    assert req.refs == [] and "No children and no main characters" in req.prompt
    assert "OUTFIT" not in req.prompt and "BOTTOM 30%" in req.prompt


def test_cover_prompt_reserves_title_space(rt: Runtime, book_inputs: BookInputs) -> None:
    req = page_request(rt, _ctx(book_inputs), 0, 1)
    assert req.step == "cover:a1" and "FRONT COVER" in req.prompt and "book title" in req.prompt
    assert len(req.refs) == 1  # no cover reference for the cover itself


# ---- generation -------------------------------------------------------------------------------


async def test_final_book_cover_first_and_print_sizes(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    run = await run_book(rt, book_inputs, mode="final")
    assert len(run.pages) == 18 and run.status_counts() == {"ok": 18} and run.flags == []
    # no fixed sheet for «قمّور» in watercolor: drawn once from its locked description, before the cover
    sheet, first = fake_image.requests[0], fake_image.requests[1]
    assert sheet.step == "companion:sheet" and "plump crescent" in sheet.prompt
    assert first.step == "cover:a1"
    later = [r for r in fake_image.requests[2:] if not r.step.startswith("page:5")]
    assert all(any(ref.label.startswith("the book's front cover") for ref in r.refs) for r in later)
    assert all(any(ref.label.startswith("THE COMPANION") for ref in r.refs) for r in [first, *later])
    assert _size(run.pages[0].print_image) == (2551, 2551)
    assert _size(run.pages[3].print_image) == (5031, 2551)  # spread
    assert _size(run.pages[2].print_image) == (2551, 1524)  # split
    assert _size(run.pages[1].print_image) == (2551, 2551)
    story = run.story
    assert story is not None and len(story.out.pages) == 17 and len(story.out.parents_questions) == 2
    assert story.out.blurb and "سلمى" in story.out.blurb


async def test_preview_draws_cover_and_first_pages_small(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    run = await run_book(rt, book_inputs, mode="preview")
    assert sorted(run.pages) == [0, 1, 2, 3]
    pages = [r for r in fake_image.requests if r.step != "companion:sheet"]  # the sheet is kept for finals
    assert {r.resolution for r in pages} == {"0.5K"}
    assert all(p.print_image is None for p in run.pages.values())


async def test_final_after_preview_reuses_the_approved_preview(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    book_inputs.previews = {1: png("pink")}
    book_inputs.cover = png("gold")
    await run_book(rt, book_inputs, mode="final", beats=[1])
    req = next(r for r in fake_image.requests if r.step.startswith("page:1"))
    assert any(ref.label.startswith("approved preview") for ref in req.refs)
    assert "parent-approved preview of THIS page" in req.prompt


async def test_failing_page_is_redrawn_twice_then_flagged(rt: Runtime, book_inputs: BookInputs) -> None:
    weak = good_page_qa().model_copy(update={"likeness": 6, "outfit_ok": False})
    _qa_sequence(rt, [good_page_qa(), weak, weak, weak])  # cover passes, page 1 never does
    run = await run_book(rt, book_inputs, mode="final", beats=[0, 1])
    page = run.pages[1]
    assert page.status == "needs_review" and len(page.attempts) == 3 and page.redraws == 2
    assert [a.why for a in page.attempts] == [None, "qa", "qa"]
    assert "face" in page.flags and page.image is not None and page.print_image is not None
    assert "pages_need_review" in run.flags


async def test_page_passing_on_second_try_is_ok(rt: Runtime, book_inputs: BookInputs) -> None:
    weak = good_page_qa().model_copy(update={"text_in_image": True})
    _qa_sequence(rt, [good_page_qa(), weak, good_page_qa()])
    run = await run_book(rt, book_inputs, mode="final", beats=[0, 1])
    assert run.pages[1].status == "ok" and run.pages[1].redraws == 1
    assert run.pages[1].attempts[0].flags == ("text_in_image",)


async def test_unsafe_pictures_are_never_kept(rt: Runtime, book_inputs: BookInputs) -> None:
    unsafe = good_page_qa().model_copy(update={"safe": False})
    _qa_sequence(rt, [good_page_qa(), unsafe, unsafe, unsafe])
    run = await run_book(rt, book_inputs, mode="final", beats=[0, 1])
    assert run.pages[1].status == "failed" and run.pages[1].image is None and "unsafe" in run.pages[1].flags


async def test_blocked_draw_counts_as_an_attempt(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    calls = 0

    class Flaky:
        name, model = "flaky", "m"

        async def generate(self, req: ImageRequest) -> GeneratedImage:
            nonlocal calls
            calls += 1
            if req.step.startswith("page:1:a1"):
                raise ContentBlocked("provider filter")
            return await fake_image.generate(req)

    rt.image = FallbackImageProvider(Flaky(), None, switch_after=1)
    run = await run_book(rt, book_inputs, mode="final", beats=[0, 1])
    assert run.pages[1].status == "ok" and len(run.pages[1].attempts) == 2
    assert "ContentBlocked" in (run.pages[1].attempts[0].error or "")
    assert run.pages[1].attempts[1].why == "error" and run.pages[1].redraws == 0  # not a QA regeneration


async def test_qa_outage_keeps_the_picture_for_a_human(rt: Runtime, book_inputs: BookInputs) -> None:
    def boom(*_: object) -> PageQA:
        raise ProviderError("anthropic down")

    rt.text.responders["PageQA"] = boom  # type: ignore[attr-defined]
    run = await run_book(rt, book_inputs, mode="final", beats=[0, 1])
    assert run.pages[1].status == "needs_review" and "qa_unavailable" in run.pages[1].flags
    assert len(run.pages[1].attempts) == 1  # no blind redraws


class Priced(FakeImageProvider):
    name = "priced"

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        img = await super().generate(req)
        return GeneratedImage(img.data, img.mime, CostEntry(req.step, "priced", "m", {}, 0.08), img.params)


async def test_budget_cap_stops_the_book_and_flags_it(rt: Runtime, book_inputs: BookInputs) -> None:
    rt.image = FallbackImageProvider(Priced(long_side=64), None)
    rt.budget = Budget(cap_usd=0.50)
    run = await run_book(rt, book_inputs, mode="final")
    assert "budget_exceeded" in run.flags
    skipped = [p for p in run.pages.values() if p.status == "skipped"]
    assert skipped and all("budget" in p.flags for p in skipped)
    assert rt.budget.spent_usd <= 0.50 and rt.ledger.total_usd == pytest.approx(rt.budget.spent_usd)


async def test_pages_respect_concurrency(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs
) -> None:
    in_flight = peak = 0

    class Slow:
        name, model = "slow", "m"

        async def generate(self, req: ImageRequest) -> GeneratedImage:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.005)
            in_flight -= 1
            return await fake_image.generate(req)

    rt.image = FallbackImageProvider(Slow(), None)
    await run_book(rt, book_inputs, mode="preview", beats=list(range(0, 10)))
    assert 1 < peak <= rt.settings.image_concurrency


async def test_plates_are_drawn_once_per_theme(
    rt: Runtime, fake_image: FakeImageProvider, book_inputs: BookInputs, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    book_inputs.plates = DirPlateStore(tmp_path)
    await run_book(rt, book_inputs, mode="preview", beats=[0, 5])
    assert sum(r.step.startswith("page:5") for r in fake_image.requests) == 1
    second = await run_book(rt, book_inputs, mode="preview", beats=[0, 5])
    assert sum(r.step.startswith("page:5") for r in fake_image.requests) == 1  # from the cache
    assert second.pages[5].from_cache and second.pages[5].status == "ok"


def test_plate_cache_is_per_model() -> None:
    """Placeholder art from offline runs must never be served to a book drawn by a real model."""
    from qamra_ai.pipeline.plates import plate_key

    common = {
        "theme": "first-day",
        "theme_version": 2,
        "beat": 5,
        "style": "watercolor",
        "house_version": "1",
        "resolution": "1K",
        "lang": "ar",
    }
    assert plate_key(model="qamra-sketch-1", **common) != plate_key(model="fal-ai/nano-banana-2", **common)  # type: ignore[arg-type]


# ---- story ------------------------------------------------------------------------------------


async def test_story_is_adapted_validated_and_cached(rt: Runtime, book_inputs: BookInputs) -> None:
    story = await write_story(
        rt, book_inputs.theme, book_inputs.child, "ar", book_inputs.companion, "نحبّك يا قمرنا"
    )
    assert [p.index for p in story.out.pages] == list(range(1, 18))
    assert "شَعَرَتْ" in story.out.pages[5].text  # feminine variant chosen
    call = rt.text.calls[0]  # type: ignore[attr-defined]
    system = call["system"]
    assert isinstance(system, list) and isinstance(system[0], SystemPart) and system[0].cache
    assert "سلمى" not in system[0].text  # the cached part has no child data
    safety = rt.text.calls[1]  # type: ignore[attr-defined]
    assert safety["model"] == rt.settings.text_model_fast and "نحبّك يا قمرنا" in safety["user"][0]
    assert call["model"] == "claude-sonnet-5" and rt.settings.text_model_fast == "claude-haiku-4-5-20251001"


async def test_parent_message_limit(rt: Runtime, book_inputs: BookInputs) -> None:
    with pytest.raises(InvalidOutput):
        await write_story(rt, book_inputs.theme, book_inputs.child, "ar", None, "أ" * 121)


async def test_unsafe_story_is_blocked(rt: Runtime, book_inputs: BookInputs) -> None:
    rt.text.responders["SafetyVerdict"] = lambda *_: SafetyVerdict(safe=False, reasons=["p3: scary"])  # type: ignore[attr-defined]
    with pytest.raises(ContentBlocked):
        await write_story(rt, book_inputs.theme, book_inputs.child, "ar", None)


async def test_qa_prefix_is_cached(rt: Runtime, book_inputs: BookInputs) -> None:
    await run_book(rt, book_inputs, mode="preview", beats=[0, 1])
    qa_calls = [c for c in rt.text.calls if c["schema"] == "PageQA"]  # type: ignore[attr-defined]
    page_call = qa_calls[1]["user"]
    marker = next(i for i, p in enumerate(page_call) if isinstance(p, CacheBreak))
    # sheet + cover + companion sheet before the marker
    assert sum(not isinstance(p, str) for p in page_call[:marker]) == 3
    assert "Brief:" in page_call[-1]


# ---- companion --------------------------------------------------------------------------------


async def test_companion_options_from_drawing(rt: Runtime, fake_image: FakeImageProvider, style) -> None:  # type: ignore[no-untyped-def]
    spec = CompanionSpec(name="بوبو", type_hint="creature")
    result = await generate_companion_options(rt, png("purple"), spec, style)
    assert len(result.options) == 2
    assert result.spec.from_drawing and "three eyes" in result.spec.description_en
    req = fake_image.requests[0]
    assert "three eyes" in req.prompt and req.refs[0].label == "the child's original drawing"
    assert "No text of any kind" in req.prompt  # house negatives on every image prompt


def test_image_prompts_carry_no_page_numbers(rt: Runtime, book_inputs: BookInputs) -> None:
    """ "page 3" in a prompt made the model paint a folio into the picture's corner."""
    ctx = _ctx(book_inputs, cover=png())
    for beat in ctx.plan.beats:
        prompt = page_request(rt, ctx, beat, 1).prompt
        assert not re.search(r"\bpages? \d", prompt), beat
    assert "No page numbers" in prompt


async def test_unsafe_drawing_rejected(rt: Runtime, style) -> None:  # type: ignore[no-untyped-def]
    rt.text.responders["DrawingReview"] = lambda *_: DrawingReview(  # type: ignore[attr-defined]
        safe=False, is_drawing=True, description_en="", key_features=[], reasons=["weapon"]
    )
    with pytest.raises(DrawingRejected) as e:
        await generate_companion_options(rt, png(), CompanionSpec(name="x"), style)
    assert "رسمة" in e.value.user_message_ar


def test_fake_text_provider_is_default_for_fake() -> None:
    assert default_fake_text_provider().name == "fake"
