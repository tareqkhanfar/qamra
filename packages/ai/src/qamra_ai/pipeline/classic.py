"""«قمرة كلاسيك» (Addendum 4 §1A): ready-made template pages, with only the hero adapted to the child.

- Templates are drawn once per theme × art style × variant with the premium page pipeline, around a neutral
  placeholder hero (`placeholder_request`). The hero's box on each page is found once by the fast vision
  model (`find_hero_box`).
- Per child: one identity portrait in the book's style, a klein edit of the character sheet or photo.
- Per book: every page with the hero is cropped around the hero's head, edited with FLUX.2 [klein] 4B (the
  crop plus the portrait, with no style text: the page itself is the style), and only the head and hair are
  blended back, colour-matched, through a soft mask (`classic_blend`); the clothes and the rest of the page
  stay the template's. The fast model checks each page (likeness, seams, stray text). Every page gets its
  first edit before any page is redrawn, so a tight budget is spent evenly.
- Text comes from the theme's page templates: the name and gender forms are filled in, no AI call.
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

from qamra_ai import prompts
from qamra_ai.cost import fal_cost, fal_unknown_price
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError, QamraError
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, sniff_mime
from qamra_ai.pipeline.budget import BudgetExceeded
from qamra_ai.pipeline.classic_blend import HEAD_FEATHER, blend_head
from qamra_ai.pipeline.classic_geometry import (
    FEATHER,
    HeroBox,
    Rect,
    edit_size,
    head_crop_rect,
    head_of,
    normalize_box,
    open_rgb,
    paste_back,
    to_jpeg,
    to_png,
)
from qamra_ai.pipeline.models import Child, Gender, Lang, SafetyVerdict, StoryOut, StoryPageOut
from qamra_ai.pipeline.pages import Attempt, PageStatus, Why
from qamra_ai.pipeline.printimg import downscale
from qamra_ai.pipeline.qa import LIKENESS_HARD_FAIL, QAResult
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_for, negatives
from qamra_ai.pipeline.theme import ArtStyle, Theme, render_template
from qamra_ai.pipeline.vowelize import DEDICATION_AR, VowelizedTexts, fill
from qamra_ai.text.base import ImagePart, UserPart

VARIANTS: tuple[str, ...] = ("girl", "girl_hijab", "boy")
PORTRAIT_PX = 768  # the identity portrait (≈0.56 MP: a klein edit of about $0.012)
PORTRAIT_REF_PX = 512  # what each hero edit gets of it (0.25 MP of billed input)
QA_PX = 640
CLASSIC_REDRAWS = 1  # automatic redraws per page, after every page had its first edit
EDIT_PROMPT = 2  # classic_edit.v2: no style guide (v1 carried it, and the edit restyled its crop)
PORTRAIT_PROMPT = 2  # classic_portrait.v2: a plain portrait, no style mood (v1 painted arches and lanterns)
PORTRAIT_PROMPT_ID = f"classic_portrait.v{PORTRAIT_PROMPT}"
HERO_BOX_PROMPT = 2  # hero_box.v2: on a labelled grid, with the head box and the page's outfit
BOX_PX = 1024
SEAM_SOFTER = 1.6  # a redraw after a seam: the mask's soft edge this much wider
GRID_STEPS = 10
LIKENESS_MIN = 7
_DRAW_ERRORS = (ContentBlocked, ProviderError, ProviderConfigError, InvalidOutput)
DEDICATION: dict[Lang, str] = {
    "ar": DEDICATION_AR,  # «إلى {name:gen}»: «إلى أبي بكر»
    "en": "To {name}, our little star: we love you to the moon.",
}


@dataclass(frozen=True)
class Variant:
    key: str
    gender: Gender
    hijab: bool


def parse_variant(key: str) -> Variant:
    """The template look. A string, so skin-tone and hair variants can be added later without a migration."""
    if key not in VARIANTS:
        raise ValueError(f"unknown Classic variant {key!r}; known: {', '.join(VARIANTS)}")
    return Variant(key, "m" if key == "boy" else "f", key == "girl_hijab")


def variant_for(gender: Gender, hijab: bool) -> str:
    if gender == "m":
        return "boy"
    return "girl_hijab" if hijab else "girl"


def placeholder_child(variant: Variant, theme: Theme) -> Child:
    age = max(2, min(12, (theme.age_range[0] + theme.age_range[1]) // 2))
    return Child(name="Hero", gender=variant.gender, age=age, hijab=variant.hijab)


# ---- structured answers from the fast vision model ---------------------------------------------------


class HeroBoxOut(BaseModel):
    found: bool
    clues: str = ""  # how the hero was told apart (written first, before the numbers)
    x: float
    y: float
    w: float
    h: float
    head_x: float | None = None
    head_y: float | None = None
    head_w: float | None = None
    head_h: float | None = None
    notes: str = ""


class ClassicQA(BaseModel):
    likeness: int  # 0–10 vs the identity portrait
    same_scene: bool
    seams: bool
    hero_count: int
    anatomy_ok: bool
    text_in_image: bool
    style_ok: bool
    safe: bool
    notes: str


WEIGHTS = {"likeness": 0.6, "same_scene": 0.15, "seams": 0.15, "style": 0.1}


def evaluate_classic(qa: ClassicQA, *, likeness_min: int, threshold: float) -> QAResult:
    """Pass: nothing hard-fails, the weighted score reaches the threshold and the child is recognizable."""
    likeness = max(0, min(10, qa.likeness))
    score = round(
        WEIGHTS["likeness"] * likeness / 10
        + WEIGHTS["same_scene"] * qa.same_scene
        + WEIGHTS["seams"] * (not qa.seams)
        + WEIGHTS["style"] * qa.style_ok,
        3,
    )
    hard = [
        flag
        for flag, bad in (
            ("unsafe", not qa.safe),
            ("text_in_image", qa.text_in_image),
            ("anatomy", not qa.anatomy_ok),
            ("hero_count", qa.hero_count != 1),
            ("seams", qa.seams),
            ("face", likeness < LIKENESS_HARD_FAIL),
        )
        if bad
    ]
    soft = [
        flag
        for flag, bad in (
            ("face", LIKENESS_HARD_FAIL <= likeness < likeness_min),
            ("scene", not qa.same_scene),
            ("style", not qa.style_ok),
        )
        if bad
    ]
    passed = not hard and score >= threshold and likeness >= likeness_min
    return QAResult(score=score, passed=passed, flags=tuple(dict.fromkeys(hard + soft)))


# ---- image requests ------------------------------------------------------------------------------------


def medium_line(style: ArtStyle) -> str:
    """The style's medium only: the guide's first clause («Premium watercolor and gouache children's
    picture-book painting on warm textured paper»), without its palette, light and framing mood."""
    first = style.guide.strip().split("\n\n", 1)[0].replace("\n", " ")
    for stop in (":", ". "):
        if stop in first:
            first = first.split(stop, 1)[0]
    return first.strip().rstrip(".")


def placeholder_request(variant: Variant, style: ArtStyle, theme: Theme, seed: int) -> ImageRequest:
    """Text to image: the neutral placeholder hero's reference sheet for one template variant."""
    h = house_for(style)
    child = placeholder_child(variant, theme)
    prompt = prompts.render(
        "classic_placeholder",
        style=h.style,
        medium=style.guide,
        gender=child.gender,
        age=child.age,
        hijab=child.hijab,
        extras=[],
        people=h.people,
        negative=negatives(h, style.negative),
    )
    return ImageRequest(step="placeholder", prompt=prompt, aspect="3:2", resolution="1K", seed=seed)


