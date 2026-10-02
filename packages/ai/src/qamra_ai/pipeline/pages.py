"""Page illustrations (Addendum 3 §2–3, Addendum 11 §2 and §4).

- Every book has a style bible (`pipeline.bible`): the hero's outfit per scene group, one head covering,
  the hair, the companion's design and the recurring side characters, locked once per book.
- The cover is drawn first, in the main scene group's outfit, and must pass QA. It is every page's style
  reference and the outfit reference of its own group. Each other group's first page is drawn next and,
  once accepted, becomes that group's outfit reference. A cover plate (a fixed background per theme and
  style), when one exists, is the cover's scene; the child's photo, while still stored, sharpens the cover's
  likeness (it goes only to the image model, never to QA).
- The companion's sheet (a content file, or drawn once from its locked description) and the side
  characters' sheets go with every page they appear on, within the provider's reference limit.
- Prompts follow the addendum's order: style → setting → scene → characters → outfit → composition →
  negatives (`prompts/page_image.v4.j2` + `prompts/style/qamra_style.md`).
- Every attempt gets a Haiku QA check (`page_qa.v5`). Only failing pages are redrawn, at most
  `page_max_regenerations` times, each told what the last review found; then the best safe attempt is
  kept and flagged for a human.
- Pages run in parallel (`image_concurrency`); one failed page never stops the others. The budget guard
  stops new calls once the cap would be passed.
- Child-free plates come from the plate cache when possible.
- Final mode upscales the chosen image and fits it exactly to its print box.
"""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import structlog

from qamra_ai import prompts
from qamra_ai.cost import CostEntry
from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError, QamraError
from qamra_ai.image.base import GeneratedImage, ImageRequest, RefImage, Resolution, sniff_mime
from qamra_ai.pipeline.bible import (
    StyleBible,
    build_bible,
    companion_sheet_key,
    plate_file,
    sheet_file,
)
from qamra_ai.pipeline.budget import BudgetExceeded
from qamra_ai.pipeline.companion import DEFAULT_SHEET_PROMPT, default_companion_request
from qamra_ai.pipeline.layout import BeatPlan, BookPlan
from qamra_ai.pipeline.models import Child, CompanionSpec, Lang, PageQA
from qamra_ai.pipeline.plates import PlateStore, plate_key
from qamra_ai.pipeline.printimg import downscale, fit_exact
from qamra_ai.pipeline.qa import QAResult, evaluate
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import HouseStyle, negatives
from qamra_ai.pipeline.theme import CONTENT_DIR, ArtStyle, Theme, ThemeScene
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
DEFAULT_MAX_REFS = 8  # providers that do not say how many reference images they take
PAGE_PROMPT = ("page_image", 4)
QA_PROMPT = ("page_qa", 5)
QA_BRIEF = ("page_qa_brief", 2)

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
    """Everything the page generator needs for one book. The style bible and `seed` are locked per book;
    `outfits` mirrors the bible (scene group → outfit with the head covering) for older callers."""

    child: Child
    lang: Lang
    theme: Theme
    style: ArtStyle
    house: HouseStyle
    plan: BookPlan
    character_sheet: bytes
    outfits: dict[str, str]  # scene group → locked outfit line (rebuilt from the bible)
    seed: int
    mode: Mode = "final"
    companion: CompanionSpec | None = None
    companion_sheet: bytes | None = None
    cover: bytes | None = None  # set once the cover is drawn (or loaded when resuming)
    cover_qa: bytes | None = None  # sharper cover for QA (the print version when there is one)
    previews: dict[int, bytes] = field(default_factory=dict)  # approved preview images (final mode)
    plates: PlateStore | None = None
    on_page: Callable[["PageResult"], None] | None = None
    bible: StyleBible | None = None  # built from theme + child + seed when not given (a new book)
    cast_sheets: dict[str, bytes] = field(default_factory=dict)  # cast id → sheet image (content files)
    cover_plate: bytes | None = None  # the cover's background plate (Addendum 11 §2.1)
    photo: bytes | None = None  # the child's photo while still stored: the cover only, never sent to QA
    group_refs: dict[str, tuple[int, bytes]] = field(default_factory=dict)  # group → (beat, accepted image)
    content_dir: Path = CONTENT_DIR

    def __post_init__(self) -> None:
        if self.bible is None:
            self.bible = build_bible(
                self.theme,
                self.child,
                self.seed,
                style=self.style.slug,
                companion=self.companion,
                content_dir=self.content_dir,
            )
        self.outfits = self.bible.outfit_lines()

    @property
    def locks(self) -> StyleBible:
        if self.bible is None:  # pragma: no cover (set in __post_init__)
            raise ValueError("book context without a style bible")
        return self.bible

    def group(self, beat: int) -> str:
        """The beat's scene group (its outfit key)."""
        return self.scene(beat).outfit

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


