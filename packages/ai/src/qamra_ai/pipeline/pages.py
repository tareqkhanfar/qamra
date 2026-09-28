"""Page illustrations (Addendum 3 §2–3).

- The cover is drawn first, in the book's locked outfit, and must pass QA. It then becomes every page's
  second reference (outfit, palette, painting style), so outfits stay identical at no extra image cost.
- Prompts follow the addendum's order: style → setting → scene → characters → outfit → composition →
  negatives (`prompts/page_image.v2.j2` + `prompts/style/qamra_style.md`).
- Every attempt gets a Haiku QA check. Only failing pages are redrawn, at most
  `page_max_regenerations` times, and then the best safe attempt is kept and flagged for a human.
- Pages run in parallel (`image_concurrency`); one failed page never stops the others. The budget guard
  stops new calls once the cap would be passed.
- Child-free plates come from the plate cache when possible.
- Final mode upscales the chosen image and fits it exactly to its print box.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog

from qamra_ai import prompts
from qamra_ai.cost import CostEntry
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError, QamraError
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.budget import BudgetExceeded
from qamra_ai.pipeline.layout import BeatPlan, BookPlan
from qamra_ai.pipeline.models import Child, CompanionSpec, Lang, PageQA
from qamra_ai.pipeline.plates import PlateStore, plate_key
from qamra_ai.pipeline.printimg import downscale, fit_exact
from qamra_ai.pipeline.qa import QAResult, evaluate
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import HouseStyle
from qamra_ai.pipeline.theme import ArtStyle, Theme, ThemeScene
from qamra_ai.text.base import CACHE, ImagePart, UserPart

log = structlog.get_logger("qamra.ai.pages")

Mode = Literal["preview", "final"]
PageStatus = Literal["ok", "needs_review", "failed", "skipped"]
# Why an attempt was drawn. The run's first draw (including the preview → final upgrade) has none; the
# dashboard's regeneration rate counts only "qa", the signal that a theme's scene prompts need work.
Why = Literal["qa", "error", "manual"]
QA_MAX_SIDE = 1024  # the page under inspection
# The book's reference images (character sheet, cover) are sent larger: sharper likeness judgments, and a
# cached prefix above Haiku 4.5's 4096-token minimum, so every page after the first reads it at 10%.
QA_REF_MAX_SIDE = 1536
_DRAW_ERRORS = (ContentBlocked, ProviderError, ProviderConfigError, InvalidOutput)

AREA_LABELS = {
    "top": "the top 30% of the image",
    "bottom": "the bottom 30% of the image",
    "left": "the left 38% of the image",
    "right": "the right 38% of the image",
    "top-right": "the top-right quarter",
    "top-left": "the top-left quarter",
    "bottom-right": "the bottom-right quarter",
    "bottom-left": "the bottom-left quarter",
    "none": "none (the text sits below the image)",
}


@dataclass
class BookContext:
    """Everything the page generator needs for one book. `outfits` and `seed` are locked per book."""

    child: Child
    lang: Lang
    theme: Theme
    style: ArtStyle
    house: HouseStyle
    plan: BookPlan
    character_sheet: bytes
    outfits: dict[str, str]  # outfit key → locked description
    seed: int
    mode: Mode = "final"
    companion: CompanionSpec | None = None
    companion_sheet: bytes | None = None
    cover: bytes | None = None  # set once the cover is drawn (or loaded when resuming)
    cover_qa: bytes | None = None  # sharper cover for QA (the print version when there is one)
    previews: dict[int, bytes] = field(default_factory=dict)  # approved preview images (final mode)
    plates: PlateStore | None = None
    on_page: Callable[["PageResult"], None] | None = None

    def scene(self, beat: int) -> ThemeScene:
        if beat == 0:
            if self.theme.cover is None:
                raise ValueError(f"theme {self.theme.slug} has no cover")
            return self.theme.cover
        return self.theme.pages[beat - 1]

    def resolution(self, rt: Runtime) -> Resolution:
        return rt.settings.preview_resolution if self.mode == "preview" else rt.settings.final_resolution

    def companion_in(self, beat: int) -> bool:
        plan = self.plan.beats[beat]
        return (
            self.companion is not None and not plan.no_child and self.scene(beat).companion_action is not None
        )


@dataclass
class Attempt:
    attempt: int
    seed: int | None = None
    why: Why | None = None
    error: str | None = None
    score: float | None = None
    passed: bool | None = None
    flags: tuple[str, ...] = ()
    qa: dict[str, Any] | None = None
    fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v not in (None, (), False)}


@dataclass
class PageResult:
    beat: int  # 0 = cover
    status: PageStatus
    image: GeneratedImage | None = None  # chosen attempt, as generated
    print_image: bytes | None = None  # final mode: upscaled + fitted JPEG at print size
    qa: PageQA | None = None
    verdict: QAResult | None = None
    attempts: list[Attempt] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    from_cache: bool = False

    @property
    def score(self) -> float | None:
        return self.verdict.score if self.verdict else None

    @property
    def redraws(self) -> int:
        """Automatic redraws after failing QA (not retries after provider errors)."""
        return sum(a.why == "qa" for a in self.attempts)


# ---- prompts --------------------------------------------------------------------------------


def page_request(rt: Runtime, ctx: BookContext, beat: int, attempt: int) -> ImageRequest:
    plan = ctx.plan.beats[beat]
    scene = ctx.scene(beat)
    kind = "cover" if beat == 0 else ("plate" if plan.no_child else "page")
    refs: list[RefImage] = []
    hero: dict[str, Any] | None = None
    if kind != "plate":
        refs.append(
            RefImage(
                ctx.character_sheet,
                sniff_mime(ctx.character_sheet),
                "THE HERO: character reference sheet of the child (likeness)",
            )
        )
        c = ctx.child
        hero = {"ref": 1, "gender": c.gender, "age": c.age, "hijab": c.hijab, "glasses": c.glasses}
    style_ref = None
    if kind == "page" and ctx.cover is not None:
        refs.append(
            RefImage(ctx.cover, sniff_mime(ctx.cover), "the book's front cover: style, palette, outfit")
        )
        style_ref = len(refs)
    preview_ref = None
    if ctx.mode == "final" and beat in ctx.previews:
        preview = ctx.previews[beat]
        refs.append(RefImage(preview, sniff_mime(preview), "approved preview of this page: keep composition"))
        preview_ref = len(refs)
    companion: dict[str, Any] | None = None
    if ctx.companion_in(beat) and ctx.companion is not None:
        ref_index = None
        if ctx.companion_sheet is not None:
            refs.append(
                RefImage(
                    ctx.companion_sheet, sniff_mime(ctx.companion_sheet), "THE COMPANION: character sheet"
                )
            )
            ref_index = len(refs)
        companion = {  # no names in image prompts: a written name invites lettering in the picture
            "ref": ref_index,
            "description": ctx.companion.description_en,
            "action": scene.companion_action,
        }
    h = ctx.house
    prompt = prompts.render(
        "page_image",
        version=3,
        kind=kind,
        layout=plan.layout,
        style=h.style,
        medium=ctx.style.guide,
        setting=ctx.theme.setting or h.setting,
        scene=scene.scene,
        location=ctx.theme.location_text(scene),
        time=scene.time,
        hero=hero,
        style_ref=style_ref,
        preview_ref=preview_ref,
        companion=companion,
        others=scene.others,
        outfit=None if kind == "plate" else ctx.outfits.get(scene.outfit),
        text_area=plan.text_area,
        composition=h.composition,
        safety=h.safety,
        negative=h.negative,
    )
    label = "cover" if beat == 0 else f"page:{beat}"
    return ImageRequest(
        step=f"{label}:a{attempt}",
        prompt=prompt,
        refs=refs,
        aspect=plan.aspect,
        resolution=ctx.resolution(rt),
        seed=(ctx.seed + beat * 101 + attempt * 7) % 2_147_483_647,
    )


def qa_request(ctx: BookContext, beat: int, image: bytes) -> tuple[str, list[UserPart]]:
    """System + user parts. The reference images come first and are cached for the whole book."""
    plan = ctx.plan.beats[beat]
    scene = ctx.scene(beat)
    expect_hero = not plan.no_child
    parts: list[UserPart] = []
    n = 0
    if expect_hero:
        n += 1
        parts += [
            f"Image {n}: the hero's character reference sheet (likeness reference).",
            ImagePart(downscale(ctx.character_sheet, QA_REF_MAX_SIDE), "image/jpeg"),
        ]
        if beat != 0 and ctx.cover is not None:
            n += 1
            parts += [
                f"Image {n}: this book's approved front cover (outfit and style reference).",
                ImagePart(downscale(ctx.cover_qa or ctx.cover, QA_REF_MAX_SIDE), "image/jpeg"),
            ]
        if ctx.companion is not None and ctx.companion_sheet is not None:
            n += 1
            parts += [
                f"Image {n}: the companion «{ctx.companion.name}» character sheet.",
                ImagePart(downscale(ctx.companion_sheet, QA_REF_MAX_SIDE), "image/jpeg"),
            ]
        parts.append(CACHE)
    companion = None
    if ctx.companion_in(beat) and ctx.companion is not None:
        companion = {
            "name": ctx.companion.name,
            "has_ref": ctx.companion_sheet is not None,
            "description": ctx.companion.description_en,
        }
    brief = prompts.render(
        "page_qa_brief",
        page_label="the front cover" if beat == 0 else f"page {plan.page_label}",
        scene=scene.scene,
        expect_hero=expect_hero,
        others=scene.others,
        companion=companion,
        outfit=None if plan.no_child else ctx.outfits.get(scene.outfit),
        text_area_label=AREA_LABELS.get(plan.text_area, plan.text_area),
    )
    parts += [ImagePart(downscale(image, QA_MAX_SIDE), "image/jpeg"), brief]
    h = ctx.house
    system = prompts.render(
        "page_qa",
        version=3,
        style=h.style,
        people=h.people,
        safety=h.safety,
        negative=h.negative,
        outfits=ctx.outfits,
    )
    return system, parts


# ---- one page ---------------------------------------------------------------------------------


def _rank(r: tuple[GeneratedImage, PageQA | None, QAResult | None]) -> tuple[float, ...]:
    _, qa, v = r
    if v is None:
        return (0, 1, 0, 0)  # QA unavailable: usable but ranked below any judged attempt
    hard = sum(f in v.flags for f in ("unsafe", "text_in_image", "anatomy", "hero_count", "face"))
    return (float(v.passed), float(qa.safe if qa else True), -hard, v.score)


async def _finish_print(rt: Runtime, ctx: BookContext, res: PageResult, plan: BeatPlan) -> None:
    if ctx.mode != "final" or res.image is None:
        return
    label = "cover" if res.beat == 0 else f"page:{res.beat}"
    try:
        up = await rt.upscale(res.image.data, step=f"upscale:{label}", target=plan.print_px)
        data = up.data
    except BudgetExceeded:
        raise
    except QamraError as e:
        log.warning("page.upscale_failed", beat=res.beat, error=str(e)[:200])
        res.flags.append("upscale_fallback")  # local Lanczos instead
        data = res.image.data
    res.print_image = await asyncio.to_thread(fit_exact, data, plan.print_px, dpi=ctx.plan.spec.dpi)


def _why(earlier: list[Attempt], manual: bool) -> Why | None:
    if manual:
        return "manual"
    if not earlier:
        return None
    return "error" if earlier[-1].passed is None else "qa"


async def generate_beat(
    rt: Runtime, ctx: BookContext, beat: int, *, first_attempt: int = 1, manual: bool = False
) -> PageResult:
    """Draw one page with QA and automatic redraws. `manual` = one admin/parent click: a single new attempt
    (numbered after the earlier ones, so it gets a new seed) and never served from the plate cache."""
    plan = ctx.plan.beats[beat]
    res = PageResult(beat=beat, status="failed")
    key = None
    if plan.no_child and ctx.plates is not None and not manual:
        key = plate_key(
            model=rt.image.model,
            theme=ctx.theme.slug,
            theme_version=ctx.theme.version,
            beat=beat,
            style=ctx.style.slug,
            house_version=ctx.house.version,
            resolution=ctx.resolution(rt),
            lang=ctx.lang,
        )
        cached = ctx.plates.get(key)
        if cached is not None:
            res.image = GeneratedImage(
                cached, sniff_mime(cached), CostEntry(f"plate:{beat}", "cache", "plate", {}, 0.0)
            )
            res.status, res.from_cache = "ok", True
            await _finish_print(rt, ctx, res, plan)
            return res

    best: tuple[GeneratedImage, PageQA | None, QAResult | None] | None = None
    max_attempts = 1 if manual else 1 + max(0, rt.settings.page_max_regenerations)
    for n in range(first_attempt, first_attempt + max_attempts):
        req = page_request(rt, ctx, beat, n)
        record = Attempt(attempt=n, seed=req.seed, why=_why(res.attempts, manual))
        res.attempts.append(record)
        try:
            image = await rt.draw(req)
        except BudgetExceeded:
            raise
        except _DRAW_ERRORS as e:
            record.error = f"{type(e).__name__}: {str(e)[:200]}"
            continue
        record.fallback = "fallback_from" in image.params
        label = "cover" if beat == 0 else str(beat)
        system, user = qa_request(ctx, beat, image.data)
        try:
            qa = await rt.ask(
                step=f"qa:{label}:a{n}",
                system=system,
                user=user,
                schema=PageQA,
                fast=True,
                kind="qa",
                max_tokens=1500,
            )
        except BudgetExceeded:
            raise
        except QamraError as e:
            log.warning("page.qa_unavailable", beat=beat, error=str(e)[:200])
            record.error = f"QA unavailable: {type(e).__name__}"
            candidate: tuple[GeneratedImage, PageQA | None, QAResult | None] = (image, None, None)
            if best is None or _rank(candidate) > _rank(best):
                best = candidate
            res.flags.append("qa_unavailable")
            break  # no automatic judgement: a human decides; don't spend on blind redraws
        verdict = evaluate(
            qa,
            expect_hero=not plan.no_child,
            expect_companion=ctx.companion_in(beat),
            threshold=rt.settings.qa_threshold,
        )
        record.score, record.passed, record.flags = verdict.score, verdict.passed, verdict.flags
        record.qa = qa.model_dump()
        candidate = (image, qa, verdict)
        if best is None or _rank(candidate) > _rank(best):
            best = candidate
        if verdict.passed:
            break

    if best is not None and best[1] is not None and not best[1].safe:
        best = None  # never keep an unsafe picture, even for review
        res.flags.append("unsafe")
    if best is None:
        res.status = "failed"
        if any(a.error for a in res.attempts):
            res.flags.append("draw_failed")
        return res
    res.image, res.qa, res.verdict = best
    passed = res.verdict is not None and res.verdict.passed
    res.status = "ok" if passed else "needs_review"
    if res.verdict is not None:
        res.flags.extend(f for f in res.verdict.flags if f not in res.flags)
    if any(a.fallback for a in res.attempts):
        res.flags.append("fallback_used")
    if key is not None and passed and ctx.plates is not None:
        ctx.plates.put(key, res.image.data)
    await _finish_print(rt, ctx, res, plan)
    return res


# ---- the book ---------------------------------------------------------------------------------


def beats_for(ctx: BookContext, preview_pages: int) -> list[int]:
    all_beats = sorted(ctx.plan.beats)
    if ctx.mode == "preview":
        return all_beats[: max(1, preview_pages)]  # cover + first story pages
    return all_beats


async def generate_pages(rt: Runtime, ctx: BookContext, beats: list[int]) -> dict[int, PageResult]:
    """Cover first (outfit anchor), then the other beats in parallel. Returns results by beat."""
    results: dict[int, PageResult] = {}

    def done(r: PageResult) -> PageResult:
        results[r.beat] = r
        if ctx.on_page is not None:
            ctx.on_page(r)
        return r

    if 0 in beats:
        try:
            cover = await generate_beat(rt, ctx, 0)
        except BudgetExceeded:
            cover = PageResult(0, "skipped", flags=["budget"])
        done(cover)
        if cover.image is not None:
            ctx.cover = cover.image.data
            ctx.cover_qa = cover.print_image or cover.image.data
    rest = [b for b in beats if b != 0]
    if ctx.cover is None and any(not ctx.plan.beats[b].no_child for b in rest):
        # no approved outfit anchor: stop here rather than paint a whole book with drifting outfits
        for b in rest:
            done(PageResult(b, "skipped", flags=["no_cover"]))
        return results

    sem = asyncio.Semaphore(max(1, rt.settings.image_concurrency))

    async def one(beat: int) -> None:
        async with sem:
            if rt.budget is not None and rt.budget.exceeded:
                done(PageResult(beat, "skipped", flags=["budget"]))
                return
            try:
                done(await generate_beat(rt, ctx, beat))
            except BudgetExceeded:
                done(PageResult(beat, "skipped", flags=["budget"]))

    await asyncio.gather(*(one(b) for b in rest))
    return results