def portrait_request(
    child: Child, style: ArtStyle, source: bytes, *, from_sheet: bool, attempt: int = 1
) -> ImageRequest:
    prompt = prompts.render(
        "classic_portrait",
        version=PORTRAIT_PROMPT,
        from_sheet=from_sheet,
        medium=medium_line(style),
        glasses=child.glasses,
        gender=child.gender,
        age=child.age,
        hijab=child.hijab,
    )
    label = "the child's character reference sheet" if from_sheet else "photo of the child"
    return ImageRequest(
        step=f"portrait:a{attempt}",
        prompt=prompt,
        refs=[RefImage(source, sniff_mime(source), label)],
        size=(PORTRAIT_PX, PORTRAIT_PX),
        seed=attempt * 4099,
    )


def synthetic_face_request(
    *, gender: Gender, age: int, hijab: bool, glasses: bool, skin: str, hair: str, top: str, seed: int
) -> ImageRequest:
    """Text to image: an invented child's photo for the cost proof (never a real person)."""
    prompt = prompts.render(
        "synthetic_child",
        gender=gender,
        age=age,
        hijab=hijab,
        glasses=glasses,
        skin=skin,
        hair=hair,
        top=top,
    )
    return ImageRequest(step="synthetic_face", prompt=prompt, aspect="1:1", resolution="1K", seed=seed)