def ref_limit(provider: object) -> int:
    """How many reference images the provider takes (fal: per model family; the fallback: the smaller)."""
    return max(1, int(getattr(provider, "max_refs", DEFAULT_MAX_REFS)))


@dataclass(frozen=True)
class _Ref:
    role: str
    priority: int  # lower = kept first when the provider's limit is reached
    image: RefImage


def _select(cands: list[_Ref], limit: int) -> tuple[list[RefImage], dict[str, int]]:
    """Keep the `limit` most important references, in their listed order → (refs, role → Image number)."""
    keep = sorted(sorted(range(len(cands)), key=lambda i: cands[i].priority)[:limit])
    return [cands[i].image for i in keep], {cands[i].role: n for n, i in enumerate(keep, start=1)}


def _ref(role: str, priority: int, data: bytes, label: str) -> _Ref:
    return _Ref(role, priority, RefImage(data, sniff_mime(data), label))


def outfit_anchor(ctx: BookContext, beat: int) -> tuple[int, bytes] | None:
    """The accepted earlier page of this beat's scene group (never the beat itself), for groups other
    than the cover's."""
    group = ctx.group(beat)
    anchor = ctx.group_refs.get(group)
    if beat == 0 or group == ctx.locks.main_group or anchor is None or anchor[0] == beat:
        return None
    return anchor


