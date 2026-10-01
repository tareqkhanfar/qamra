"""The Classic pipeline with fake providers: klein requests, prices, QA scoring, the budget guard, texts."""

import io
from decimal import Decimal
from typing import Any

import pytest
from PIL import Image
from pydantic import SecretStr
from tests_helpers import png

from qamra_ai.config import Settings
from qamra_ai.cost import CostEntry, fal_cost
from qamra_ai.image import make_classic_image_provider
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage
from qamra_ai.image.fal import FalImageProvider
from qamra_ai.image.fallback import FallbackImageProvider
from qamra_ai.pipeline.budget import Budget
from qamra_ai.pipeline.classic import (
    ClassicContext,
    ClassicQA,
    PageJob,
    classic_budget_usd,
    classic_story,
    edit_pages,
    evaluate_classic,
    find_hero_box,
    make_portrait,
    parse_variant,
    variant_for,
)
from qamra_ai.pipeline.classic_geometry import HeroBox
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.models import Child
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_style, load_theme

KLEIN = "fal-ai/flux-2/klein/4b/edit"


class FakeFal:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def subscribe(self, application: str, arguments: dict[str, Any], *, headers: Any = None) -> Any:
        import base64

        self.calls.append({"endpoint": application, "args": arguments})
        size = arguments.get("image_size") or {"width": 64, "height": 64}
        buf = io.BytesIO()
        Image.new("RGB", (size["width"], size["height"]), "tan").save(buf, format="PNG")
        return {"images": [{"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}]}


class PricedEdits:
    """A klein stand-in on "fal": images of the requested size, priced like the real endpoint."""

    name, model = "fal", KLEIN

    def __init__(self) -> None:
        self.requests: list[ImageRequest] = []

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        self.requests.append(req)
        w, h = req.size or (512, 512)
        buf = io.BytesIO()
        Image.new("RGB", (w, h), "#c08060").save(buf, format="PNG")
        usd = fal_cost(KLEIN, out_px=(w, h), in_megapixels=1.0) or 0.0
        return GeneratedImage(buf.getvalue(), "image/png", CostEntry(req.step, "fal", KLEIN, {}, usd))


def _page_png(size: tuple[int, int] = (1200, 1200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "#28407a").save(buf, format="PNG")
    return buf.getvalue()


def _child() -> Child:
    return Child(name="ليان", gender="f", age=5, hijab=True)


def _rt(settings: Settings, image: Any, budget: Budget | None = None) -> Runtime:
    return Runtime(settings=settings, text=default_fake_text_provider(), image=image, budget=budget)


async def test_klein_request_shape_price_and_privacy() -> None:
    fake = FakeFal()
    provider = FalImageProvider(None, KLEIN, client=fake)
    refs = [RefImage(png("red", (2000, 1500)), "image/png", f"ref {i}") for i in range(6)]
    img = await provider.generate(
        ImageRequest(step="hero:3:a1", prompt="P", refs=refs, size=(640, 896), seed=3)
    )
    call = fake.calls[0]
    assert call["endpoint"] == KLEIN
    args = call["args"]
    assert args["image_size"] == {"width": 640, "height": 896} and args["num_images"] == 1
    assert "safety_tolerance" not in args and args["enable_safety_checker"] is True
    assert args["sync_mode"] is True and len(args["image_urls"]) == 4  # klein takes up to 4 references
    for uri in args["image_urls"]:  # each reference at most 1 MP (klein bills input megapixels)
        import base64

        ref = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
        assert max(ref.size) <= 1024
    assert img.cost.model == KLEIN
    out_mp = 640 * 896 / (1024 * 1024)
    assert img.cost.usd == pytest.approx(0.01 * (out_mp + img.cost.units["input_megapixels"]), rel=0.02)


def test_klein_price_is_per_megapixel_of_input_and_output() -> None:
    assert fal_cost(KLEIN, out_px=(1024, 1024), in_megapixels=1.0) == pytest.approx(0.02)
    assert fal_cost(KLEIN, out_px=(768, 768), in_megapixels=0.5) == pytest.approx(0.01 * (0.5625 + 0.5))


def test_classic_provider_honours_the_admin_choice(settings: Settings) -> None:
    keyed = settings.model_copy(update={"image_provider": "fal", "fal_key": SecretStr("k")})
    on_fal = make_classic_image_provider(keyed)
    assert on_fal.primary.model == KLEIN and on_fal.fallback is None  # no silent move to a pricier model
    gpu = keyed.model_copy(update={"classic_image_provider": "self_hosted", "self_hosted_url": ""})
    fallback = make_classic_image_provider(gpu)  # no server set: fal draws instead
    assert fallback.primary.name == "fal" and fallback.primary.model == KLEIN
    assert make_classic_image_provider(settings).primary.name == "fake"  # offline stays offline


def test_self_hosted_budgets_for_its_fal_fallback(settings: Settings) -> None:
    class Gpu:
        name, model = "self_hosted", "klein-4b"

        async def generate(self, req: ImageRequest) -> GeneratedImage:  # pragma: no cover
            raise NotImplementedError

    image = FallbackImageProvider(Gpu(), FalImageProvider(None, KLEIN, client=FakeFal()))
    rt = _rt(settings, image)
    req = ImageRequest(
        step="hero:1:a1", prompt="P", refs=[RefImage(png(), "image/png", "x")], size=(768, 768)
    )
    assert 0 < rt.image_estimate(req) < 0.02  # klein's price, not the flat unknown-model guess
    assert _rt(settings, FallbackImageProvider(Gpu())).image_estimate(req) == 0.0


def test_the_budget_is_two_shekels_at_the_admin_rate() -> None:
    assert classic_budget_usd({"classic_budget_ils": "2.00", "usd_ils": "3.70"}) == Decimal("0.54")
    assert classic_budget_usd({"classic_budget_ils": "2.00", "usd_ils": "3.50"}) == Decimal("0.57")


def test_variants() -> None:
    assert variant_for("m", False) == "boy" and variant_for("m", True) == "boy"
    assert variant_for("f", True) == "girl_hijab" and variant_for("f", False) == "girl"
    assert parse_variant("girl_hijab").hijab and parse_variant("boy").gender == "m"
    with pytest.raises(ValueError, match="unknown Classic variant"):
        parse_variant("robot")


def _qa(**over: Any) -> ClassicQA:
    base: dict[str, Any] = {
        "likeness": 9,
        "same_scene": True,
        "seams": False,
        "hero_count": 1,
        "anatomy_ok": True,
        "text_in_image": False,
        "style_ok": True,
        "safe": True,
        "notes": "ok",
    }
    return ClassicQA(**(base | over))


def test_classic_qa_scoring() -> None:
    assert evaluate_classic(_qa(), likeness_min=7, threshold=0.75).passed
    weak = evaluate_classic(_qa(likeness=6), likeness_min=7, threshold=0.75)
    assert not weak.passed and "face" in weak.flags
    for bad in ({"seams": True}, {"text_in_image": True}, {"hero_count": 2}, {"safe": False}):
        verdict = evaluate_classic(_qa(**bad), likeness_min=7, threshold=0.75)
        assert not verdict.passed and verdict.flags


BOX = HeroBox(0.3, 0.2, 0.3, 0.6)


def _jobs(n: int, box: HeroBox | None = BOX) -> list[PageJob]:
    page = _page_png()
    return [PageJob(beat=b, template=page, box=box, scene="the hero waves") for b in range(n)]


def _ctx() -> ClassicContext:
    buf = io.BytesIO()
    Image.new("RGB", (768, 768), "#e8c0a0").save(buf, format="PNG")
    return ClassicContext(child=_child(), style=load_style("watercolor"), portrait=buf.getvalue(), seed=7)


async def test_edit_pages_crops_edits_pastes_and_checks(settings: Settings) -> None:
    image = PricedEdits()
    rt = _rt(settings, image)
    saved: list[int] = []
    results = await edit_pages(rt, _ctx(), _jobs(3), on_page=lambda r: saved.append(r.beat))
    assert sorted(saved) == [0, 1, 2]
    for res in results.values():
        assert res.status == "ok" and res.page is not None and res.qa is not None
        out = Image.open(io.BytesIO(res.page))
        assert out.size == (1200, 1200) and out.format == "JPEG"
        assert out.getpixel((20, 20)) == pytest.approx((40, 64, 122), abs=6)  # outside the crop: untouched
    req = next(r for r in image.requests if r.step == "hero:cover:a1")
    assert req.size is not None and {r.step for r in image.requests} == {
        "hero:cover:a1",
        "hero:1:a1",
        "hero:2:a1",
    }
    assert req.refs[0].label.startswith("the picture-book page") and "identity portrait" in req.refs[1].label
    w, h = req.size
    assert w * h <= 0.6 * 1024 * 1024 and w < h  # the hero's crop keeps its portrait shape
    assert all(c["schema"] == "ClassicQA" for c in rt.text.calls)  # type: ignore[attr-defined]


async def test_a_page_without_a_box_is_edited_whole_and_flagged(settings: Settings) -> None:
    results = await edit_pages(_rt(settings, PricedEdits()), _ctx(), _jobs(1, box=None))
    assert "whole_page_edit" in results[0].flags


async def test_failed_pages_are_redrawn_after_every_first_attempt(settings: Settings) -> None:
    rt = _rt(settings, PricedEdits())

    def qa(step: str, *_: Any) -> ClassicQA:  # the cover's first edit is not recognizable
        return _qa(likeness=6 if step == "qa:cover:a1" else 9)

    rt.text.responders["ClassicQA"] = qa  # type: ignore[attr-defined]
    results = await edit_pages(rt, _ctx(), _jobs(3))
    steps = [c["step"] for c in rt.text.calls]  # type: ignore[attr-defined]
    assert steps.index("qa:cover:a2") > max(steps.index("qa:1:a1"), steps.index("qa:2:a1"))
    assert results[0].status == "ok" and [a.why for a in results[0].attempts] == [None, "qa"]


async def test_the_budget_guard_stops_the_book_at_its_cap(settings: Settings) -> None:
    budget = Budget(cap_usd=0.05)
    rt = _rt(settings, PricedEdits(), budget)
    results = await edit_pages(rt, _ctx(), _jobs(8))
    drawn = [r for r in results.values() if r.page is not None]
    skipped = [r for r in results.values() if r.status == "skipped"]
    assert drawn and skipped and all("budget" in r.flags for r in skipped)
    assert budget.exceeded and rt.ledger.total_usd <= 0.05 + 1e-9


async def test_a_whole_book_fits_two_shekels(settings: Settings) -> None:
    """18 hero pages at klein's price stay under the 2₪ cap (text QA is priced separately, in the worker)."""
    cap = float(classic_budget_usd({"classic_budget_ils": "2.00", "usd_ils": "3.70"}))
    budget = Budget(cap_usd=cap)
    rt = _rt(settings, PricedEdits(), budget)
    results = await edit_pages(rt, _ctx(), _jobs(18))
    assert all(r.status == "ok" for r in results.values()) and not budget.exceeded
    assert rt.ledger.total_usd < cap / 2


async def test_hero_box_and_portrait_with_fakes(settings: Settings, face_png: bytes) -> None:
    rt = _rt(settings, PricedEdits())
    box = await find_hero_box(rt, _page_png(), face_png, _child(), "scene", step="qa:1:box")
    assert box == HeroBox(0.3, 0.3, 0.35, 0.6)
    portrait, qa = await make_portrait(rt, _child(), load_style("watercolor"), face_png, from_sheet=False)
    assert qa is not None and qa.likeness == 9 and Image.open(io.BytesIO(portrait.data)).size == (768, 768)


def test_classic_text_fills_the_name_and_the_gender_forms() -> None:
    theme = load_theme("graduation")
    girl = classic_story(theme, _child(), "ar", "قَمّور")
    boy = classic_story(theme, Child(name="يوسف", gender="m", age=5), "ar", "قَمّور")
    assert girl.title.startswith("يوم تخرّج ليان") and len(girl.pages) == len(theme.pages)
    assert "اسْتَيْقَظَتْ ليان" in girl.pages[0].text and "اسْتَيْقَظَ يوسف" in boy.pages[0].text
    assert all("{" not in p.text for p in girl.pages) and "قَمّور" in girl.pages[0].text
    assert len(girl.parents_questions) == 2 and "ليان" in girl.blurb and "نحبُّكِ" in girl.dedication
    english = classic_story(theme, Child(name="Layan", gender="f", age=5), "en", "Qamour")
    assert english.title == "Layan's Graduation Day" and "we love you" in english.dedication