def hero_edit_request(
    ctx: "ClassicContext", beat: int, crop: bytes, size: tuple[int, int], attempt: int
) -> ImageRequest:
    c = ctx.child
    prompt = prompts.render(
        "classic_edit", version=EDIT_PROMPT, hijab=c.hijab, glasses=c.glasses, gender=c.gender, age=c.age
    )
    label = "cover" if beat == 0 else str(beat)
    return ImageRequest(
        step=f"hero:{label}:a{attempt}",
        prompt=prompt,
        refs=[
            RefImage(crop, "image/png", "the picture-book page to edit (around the hero's head)"),
            RefImage(ctx.portrait_ref, "image/jpeg", f"the child who becomes the hero ({ctx.ref_label})"),
        ],
        size=size,
        seed=(ctx.seed + beat * 101 + attempt * 7) % 2_147_483_647,
    )


# ---- the fast vision model: hero box, portrait check ------------------------------------------------


def with_grid(page: bytes, px: int = BOX_PX, steps: int = GRID_STEPS) -> tuple[bytes, int, int]:
    """(the page as a JPEG of at most `px`, with a labelled 10 % grid, its width, its height).

    Vision models place boxes much more precisely when they can read positions off a ruler than when they
    guess fractions of a bare picture (the first boxes were coarse, round guesses, one on the wrong child)."""
    img = open_rgb(downscale(page, px))
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    size = max(11, min(w, h) // 48)
    font = ImageFont.load_default(size=size)
    for i in range(1, steps):
        x, y = round(w * i / steps), round(h * i / steps)
        draw.line((x, 0, x, h), fill=(255, 0, 160, 110), width=1)
        draw.line((0, y, w, y), fill=(255, 0, 160, 110), width=1)
        label = str(i * 100 // steps)
        for xy in ((x + 2, 2), (2, y + 2), (x + 2, h - size - 4), (w - size * 2 - 4, y + 2)):
            box = draw.textbbox(xy, label, font=font)
            draw.rectangle(box, fill=(255, 255, 255, 200))
            draw.text(xy, label, fill=(200, 0, 120, 255), font=font)
    out = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return to_jpeg(out, quality=88, dpi=None), w, h


async def find_hero_box(
    rt: Runtime,
    page: bytes,
    sheet: bytes,
    child: Child,
    scene: str,
    *,
    step: str,
    outfit: str = "",
) -> HeroBox | None:
    """The hero's figure and head boxes on a template page, asked once per page (docs/decisions.md).

    The image model returns no layout data, so the boxes are found on the finished page: the hero's
    reference sheet and the page's outfit tell the hero apart from classmates, and a labelled grid lets the
    model read the position instead of guessing it. Asked of the main model (a one-time cost per template
    page, ≈ $0.01): the fast model's boxes were coarse and once on the wrong child. The answer is normalized
    and clipped; an editor can still move the box in the template studio.
    """
    gridded, width, height = await asyncio.to_thread(with_grid, page)
    system = prompts.render(
        "hero_box",
        version=HERO_BOX_PROMPT,
        gender=child.gender,
        hijab=child.hijab,
        scene=scene,
        outfit=outfit,
    )
    user: list[UserPart] = [
        "Image 1: the hero's character reference sheet.",
        ImagePart(await asyncio.to_thread(downscale, sheet, 768), "image/jpeg"),
        "Image 2: the page, with a grid labelled in percent of its width (x) and height (y).",
        ImagePart(gridded, "image/jpeg"),
    ]
    answer = await rt.ask(
        step=step, system=system, user=user, schema=HeroBoxOut, kind="check", effort="low", max_tokens=1200
    )
    if not answer.found:
        return None
    figure = normalize_box(answer.x, answer.y, answer.w, answer.h, width=width, height=height)
    if figure is None:
        return None
    head = None
    if None not in (answer.head_x, answer.head_y, answer.head_w, answer.head_h):
        head = normalize_box(
            answer.head_x, answer.head_y, answer.head_w, answer.head_h, width=width, height=height
        )
    return figure.with_head(head)


class PortraitQA(BaseModel):
    likeness: int  # 0–10 vs the source (character sheet or photo)
    safe: bool
    text_in_image: bool
    notes: str


async def make_portrait(
    rt: Runtime, child: Child, style: ArtStyle, source: bytes, *, from_sheet: bool, attempts: int = 2
) -> tuple[GeneratedImage, PortraitQA | None]:
    """The child's identity portrait in the book's style, checked against its source; one redraw if weak."""
    src = await asyncio.to_thread(downscale, source, 1024)  # klein bills input megapixels
    best: tuple[GeneratedImage, PortraitQA | None] | None = None
    for n in range(1, attempts + 1):
        image = await rt.draw(portrait_request(child, style, src, from_sheet=from_sheet, attempt=n))
        try:
            qa = await rt.ask(
                step=f"qa:portrait:a{n}",
                system=prompts.render("classic_portrait_qa", from_sheet=from_sheet),
                user=[
                    "Image 1: the source.",
                    ImagePart(await asyncio.to_thread(downscale, src, 768), "image/jpeg"),
                    "Image 2: the portrait to inspect.",
                    ImagePart(await asyncio.to_thread(downscale, image.data, 768), "image/jpeg"),
                ],
                schema=PortraitQA,
                fast=True,
                kind="check",
                max_tokens=500,
            )
        except BudgetExceeded:
            raise
        except QamraError:
            return image, None  # no judgement available: keep it, the page QA still compares every page
        ok = qa.safe and not qa.text_in_image and qa.likeness >= LIKENESS_MIN
        if best is None or (ok, qa.likeness) > (
            bool(best[1] and best[1].safe and not best[1].text_in_image and best[1].likeness >= LIKENESS_MIN),
            best[1].likeness if best[1] else -1,
        ):
            best = (image, qa)
        if ok:
            break
    assert best is not None  # nosec B101 (the loop runs at least once)
    if best[1] is not None and not best[1].safe:
        raise ContentBlocked("the identity portrait failed the safety check")
    return best


# ---- the hero edit ------------------------------------------------------------------------------------


@dataclass
class ClassicContext:
    child: Child
    style: ArtStyle
    portrait: bytes  # the identity portrait (or, for a free cover, the character sheet or the photo)
    seed: int
    likeness_min: int = LIKENESS_MIN
    portrait_ref: bytes = b""  # the smaller copy each edit gets (set in __post_init__)
    ref_label: str = "the child's identity portrait"  # what the reference is, for the edit and the QA

    def __post_init__(self) -> None:
        if not self.portrait_ref:
            self.portrait_ref = downscale(self.portrait, PORTRAIT_REF_PX)


@dataclass
class PageJob:
    beat: int  # 0 = cover
    template: bytes  # the print-resolution template page (already mirrored for a left-to-right book)
    box: HeroBox | None  # None: the whole page is edited (flagged)
    scene: str
    first_attempt: int = 1


@dataclass
class HeroEdit:
    beat: int
    status: PageStatus = "failed"
    page: bytes | None = None  # the finished page at print resolution (JPEG, 300 dpi)
    qa: ClassicQA | None = None
    verdict: QAResult | None = None
    attempts: list[Attempt] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.verdict is not None and self.verdict.passed


Candidate = tuple[bytes, ClassicQA | None, QAResult | None]


def _rank(c: Candidate) -> tuple[float, ...]:
    _, qa, v = c
    if v is None:
        return (0, 1, 0, 0)
    hard = sum(f in v.flags for f in ("unsafe", "text_in_image", "anatomy", "hero_count", "seams"))
    return (float(v.passed), float(qa.safe if qa else True), -hard, v.score)


def _prepare(template: bytes, box: HeroBox | None) -> tuple[Rect, Rect | None, bytes, tuple[int, int]]:
    """(crop rectangle, the head's rectangle (None: no box, the whole page), the crop sized for the model
    as PNG, that size). The crop is the hero's head with room around it, not the whole figure: the clothes
    are never sent to be repainted, and the face gets more of the model's pixels."""
    page = open_rgb(template)
    if box is None:
        rect: Rect = (0, 0, page.width, page.height)
        head = None
    else:
        hbox = head_of(box)
        rect = head_crop_rect(hbox, page.width, page.height)
        head = hbox.rect(page.width, page.height)
    size = edit_size(rect[2] - rect[0], rect[3] - rect[1])
    crop = page.crop(rect).resize(size, Image.Resampling.LANCZOS)
    return rect, head, to_png(crop), size


def _grow(rect: Rect, width: int, height: int, frac: float = 0.06) -> Rect:
    dx, dy = round((rect[2] - rect[0]) * frac), round((rect[3] - rect[1]) * frac)
    return (max(0, rect[0] - dx), max(0, rect[1] - dy), min(width, rect[2] + dx), min(height, rect[3] + dy))


def _compose(
    template: bytes, edited: bytes, rect: Rect, head: Rect | None, soft: float
) -> tuple[bytes, bytes, bytes]:
    """(finished print page JPEG, the region before, the region after) — the last two small, for QA.

    With a head: only the head and hair are blended in (`classic_blend`). Without a box (flagged
    `whole_page_edit`) the whole edited page replaces the template, as before."""
    page = open_rgb(template)
    if head is None:
        out = paste_back(page, open_rgb(edited), rect, FEATHER * soft)
    else:
        out, _ = blend_head(page, open_rgb(edited), rect, head, HEAD_FEATHER * soft)
    view = _grow(rect, page.width, page.height)
    before = page.crop(view)
    after = out.crop(view)
    before.thumbnail((QA_PX, QA_PX), Image.Resampling.LANCZOS)
    after.thumbnail((QA_PX, QA_PX), Image.Resampling.LANCZOS)
    return to_jpeg(out), to_jpeg(before, quality=85, dpi=None), to_jpeg(after, quality=85, dpi=None)


def qa_parts(ctx: ClassicContext, before: bytes, after: bytes, brief: str) -> list[UserPart]:
    return [
        f"Image 1: {ctx.ref_label} (the likeness reference).",
        ImagePart(ctx.portrait_ref, "image/jpeg"),
        "Image 2: the page region before the edit (the placeholder hero).",
        ImagePart(before, "image/jpeg"),
        "Image 3: the same region after the edit.",
        ImagePart(after, "image/jpeg"),
        brief,
    ]


async def _attempt(
    rt: Runtime, ctx: ClassicContext, job: PageJob, res: HeroEdit, n: int, why: Why | None, soft: float
) -> Candidate | None:
    """One klein edit + blend + QA. Provider errors are recorded on the attempt; a budget stop propagates."""
    rect, head, crop, size = await asyncio.to_thread(_prepare, job.template, job.box)
    req = hero_edit_request(ctx, job.beat, crop, size, n)
    record = Attempt(attempt=n, seed=req.seed, why=why)
    res.attempts.append(record)
    try:
        image = await rt.draw(req)
    except BudgetExceeded:
        raise
    except _DRAW_ERRORS as e:
        record.error = f"{type(e).__name__}: {str(e)[:200]}"
        return None
    record.fallback = "fallback_from" in image.params
    page, before, after = await asyncio.to_thread(_compose, job.template, image.data, rect, head, soft)
    label = "the front cover" if job.beat == 0 else f"page {job.beat}"
    c = ctx.child
    brief = prompts.render(
        "classic_qa_brief",
        page_label=label,
        gender=c.gender,
        age=c.age,
        hijab=c.hijab,
        glasses=c.glasses,
        scene=job.scene,
    )
    try:
        qa = await rt.ask(
            step=f"qa:{'cover' if job.beat == 0 else job.beat}:a{n}",
            system=prompts.render("classic_qa"),
            user=qa_parts(ctx, before, after, brief),
            schema=ClassicQA,
            fast=True,
            kind="check",
            max_tokens=800,
        )
    except BudgetExceeded:
        raise
    except QamraError as e:
        record.error = f"QA unavailable: {type(e).__name__}"
        if "qa_unavailable" not in res.flags:
            res.flags.append("qa_unavailable")
        return page, None, None
    verdict = evaluate_classic(qa, likeness_min=ctx.likeness_min, threshold=rt.settings.qa_threshold)
    record.score, record.passed, record.flags = verdict.score, verdict.passed, verdict.flags
    record.qa = qa.model_dump()
    return page, qa, verdict


def _finish(res: HeroEdit, best: Candidate | None, job: PageJob) -> HeroEdit:
    if best is not None and best[1] is not None and not best[1].safe:
        best = None  # never keep an unsafe picture, even for review
        res.flags.append("unsafe")
    if job.box is None and "whole_page_edit" not in res.flags:
        res.flags.append("whole_page_edit")
    if best is None:
        budget_only = "budget" in res.flags and not res.attempts
        res.status = "skipped" if budget_only else "failed"
        if any(a.error for a in res.attempts):
            res.flags.append("draw_failed")
        return res
    res.page, res.qa, res.verdict = best
    res.status = "ok" if res.passed else "needs_review"
    if res.verdict is not None:
        res.flags.extend(f for f in res.verdict.flags if f not in res.flags)
    if any(a.fallback for a in res.attempts):
        res.flags.append("fallback_used")
    return res


async def edit_pages(
    rt: Runtime,
    ctx: ClassicContext,
    jobs: list[PageJob],
    *,
    redraws: int = CLASSIC_REDRAWS,
    manual: bool = False,
    on_page: Callable[[HeroEdit], None] | None = None,
) -> dict[int, HeroEdit]:
    """Edit every page's hero: all first attempts, then up to `redraws` redraws of the pages that failed QA.

    Pages run in parallel (`image_concurrency`). A page is final, and handed to `on_page`, as soon as it
    passes or has no redraw left. The budget guard stops new calls; pages it stopped are `skipped`.
    `manual` (one admin click): a single attempt per page, numbered after the earlier ones.
    """
    results = {j.beat: HeroEdit(j.beat) for j in jobs}
    best: dict[int, Candidate | None] = {j.beat: None for j in jobs}
    sem = asyncio.Semaphore(max(1, rt.settings.image_concurrency))

    async def run(job: PageJob, n: int, why: Why | None, soft: float) -> None:
        res = results[job.beat]
        async with sem:
            if rt.budget is not None and rt.budget.exceeded:
                res.flags.append("budget")
                return
            try:
                candidate = await _attempt(rt, ctx, job, res, n, why, soft)
            except BudgetExceeded:
                res.flags.append("budget")
                return
        current = best[job.beat]
        if candidate is not None and (current is None or _rank(candidate) > _rank(current)):
            best[job.beat] = candidate

    def done(job: PageJob) -> None:
        res = _finish(results[job.beat], best[job.beat], job)
        if on_page is not None:
            on_page(res)

    rounds = 0 if manual else max(0, redraws)
    first_why: Why | None = "manual" if manual else None
    cover = [j for j in jobs if j.beat == 0]
    if cover:  # the cover first: a book cannot be put together without it, whatever the budget allows
        await run(cover[0], cover[0].first_attempt, first_why, 1.0)
    await asyncio.gather(*(run(j, j.first_attempt, first_why, 1.0) for j in jobs if j.beat != 0))
    pending = []
    for job in jobs:
        cand = best[job.beat]
        verdict = cand[2] if cand is not None else None
        final = rounds == 0 or (verdict is not None and verdict.passed) or "budget" in results[job.beat].flags
        final = final or (cand is not None and verdict is None)  # QA unavailable: a human decides
        if final:
            done(job)
        else:
            pending.append(job)
    for _ in range(rounds):
        if not pending:
            break

        def softness_for(job: PageJob) -> float:  # a seam seen: a wider soft edge on the redraw
            cand = best[job.beat]
            seams = cand is not None and cand[2] is not None and "seams" in cand[2].flags
            return SEAM_SOFTER if seams else 1.0

        def why_for(job: PageJob) -> Why:
            return "error" if best[job.beat] is None else "qa"

        await asyncio.gather(
            *(
                run(j, j.first_attempt + len(results[j.beat].attempts), why_for(j), softness_for(j))
                for j in pending
            )
        )
        still = []
        for job in pending:
            cand = best[job.beat]
            if cand is not None and cand[2] is not None and cand[2].passed:
                done(job)
            else:
                still.append(job)
        pending = still
    for job in pending:
        done(job)
    return results


# ---- text ---------------------------------------------------------------------------------------------


def classic_story(
    theme: Theme, child: Child, lang: Lang, companion_name: str, texts: VowelizedTexts | None = None
) -> StoryOut:
    """The Classic book's words: the theme's page templates with the name and gender forms, no AI call.
    `texts`: the theme's Arabic texts vowelized once for this gender (pipeline.vowelize), used when given."""
    if texts is not None and lang == "ar":
        by_index = {p.index: p.text for p in texts.pages}
        fp = theme.for_parents
        asked = list(fp.questions_ar) if fp and len(fp.questions_ar) == len(texts.questions) else []
        return StoryOut(
            title=fill(texts.title, child.name, companion_name, theme.title_ar),
            dedication=fill(texts.dedication, child.name, companion_name, DEDICATION_AR),
            pages=[
                StoryPageOut(
                    index=p.index, text=fill(by_index[p.index], child.name, companion_name, p.text_ar)
                )
                if p.index in by_index
                else StoryPageOut(
                    index=p.index, text=theme.base_text(p, lang, child.gender, child.name, companion_name)
                )
                for p in theme.pages
            ],
            parents_lesson=fill(texts.lesson, child.name, companion_name, fp.lesson_ar if fp else ""),
            parents_questions=[
                fill(q, child.name, companion_name, asked[i] if asked else "")
                for i, q in enumerate(texts.questions)
            ],
            blurb=fill(texts.blurb, child.name, companion_name, theme.blurb_ar or ""),
        )

    def render(template: str) -> str:
        return render_template(template, child.gender, child.name, companion_name)

    fp = theme.for_parents
    return StoryOut(
        title=theme.title(lang, child.gender, child.name),
        dedication=render(DEDICATION[lang]),
        pages=[
            StoryPageOut(
                index=p.index, text=theme.base_text(p, lang, child.gender, child.name, companion_name)
            )
            for p in theme.pages
        ],
        parents_lesson=render((fp.lesson_ar if lang == "ar" else fp.lesson_en) if fp else ""),
        parents_questions=[
            render(q) for q in ((fp.questions_ar if lang == "ar" else fp.questions_en) if fp else [])
        ],
        blurb=render((theme.blurb_ar if lang == "ar" else theme.blurb_en) or ""),
    )


async def check_texts(
    rt: Runtime, story: StoryOut, child: Child, parent_message: str | None
) -> SafetyVerdict:
    """The fast model's safety review, for Classic books whose words the parent changed or added."""
    review: dict[str, object] = story.model_dump()
    if parent_message:
        review["parent_message"] = parent_message
    return await rt.ask(
        step="story:safety",
        system=prompts.render("story_safety", version=3, gender=child.gender),
        user=[json.dumps(review, ensure_ascii=False)],
        schema=SafetyVerdict,
        fast=True,
        kind="safety",
    )


# ---- money -------------------------------------------------------------------------------------------


def classic_budget_usd(values: dict[str, object]) -> Decimal:
    """The Classic cap (Addendum 4 §1A: 2₪ per book) in dollars, with the admin's exchange rate."""
    ils, rate = Decimal(str(values["classic_budget_ils"])), Decimal(str(values["usd_ils"]))
    return (ils / rate).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def edit_estimate_usd(model: str) -> float:
    """What one hero edit and its check may cost (a redraw's budget pre-check in the admin)."""
    price = fal_cost(model, out_px=(800, 800), in_megapixels=0.85)
    return round((price if price is not None else fal_unknown_price()) + 0.01, 4)


# ---- the free cover (Addendum 9) -----------------------------------------------------------------------

FREE_COVER_PX = 1024  # preview resolution: the cover is never print quality


async def free_cover_edit(
    rt: Runtime,
    *,
    child: Child,
    style: ArtStyle,
    cover: bytes,
    box: HeroBox | None,
    reference: bytes,
    ref_label: str,
    scene: str,
    seed: int,
) -> HeroEdit:
    """One small hero edit on a template cover: the Classic edit at preview size, with no redraw."""
    small = await asyncio.to_thread(downscale, cover, FREE_COVER_PX, 92)
    ctx = ClassicContext(child=child, style=style, portrait=reference, seed=seed, ref_label=ref_label)
    results = await edit_pages(rt, ctx, [PageJob(0, small, box, scene)], redraws=0)
    return results[0]