def page_request(
    rt: Runtime, ctx: BookContext, beat: int, attempt: int, fixes: Sequence[str] = ()
) -> ImageRequest:
    plan = ctx.plan.beats[beat]
    scene = ctx.scene(beat)
    bible = ctx.locks
    kind = "cover" if beat == 0 else ("plate" if plan.no_child else "page")
    cover_group = ctx.group(beat) == bible.main_group
    cands: list[_Ref] = []
    if kind != "plate":
        cands.append(
            _ref(
                "hero", 0, ctx.character_sheet, "THE HERO: character reference sheet of the child (likeness)"
            )
        )
    if kind == "cover" and ctx.cover_plate is not None:
        cands.append(
            _ref(
                "plate", 1, ctx.cover_plate, "THE COVER BACKGROUND: the finished scene to paint the hero into"
            )
        )
    if kind == "cover" and ctx.photo is not None:
        cands.append(_ref("photo", 2, ctx.photo, "a photo of the hero: face likeness only"))
    if kind == "page" and ctx.cover is not None:
        what = "style, palette, outfit" if cover_group else "style, palette"
        cands.append(_ref("cover", 4 if cover_group else 6, ctx.cover, f"the book's front cover: {what}"))
    anchor = outfit_anchor(ctx, beat) if kind == "page" else None
    if anchor is not None:
        cands.append(_ref("outfit", 4, anchor[1], "an earlier page of this book in the same outfit: outfit"))
    if ctx.mode == "final" and beat in ctx.previews:
        cands.append(
            _ref("preview", 5, ctx.previews[beat], "approved preview of this page: keep composition")
        )
    with_companion = ctx.companion_in(beat) and ctx.companion is not None
    if with_companion and ctx.companion_sheet is not None:
        cands.append(_ref("companion", 3, ctx.companion_sheet, "THE COMPANION: character sheet"))
    cast_here = bible.cast_in(scene.others) if kind != "plate" else []
    for i, cid in enumerate(cast_here):
        if cid in ctx.cast_sheets:
            role = bible.cast[cid].role
            cands.append(_ref(f"cast:{cid}", 7 + i, ctx.cast_sheets[cid], f"{role.upper()}: character sheet"))
    provider = (rt.cover_image or rt.image) if kind == "cover" else rt.image
    refs, at = _select(cands, ref_limit(provider))

    hero: dict[str, Any] | None = None
    if kind != "plate":
        c = ctx.child
        hero = {
            "ref": at["hero"],
            "gender": c.gender,
            "age": c.age,
            "hijab": c.hijab,
            "glasses": c.glasses,
            "hair": bible.hair,
        }
    companion: dict[str, Any] | None = None
    if with_companion and ctx.companion is not None:
        companion = {  # no names in image prompts: a written name invites lettering in the picture
            "ref": at.get("companion"),
            "description": bible.companion or ctx.companion.description_en,
            "action": scene.companion_action,
        }
    cast = [
        {"role": bible.cast[c].role, "description": bible.cast[c].description, "ref": at.get(f"cast:{c}")}
        for c in cast_here
    ]
    h = ctx.house
    name, version = PAGE_PROMPT
    prompt = prompts.render(
        name,
        version=version,
        kind=kind,
        layout=plan.layout,
        style=h.style,
        medium=ctx.style.guide,
        setting=ctx.theme.setting or h.setting,
        scene=scene.scene,
        location=ctx.theme.location_text(scene),
        time=scene.time,
        hero=hero,
        photo_ref=at.get("photo"),
        plate_ref=at.get("plate"),
        style_ref=at.get("cover"),
        cover_outfit=cover_group,
        outfit_ref=at.get("outfit"),
        preview_ref=at.get("preview"),
        companion=companion,
        cast=cast,
        others=bible.render_others(scene.others),
        outfit=None if kind == "plate" else bible.outfits.get(scene.outfit),
        hijab=None if kind == "plate" else bible.hijab,
        text_area=plan.text_area,
        composition=h.composition,
        fixes=list(fixes),
        safety=h.safety,
        negative=negatives(h, ctx.style.negative),
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
    """System + user parts. The book's reference images come first and are cached for the whole book; a
    scene group's own outfit reference follows the cache marker."""
    plan = ctx.plan.beats[beat]
    scene = ctx.scene(beat)
    bible = ctx.locks
    expect_hero = not plan.no_child
    parts: list[UserPart] = []
    n = 0
    cover_ref = companion_ref = outfit_ref = None
    if expect_hero:
        n += 1
        parts += [
            f"Image {n}: the hero's character reference sheet (likeness reference).",
            ImagePart(downscale(ctx.character_sheet, QA_REF_MAX_SIDE), "image/jpeg"),
        ]
        if beat != 0 and ctx.cover is not None:
            n += 1
            cover_ref = n
            parts += [
                f"Image {n}: this book's approved front cover (style reference; the outfit of the cover's "
                "part of the story).",
                ImagePart(downscale(ctx.cover_qa or ctx.cover, QA_REF_MAX_SIDE), "image/jpeg"),
            ]
        if ctx.companion is not None and ctx.companion_sheet is not None:
            n += 1
            companion_ref = n
            parts += [
                f"Image {n}: the companion «{ctx.companion.name}» character sheet (its exact design).",
                ImagePart(downscale(ctx.companion_sheet, QA_REF_MAX_SIDE), "image/jpeg"),
            ]
        parts.append(CACHE)
        anchor = outfit_anchor(ctx, beat)
        if anchor is not None:
            n += 1
            outfit_ref = n
            parts += [
                f"Image {n}: an accepted earlier page of this book in the same outfit (outfit reference).",
                ImagePart(downscale(anchor[1], QA_MAX_SIDE), "image/jpeg"),
            ]
        elif beat != 0 and ctx.group(beat) == bible.main_group:
            outfit_ref = cover_ref
    companion = None
    if ctx.companion_in(beat) and ctx.companion is not None:
        companion = {
            "name": ctx.companion.name,
            "ref": companion_ref,
            "description": bible.companion or ctx.companion.description_en,
        }
    cast_here = bible.cast_in(scene.others) if expect_hero else []
    name, version = QA_BRIEF
    brief = prompts.render(
        name,
        version=version,
        page_label="the front cover" if beat == 0 else f"page {plan.page_label}",
        scene=scene.scene,
        expect_hero=expect_hero,
        others=bible.render_others(scene.others),
        cast=[{"role": bible.cast[c].role, "description": bible.cast[c].description} for c in cast_here],
        companion=companion,
        outfit=bible.outfits.get(scene.outfit) if expect_hero else None,
        outfit_ref=outfit_ref,
        hijab=bible.hijab,
        text_area_label=AREA_LABELS.get(plan.text_area, plan.text_area),
    )
    parts += [ImagePart(downscale(image, QA_MAX_SIDE), "image/jpeg"), brief]
    h = ctx.house
    name, version = QA_PROMPT
    system = prompts.render(
        name,
        version=version,
        style=h.style,
        medium=ctx.style.guide,
        people=h.people,
        safety=h.safety,
        negative=negatives(h, ctx.style.negative),
        outfits=bible.outfits,
        hijab=bible.hijab,
        companion=bible.companion if ctx.companion is not None else None,
        cast=bible.cast,
    )
    return system, parts


# ---- reference sheets -------------------------------------------------------------------------


async def theme_companion_sheet(rt: Runtime, ctx: BookContext) -> bytes | None:
    """A theme companion's sheet: the theme's file, the shared file, or drawn once from its locked
    description and kept in the plate store (shared by every book with the same design and style)."""
    d = ctx.theme.default_companion
    path = sheet_file(
        ctx.theme.slug,
        "companion",
        ctx.style.slug,
        shared_id=d.id if d is not None else None,
        content_dir=ctx.content_dir,
    )
    if path is not None:
        return path.read_bytes()
    description = ctx.locks.companion or (ctx.companion.description_en if ctx.companion else "")
    if not description:
        return None
    name, version = DEFAULT_SHEET_PROMPT
    key = companion_sheet_key(
        model=rt.image.model,
        style=ctx.style.slug,
        house_version=ctx.house.version,
        description=description,
        prompt=f"{name}.v{version}",
    )
    cached = ctx.plates.get(key) if ctx.plates is not None else None
    if cached is not None:
        return cached
    try:
        image = await rt.draw(default_companion_request(description, ctx.style))
    except (BudgetExceeded, *_DRAW_ERRORS) as e:
        log.warning("companion.sheet_failed", theme=ctx.theme.slug, error=type(e).__name__)
        return None  # the pages fall back to the locked description
    if ctx.plates is not None:
        ctx.plates.put(key, image.data)
    return image.data


async def prepare_book(rt: Runtime, ctx: BookContext, beats: Sequence[int] | None = None) -> None:
    """Load the book's fixed references before drawing: the side characters' sheets and the cover plate
    (content files), and the theme companion's sheet when any of `beats` shows it. Safe to call again."""
    bible = ctx.locks
    for cid in bible.cast:
        if cid not in ctx.cast_sheets:
            path = sheet_file(ctx.theme.slug, cid, ctx.style.slug, content_dir=ctx.content_dir)
            if path is not None:
                ctx.cast_sheets[cid] = path.read_bytes()
    if ctx.cover_plate is None and bible.cover_plate:
        plate = plate_file(ctx.theme.slug, bible.cover_plate, ctx.content_dir)
        if plate is not None:
            ctx.cover_plate = plate.read_bytes()
    wanted = [b for b in (ctx.plan.beats if beats is None else beats) if b in ctx.plan.beats]
    if (
        ctx.companion is not None
        and not ctx.companion.from_drawing
        and ctx.companion_sheet is None
        and any(ctx.companion_in(b) for b in wanted)
    ):
        ctx.companion_sheet = await theme_companion_sheet(rt, ctx)


# ---- one page ---------------------------------------------------------------------------------


def _rank(r: tuple[GeneratedImage, PageQA | None, QAResult | None]) -> tuple[float, ...]:
    _, qa, v = r
    if v is None:
        return (0, 1, 0, 0, 0)  # QA unavailable: usable but ranked below any judged attempt
    return (float(v.passed), float(qa.safe if qa else True), -v.hard, -v.lock_misses, v.score)


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
        why = _why(res.attempts, manual)
        fixes = res.attempts[-1].flags if why == "qa" else ()  # what the last review found
        req = page_request(rt, ctx, beat, n, fixes)
        record = Attempt(attempt=n, seed=req.seed, why=why)
        res.attempts.append(record)
        try:
            image = await rt.draw(req, cover=beat == 0)
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


def group_anchors(ctx: BookContext, beats: list[int]) -> list[int]:
    """The first hero page of every scene group other than the cover's that has no outfit reference yet:
    drawn before the rest so the group's other pages can match it."""
    main, seen, out = ctx.locks.main_group, set(ctx.group_refs), []
    for beat in sorted(b for b in beats if b != 0):
        group = ctx.group(beat)
        if ctx.plan.beats[beat].no_child or group == main or group in seen:
            continue
        seen.add(group)
        out.append(beat)
    return out


async def generate_pages(rt: Runtime, ctx: BookContext, beats: list[int]) -> dict[int, PageResult]:
    """Cover first (style + main outfit anchor), then each other scene group's first page (its outfit
    anchor), then the remaining beats in parallel. Returns results by beat."""
    results: dict[int, PageResult] = {}
    await prepare_book(rt, ctx, beats)

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
                res = done(await generate_beat(rt, ctx, beat))
            except BudgetExceeded:
                done(PageResult(beat, "skipped", flags=["budget"]))
                return
        group, hero = ctx.group(beat), not ctx.plan.beats[beat].no_child
        if hero and res.status == "ok" and res.image is not None and group != ctx.locks.main_group:
            ctx.group_refs.setdefault(group, (beat, res.image.data))

    anchors = group_anchors(ctx, rest)
    await asyncio.gather(*(one(b) for b in anchors))
    await asyncio.gather(*(one(b) for b in rest if b not in anchors))
    return results
