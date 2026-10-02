"""«قمرة كلاسيك» jobs (Addendum 4 §1A): templates, identity portraits and Classic books.

- `generate_template`: draw a theme × style × variant once with the premium page pipeline around a neutral
  placeholder hero, find each page's hero box, log the one-time cost. Resumable; locked pages never change.
- `template_from_book`: turn an approved sample book of a synthetic child into a template (its print pages are
  copied and the hero boxes found), ready for an editor's review.
- `generate_classic_book`: the identity portrait (once per child and style), then every hero page of the
  template edited with klein and checked, the texts filled from the theme, and the PDFs. Preview = the cover
  and the first two hero pages, watermarked; final = the whole book, after the order is confirmed. A Classic
  book stops at its budget (2₪ by default: `classic_budget_ils` ÷ `usd_ils`) and goes to review.
All of a child's files stay under the child's storage prefix; template art lives under `classic/templates/`.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.cost import CostEntry
from qamra_ai.errors import QamraError
from qamra_ai.pipeline.assemble import plan_pages
from qamra_ai.pipeline.book import choose_outfits, default_companion, new_seed
from qamra_ai.pipeline.budget import Budget, BudgetExceeded
from qamra_ai.pipeline.classic import (
    ClassicContext,
    HeroEdit,
    PageJob,
    check_texts,
    classic_budget_usd,
    classic_story,
    edit_pages,
    find_hero_box,
    make_portrait,
    parse_variant,
    placeholder_child,
    placeholder_request,
    synthetic_face_request,
    variant_for,
)
from qamra_ai.pipeline.classic_geometry import HeroBox, mirror, open_rgb, preview_copy, text_box, to_png
from qamra_ai.pipeline.layout import BookPlan, PrintSpec, plan_book
from qamra_ai.pipeline.models import Child as AIChild
from qamra_ai.pipeline.models import Lang, StoryOut
from qamra_ai.pipeline.pages import BookContext, PageResult, generate_beat, generate_pages
from qamra_ai.pipeline.printimg import downscale
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import Theme, load_style
from qamra_ai.pipeline.vowelize import VowelizedTexts, source_hash, sources, vowelize
from qamra_core.db.classic import (
    ChildPortrait,
    ClassicTemplate,
    ClassicTemplatePage,
    TemplateJob,
    TemplateStatus,
)
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    GenerationCost,
    PageStatus,
    PhotoStatus,
    SafetyStatus,
)
from qamra_core.storage import ObjectNotFound, ObjectStorage
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_classic_runtime, make_runtime
from qamra_worker.jobs.books import (
    THUMB_PX,
    BookJob,
    CostSink,
    S3PlateStore,
    _beat_of,
    _set_flags,
    ai_child,
    book_lang,
    book_prefix,
    page_key,
    render_files,
    resolved_settings,
)
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.classic")

TEMPLATE_PREFIX = "classic/templates/"
SYNTHETIC_PREFIX = "classic/synthetic/"
PREVIEW_HERO_PAGES = 2  # the preview: the cover and the first two pages with the hero
PREVIEW_PX = 720
STUDIO_PX = 1024
LIVE_ORDER = (TemplateStatus.live, TemplateStatus.approved, TemplateStatus.in_review, TemplateStatus.draft)


def template_key(t: ClassicTemplate, beat: int, kind: str) -> str:
    ext = "png" if kind == "raw" else "jpg"
    return f"{TEMPLATE_PREFIX}{t.id}/{kind}/{beat:02d}.{ext}"


def label_of(beat: int) -> str:
    return "cover" if beat == 0 else str(beat)


@dataclass
class TemplateCostSink:
    """One-time template costs: generation_costs rows (no book, no child) plus the template's own totals."""

    db: Session
    template: ClassicTemplate

    def __call__(self, entry: CostEntry) -> None:
        usd = Decimal(str(round(entry.usd, 5)))
        self.db.add(
            GenerationCost(
                book_id=None,
                child_id=None,
                step=f"tpl:{entry.step}"[:64],
                provider=entry.provider[:32],
                model=entry.model[:100],
                units={**entry.units, "template": str(self.template.id)},
                usd=usd,
                estimated=entry.estimated,
            )
        )
        self.template.cost_usd = (self.template.cost_usd or Decimal("0")) + usd
        beat = _beat_of(entry.step)
        if beat is not None:
            page = self.db.scalar(
                select(ClassicTemplatePage).where(
                    ClassicTemplatePage.template_id == self.template.id, ClassicTemplatePage.beat == beat
                )
            )
            if page is not None:
                page.cost_usd = (page.cost_usd or Decimal("0")) + usd
        self.db.commit()


def template_pages(db: Session, template: ClassicTemplate) -> dict[int, ClassicTemplatePage]:
    rows = db.scalars(select(ClassicTemplatePage).where(ClassicTemplatePage.template_id == template.id)).all()
    return {r.beat: r for r in rows}


def template_lang(template: ClassicTemplate) -> Lang:
    return "en" if template.lang == "en" else "ar"


def template_theme(template: ClassicTemplate) -> Theme:
    return Theme.model_validate(template.generation["theme_def"])


def print_spec(settings: Any) -> PrintSpec:
    return PrintSpec.from_settings(settings)


def get_bytes(storage: ObjectStorage, key: str | None) -> bytes | None:
    if not key:
        return None
    try:
        return storage.get(key)
    except ObjectNotFound:
        return None


def find_template(db: Session, book: Book, child: AIChild, *, any_status: bool) -> ClassicTemplate | None:
    """The live template for the book's theme, style and the child's look. Sample books (the cost proof) may
    use a template that is still in review, so templates can be tried before they go live."""
    rows = db.scalars(
        select(ClassicTemplate).where(
            ClassicTemplate.theme_id == book.theme_id,
            ClassicTemplate.art_style == book.art_style,
            ClassicTemplate.variant == variant_for(child.gender, child.hijab),
        )
    ).all()
    allowed = LIVE_ORDER if any_status else (TemplateStatus.live,)
    ranked = sorted((r for r in rows if r.status in allowed), key=lambda r: LIVE_ORDER.index(r.status))
    return ranked[0] if ranked else None


# ---- templates ----------------------------------------------------------------------------------------


def _store_template_images(
    storage: ObjectStorage, template: ClassicTemplate, row: ClassicTemplatePage, raw: bytes, printed: bytes
) -> None:
    row.raw_key = template_key(template, row.beat, "raw")
    storage.put(row.raw_key, raw, "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg")
    row.image_key = template_key(template, row.beat, "print")
    storage.put(row.image_key, printed, "image/jpeg")
    row.preview_key = template_key(template, row.beat, "preview")
    storage.put(row.preview_key, downscale(printed, STUDIO_PX, 85), "image/jpeg")
    row.hero_box = None  # a new picture: its hero is found again


def _template_row(db: Session, template: ClassicTemplate, beat: int, plan: BookPlan) -> ClassicTemplatePage:
    row = template_pages(db, template).get(beat) or ClassicTemplatePage(template_id=template.id, beat=beat)
    bp = plan.beats[beat]
    row.layout = bp.layout
    row.has_hero = not bp.no_child
    row.text_box = text_box(bp.layout, bp.text_area)
    if row.id is None:
        db.add(row)
    return row


def save_template_page(
    db: Session, storage: ObjectStorage, template: ClassicTemplate, plan: BookPlan, res: PageResult
) -> None:
    row = _template_row(db, template, res.beat, plan)
    row.status = PageStatus(res.status)
    row.flags = list(dict.fromkeys(res.flags))
    row.attempts = [*(row.attempts or []), *[a.to_dict() for a in res.attempts]]
    if res.qa is not None:
        row.qa = res.qa.model_dump()
    if res.verdict is not None:
        row.qa_score = Decimal(str(res.verdict.score))
    if res.image is not None:
        _store_template_images(storage, template, row, res.image.data, res.print_image or res.image.data)
    db.flush()
    drawn = sum(bool(r.image_key) for b, r in template_pages(db, template).items() if b in plan.beats)
    template.generation = {**template.generation, "progress": {"done": drawn, "total": len(plan.beats)}}
    db.commit()


async def find_boxes(
    db: Session,
    storage: ObjectStorage,
    rt: Runtime,
    template: ClassicTemplate,
    hero: AIChild,
    sheet: bytes,
    beats: list[int] | None = None,
) -> None:
    """The hero's box on every drawn hero page that has none yet (on the print image the edit will crop)."""
    theme = template_theme(template)
    for beat, row in sorted(template_pages(db, template).items()):
        if beats is not None and beat not in beats:
            continue
        if not row.has_hero or row.hero_box is not None or not row.image_key:
            continue
        data = get_bytes(storage, row.image_key)
        if data is None:
            continue
        scene = theme.cover if beat == 0 else theme.pages[beat - 1]
        try:
            box = await find_hero_box(
                rt, data, sheet, hero, scene.scene if scene else "", step=f"qa:{label_of(beat)}:box"
            )
        except BudgetExceeded:
            _set_flags_on(template, ["budget_exceeded"])
            db.commit()
            return
        except QamraError as e:
            log.warning("classic.hero_box_failed", template=str(template.id), beat=beat, error=str(e)[:200])
            box = None
        row.hero_box = box.to_dict() if box else None
        row.flags = [f for f in (row.flags or []) if f != "no_hero_box"] + ([] if box else ["no_hero_box"])
        db.commit()


def _set_flags_on(template: ClassicTemplate, add: list[str], remove: tuple[str, ...] = ()) -> None:
    kept = [f for f in (template.flags or []) if f not in remove]
    template.flags = list(dict.fromkeys([*kept, *add]))


async def ensure_texts(db: Session, rt: Runtime, template: ClassicTemplate, *, refresh: bool = False) -> None:
    """The template's Arabic texts vowelized once for its gender (plan §2.13), cached with the template and
    keyed by a hash of the source words: a sibling template of the same theme and gender lends its copy, so a
    theme is vowelized once per gender. The one-time cost is logged as `tpl:vowelize:<gender>`."""
    theme = template_theme(template)
    gender = parse_variant(template.variant).gender
    digest = source_hash(sources(theme, gender))
    cached = template.generation.get("texts") or {}
    if not refresh and cached.get("hash") == digest:
        return
    siblings = db.scalars(
        select(ClassicTemplate).where(
            ClassicTemplate.theme_id == template.theme_id, ClassicTemplate.id != template.id
        )
    ).all()
    lent: dict[str, Any] | None = None
    for sibling in [] if refresh else siblings:
        theirs = sibling.generation.get("texts") or {}
        if theirs.get("hash") == digest and theirs.get("gender") == gender:
            lent = dict(theirs)  # the same words, already vowelized for this gender: no new call
            break
    if lent is None:
        result = await vowelize(rt, theme, gender, step=f"vowelize:{gender}")
        lent = {
            "hash": digest,
            "gender": gender,
            "texts": result.texts.model_dump(),
            "kept": result.kept,
            "model": rt.settings.text_model,
            "at": datetime.now(UTC).isoformat(),
        }
    template.generation = {**template.generation, "texts": lent}
    _set_flags_on(template, ["text_kept"] if lent.get("kept") else [], remove=("text_kept", "texts_pending"))
    db.commit()


async def texts_or_flag(db: Session, rt: Runtime, template: ClassicTemplate) -> None:
    try:
        await ensure_texts(db, rt, template)
    except (BudgetExceeded, QamraError) as e:
        log.warning("classic.vowelize_failed", template=str(template.id), error=str(e)[:200])
        _set_flags_on(template, ["texts_pending"])
        db.commit()


def finish_template(
    db: Session, template: ClassicTemplate, plan: BookPlan, *, budget_hit: bool
) -> dict[str, Any]:
    rows = template_pages(db, template)
    missing = [b for b in plan.beats if not (rows.get(b) and rows[b].image_key)]
    flags = []
    if missing:
        flags.append("pages_missing")
    if budget_hit:
        flags.append("budget_exceeded")
    if any(r.status in (PageStatus.needs_review, PageStatus.failed) for r in rows.values()):
        flags.append("pages_need_review")
    if any(r.has_hero and r.image_key and r.hero_box is None for r in rows.values()):
        flags.append("no_hero_box")
    remove = ("pages_missing", "budget_exceeded", "pages_need_review", "no_hero_box", "job_failed")
    _set_flags_on(template, flags, remove=remove)
    if not missing and template.status == TemplateStatus.draft:
        template.status = TemplateStatus.in_review
    template.job = TemplateJob.idle
    template.error = None
    db.commit()
    return {"status": template.status.value, "missing": missing, "cost_usd": float(template.cost_usd or 0)}


async def run_template_job(
    db: Session, storage: ObjectStorage, template: ClassicTemplate, beats: list[int] | None = None
) -> dict[str, Any]:
    """Draw the template's missing pages (or redraw `beats` once each), then find the hero boxes."""
    offline = template.generation.get("offline") or False
    settings = ai_settings(resolved_settings(db), get_settings(), offline=offline)
    rt = make_runtime(settings)
    rt.on_cost = TemplateCostSink(db, template)
    rt.budget = Budget(cap_usd=float(template.budget_usd or Decimal(str(settings.book_budget_usd))))
    theme = template_theme(template)
    variant = parse_variant(template.variant)
    hero = placeholder_child(variant, theme)
    style = load_style(template.art_style)
    lang = template_lang(template)
    plan = plan_book(theme, lang, companion_page=False, spec=print_spec(settings))
    gen = dict(template.generation)
    gen.setdefault("seed", new_seed())
    gen.setdefault("outfits", choose_outfits(theme, hero, int(gen["seed"])))
    gen["models"] = {
        "image": settings.image_provider
        if offline
        else f"{settings.image_provider}:{settings.fal_image_model}",
        "upscale": settings.fal_upscale_model,
        "text_fast": settings.text_model_fast,
        "style": house_style().prompt_id,
    }
    template.generation = gen
    db.commit()

    sheet = get_bytes(storage, gen.get("placeholder_key"))
    if sheet is None:
        image = await rt.draw(placeholder_request(variant, style, theme, int(gen["seed"])))
        key = f"{TEMPLATE_PREFIX}{template.id}/placeholder.png"
        storage.put(key, image.data, image.mime)
        template.generation = {**template.generation, "placeholder_key": key}
        db.commit()
        sheet = image.data

    rows = template_pages(db, template)
    cover = rows.get(0)
    ctx = BookContext(
        child=hero,
        lang=lang,
        theme=theme,
        style=style,
        house=house_style(),
        plan=plan,
        character_sheet=sheet,
        outfits=dict(gen["outfits"]),
        seed=int(gen["seed"]),
        mode="final",
        companion=default_companion(theme, lang),
        cover=get_bytes(storage, cover.raw_key) if cover else None,
        cover_qa=get_bytes(storage, cover.image_key) if cover else None,
        plates=S3PlateStore(storage),
        on_page=lambda r: save_template_page(db, storage, template, plan, r),
    )
    if beats is None:
        done = {
            b for b, r in rows.items() if r.image_key and r.status in (PageStatus.ok, PageStatus.needs_review)
        }
        wanted = [b for b in sorted(plan.beats) if b not in done and not (b in rows and rows[b].locked)]
        await generate_pages(rt, ctx, wanted)
    else:
        for beat in sorted(set(beats)):
            row = rows.get(beat)
            if beat not in plan.beats or (row is not None and row.locked):
                continue
            first = len(row.attempts or []) + 1 if row else 1
            try:
                res = await generate_beat(rt, ctx, beat, first_attempt=first, manual=True)
            except BudgetExceeded:
                break
            if res.image is None:
                if row is not None:  # keep the old picture when the new attempt failed or was unsafe
                    row.attempts = [*(row.attempts or []), *[a.to_dict() for a in res.attempts]]
                    db.commit()
                continue
            save_template_page(db, storage, template, plan, res)
            saved = template_pages(db, template)[beat]
            saved.regen_count = (saved.regen_count or 0) + 1
            db.commit()
            if beat == 0:
                ctx.cover, ctx.cover_qa = res.image.data, res.print_image or res.image.data
    await find_boxes(db, storage, rt, template, hero, sheet)
    await texts_or_flag(db, rt, template)
    return finish_template(db, template, plan, budget_hit=bool(rt.budget and rt.budget.exceeded))


async def run_template_from_book(
    db: Session, storage: ObjectStorage, template: ClassicTemplate, book: Book
) -> dict[str, Any]:
    """Copy an approved sample book's print pages into the template, find the hero boxes → in review."""
    settings = ai_settings(
        resolved_settings(db),
        get_settings(),
        offline=template.generation.get("offline") or book.generation.get("offline") or False,
    )
    rt = make_runtime(settings)
    rt.on_cost = TemplateCostSink(db, template)
    theme = template_theme(template)
    lang = template_lang(template)
    plan = plan_book(theme, lang, companion_page=False, spec=print_spec(settings))
    child = db.get(Child, book.child_id)
    character = db.get(Character, book.character_id) if book.character_id else None
    sheet = get_bytes(storage, character.sheet_image_key if character else None)
    if child is None or sheet is None:
        raise ValueError("the sample book's child or character sheet is missing")
    pages = {r.index: r for r in db.scalars(select(BookPage).where(BookPage.book_id == book.id)).all()}
    for beat in sorted(plan.beats):
        src = pages.get(beat)
        printed = get_bytes(storage, src.print_image_key if src else None)
        if src is None or printed is None:
            continue
        row = _template_row(db, template, beat, plan)
        if row.locked:
            continue
        _store_template_images(storage, template, row, get_bytes(storage, src.image_key) or printed, printed)
        row.status = src.status if src.status != PageStatus.pending else PageStatus.ok
        row.qa, row.qa_score = dict(src.qa or {}), src.qa_score
        row.flags = [f for f in (src.flags or []) if f not in ("parent_edited",)]
        row.attempts = [{"attempt": 0, "why": "sample_book", "book": str(book.id)}]
        db.commit()
    template.generation = {
        **template.generation,
        "seed": book.generation.get("seed"),
        "outfits": book.generation.get("outfits"),
        "source_cost_usd": float(book.cost_usd or 0),
        "progress": {
            "done": sum(bool(r.image_key) for r in template_pages(db, template).values()),
            "total": len(plan.beats),
        },
    }
    db.commit()
    await find_boxes(db, storage, rt, template, ai_child(child), sheet)
    await texts_or_flag(db, rt, template)
    return finish_template(db, template, plan, budget_hit=False)


# ---- the identity portrait -----------------------------------------------------------------------------


def portrait_source(
    db: Session, storage: ObjectStorage, book: Book, child: Child
) -> tuple[bytes, bool] | None:
    """(image, is a character sheet): the book's character sheet, else the child's newest accepted photo."""
    ready = (CharacterStatus.ready, CharacterStatus.approved)
    character = db.get(Character, book.character_id) if book.character_id else None
    if character is not None and character.status in ready and character.sheet_image_key:
        data = get_bytes(storage, character.sheet_image_key)
        if data is not None:
            return data, True
    photo = db.scalars(
        select(ChildPhoto)
        .where(
            ChildPhoto.child_id == child.id,
            ChildPhoto.status == PhotoStatus.accepted,
            ChildPhoto.storage_key.is_not(None),
        )
        .order_by(ChildPhoto.created_at.desc())
    ).first()
    data = get_bytes(storage, photo.storage_key if photo else None)
    return (data, False) if data is not None else None


async def ensure_portrait(
    db: Session, storage: ObjectStorage, rt: Runtime, book: Book, child: Child, ai: AIChild
) -> bytes:
    row = db.scalar(
        select(ChildPortrait).where(
            ChildPortrait.child_id == child.id, ChildPortrait.art_style == book.art_style
        )
    )
    stored = get_bytes(storage, row.image_key if row else None)
    if stored is not None:
        return stored
    source = portrait_source(db, storage, book, child)
    if source is None:
        raise LookupError("no character sheet or photo to paint the portrait from")
    image, qa = await make_portrait(rt, ai, load_style(book.art_style), source[0], from_sheet=source[1])
    key = f"children/{child.id}/portraits/{book.art_style}.png"
    storage.put(key, image.data, image.mime)
    if row is None:
        row = ChildPortrait(child_id=child.id, art_style=book.art_style, image_key=key, source="")
        db.add(row)
    row.image_key, row.source = key, "sheet" if source[1] else "photo"
    row.provider = str(image.params.get("provider", rt.image.name))[:32]
    row.model = str(image.params.get("model", rt.image.model))[:100]
    row.params = {
        "seed": image.params.get("seed"),
        "likeness": qa.likeness if qa else None,
        "notes": (qa.notes if qa else "unchecked")[:200],
    }
    # the photo has done its job: originals follow the same deletion rule as an approved character
    retention = int(resolved_settings(db).values["photo_retention_hours"])
    for photo in db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == child.id)).all():
        photo.delete_after = photo.delete_after or datetime.now(UTC) + timedelta(hours=retention)
    db.commit()
    return image.data


# ---- the Classic book ----------------------------------------------------------------------------------


@dataclass
class ClassicJob:
    db: Session
    storage: ObjectStorage
    book: Book
    child: Child
    ai: AIChild
    theme: Theme
    plan: BookPlan
    template: ClassicTemplate
    trows: dict[int, ClassicTemplatePage]
    rt: Runtime
    mirrored: bool

    def pages_by_beat(self) -> dict[int, BookPage]:
        rows = self.db.scalars(select(BookPage).where(BookPage.book_id == self.book.id)).all()
        return {r.index: r for r in rows}

    def book_job(self) -> BookJob:
        return BookJob(self.db, self.storage, self.book, self.child, self.theme, self.rt, self.plan)

    def scene(self, beat: int) -> str:
        scene = self.theme.cover if beat == 0 else self.theme.pages[beat - 1]
        return scene.scene if scene else ""


class TemplateMissing(Exception):
    """No template for this theme, style and look (yet): the book waits in the admin with a flag."""


def setup_classic(db: Session, storage: ObjectStorage, book: Book) -> ClassicJob:
    resolved = resolved_settings(db)
    offline = book.generation.get("offline") or False
    settings = ai_settings(resolved, get_settings(), offline=offline)
    rt = make_classic_runtime(settings)
    child = db.get(Child, book.child_id)
    if child is None:
        raise ValueError("child not found")
    ai = ai_child(child)
    pinned = book.generation.get("template_id")
    template = (
        db.get(ClassicTemplate, pinned) if pinned else find_template(db, book, ai, any_status=book.is_sample)
    )
    if template is None:
        raise TemplateMissing(
            f"no Classic template for {book.art_style} / {variant_for(ai.gender, ai.hijab)}"
        )
    theme = template_theme(template)
    plan = plan_book(theme, book_lang(book), companion_page=False, spec=print_spec(settings))
    gen = dict(book.generation)
    gen.update(line="classic", template_id=str(template.id), theme_def=template.generation["theme_def"])
    gen["plan"] = plan_pages(plan)
    gen.setdefault("seed", new_seed())
    gen.setdefault("outfits", dict(template.generation.get("outfits") or {}))
    gen["models"] = {
        "edit": "offline" if offline else f"{rt.image.name}:{rt.image.model}",
        "text_fast": settings.text_model_fast,
        "template": str(template.id),
        "variant": template.variant,
    }
    if book.budget_usd is None or not gen.get("budget_pinned"):  # older drafts carry the Magic cap
        book.budget_usd = classic_budget_usd(resolved.values)
        gen["budget_pinned"] = True
    book.generation = gen
    book.theme_version = template.theme_version
    db.commit()
    return ClassicJob(
        db,
        storage,
        book,
        child,
        ai,
        theme,
        plan,
        template,
        template_pages(db, template),
        rt,
        mirrored=book_lang(book) != template_lang(template),
    )


def ensure_text(job: ClassicJob) -> StoryOut:
    """The words, once: the theme's templates with the child's name and gender (the parent may edit later)."""
    book = job.book
    if book.story:
        return StoryOut.model_validate(book.story)
    lang = book_lang(book)
    companion = default_companion(job.theme, lang)
    texts = None
    if lang == "ar":
        cached = job.template.generation.get("texts") or {}
        fresh = cached.get("hash") == source_hash(sources(job.theme, job.ai.gender))
        if fresh and cached.get("gender") == job.ai.gender:
            texts = VowelizedTexts.model_validate(cached["texts"])
        else:
            _set_flags(book, ["text_not_vowelized"])  # the reviewer sees it; printing waits for the words
    story = classic_story(job.theme, job.ai, lang, companion.name if companion else "", texts)
    book.story = story.model_dump()
    book.title = story.title[:200]
    book.dedication = story.dedication
    rows = job.pages_by_beat()
    for p in story.pages:
        row = rows.get(p.index) or BookPage(book_id=book.id, index=p.index)
        row.text = row.original_text = p.text
        if row.id is None:
            job.db.add(row)
    if 0 not in rows:
        job.db.add(BookPage(book_id=book.id, index=0, text=story.title, original_text=story.title))
    job.db.commit()
    return story


def save_page(
    job: ClassicJob,
    beat: int,
    mode: str,
    *,
    page: bytes | None,
    status: str,
    flags: list[str],
    edit: HeroEdit | None = None,
) -> None:
    db, storage, book = job.db, job.storage, job.book
    row = job.pages_by_beat().get(beat) or BookPage(book_id=book.id, index=beat)
    row.layout = job.plan.beats[beat].layout
    row.status = PageStatus(status)
    row.flags = list(dict.fromkeys(flags))
    if edit is not None:
        row.attempts = [*(row.attempts or []), *[a.to_dict() for a in edit.attempts]]
        if edit.qa is not None:
            row.qa = edit.qa.model_dump()
            row.safety_status = SafetyStatus.passed if edit.qa.safe else SafetyStatus.failed
        if edit.verdict is not None:
            row.qa_score = Decimal(str(edit.verdict.score))
    if page is not None:
        row.print_image_key = page_key(book, beat, "print")
        storage.put(row.print_image_key, page, "image/jpeg")
        web = open_rgb(page)
        web.thumbnail((STUDIO_PX, STUDIO_PX))
        row.image_key = page_key(book, beat, "raw")
        storage.put(row.image_key, to_png(web), "image/png")
        storage.put(page_key(book, beat, "thumb"), downscale(page, THUMB_PX, 82), "image/jpeg")
        if mode == "preview":
            row.preview_image_key = f"{book_prefix(book)}preview/{beat:02d}.jpg"
            label = f"{get_settings().brand_name_en} · Preview"
            storage.put(
                row.preview_image_key, preview_copy(page, max_side=PREVIEW_PX, label=label), "image/jpeg"
            )
    if row.id is None:
        db.add(row)
    db.flush()
    progress = dict(book.generation.get("progress", {}))
    progress["done"] = sum(
        bool(r.print_image_key) or r.status in (PageStatus.failed, PageStatus.skipped)
        for b, r in job.pages_by_beat().items()
        if b in set(progress.get("beats", job.plan.beats))
    )
    book.generation = {**book.generation, "progress": progress}
    db.commit()


def add_preview(job: ClassicJob, row: BookPage) -> None:
    page = get_bytes(job.storage, row.print_image_key)
    if page is None:
        return
    row.preview_image_key = f"{book_prefix(job.book)}preview/{row.index:02d}.jpg"
    label = f"{get_settings().brand_name_en} · Preview"
    job.storage.put(row.preview_image_key, preview_copy(page, max_side=PREVIEW_PX, label=label), "image/jpeg")
    job.db.commit()


def wanted_beats(job: ClassicJob, mode: str) -> list[int]:
    beats = sorted(job.plan.beats)
    if mode != "preview":
        return beats
    heroes = [b for b in beats if b != 0 and job.trows.get(b) is not None and job.trows[b].has_hero]
    return [0, *heroes[:PREVIEW_HERO_PAGES]]


def _page_jobs(job: ClassicJob, beats: list[int], mode: str, *, manual: bool = False) -> list[PageJob]:
    """Hero pages → edit jobs. Pages without the hero are the template's own page, stored as they are."""
    rows = job.pages_by_beat()
    jobs: list[PageJob] = []
    for beat in beats:
        trow = job.trows.get(beat)
        data = get_bytes(job.storage, trow.image_key if trow else None)
        if trow is None or data is None:
            save_page(job, beat, mode, page=None, status="failed", flags=["template_page_missing"])
            continue
        if job.mirrored:
            data = mirror(data)
        if not trow.has_hero:
            if not manual:
                save_page(job, beat, mode, page=data, status="ok", flags=["template_page"])
            continue
        box = HeroBox.from_dict(trow.hero_box)
        if box is not None and job.mirrored:
            box = box.mirrored()
        row = rows.get(beat)
        first = len(row.attempts or []) + 1 if row is not None else 1
        jobs.append(PageJob(beat, data, box, job.scene(beat), first_attempt=first))
    return jobs


async def review_texts(job: ClassicJob, story: StoryOut) -> None:
    """Words the parent wrote or changed get the fast model's safety review before print (plan §2.13)."""
    book = job.book
    rows = job.pages_by_beat()
    if not (book.parent_message or any("parent_edited" in (r.flags or []) for r in rows.values())):
        return
    texts = {b: r.text for b, r in rows.items() if b > 0 and r.text}
    current = story.model_copy(
        update={"pages": [p.model_copy(update={"text": texts.get(p.index, p.text)}) for p in story.pages]}
    )
    try:
        verdict = await check_texts(job.rt, current, job.ai, book.parent_message)
    except BudgetExceeded:
        _set_flags(book, ["budget_exceeded"])
        return
    except QamraError as e:
        log.warning("classic.text_review_unavailable", book=str(book.id), error=str(e)[:200])
        _set_flags(book, ["text_review_unavailable"])
        return
    book.generation = {**book.generation, "text_review": {"safe": verdict.safe, "reasons": verdict.reasons}}
    _set_flags(
        book, [] if verdict.safe else ["text_unsafe"], remove=("text_unsafe", "text_review_unavailable")
    )
    job.db.commit()


async def render(job: ClassicJob, mode: str, story: StoryOut, portrait: bytes) -> dict[str, Any]:
    companion = default_companion(job.theme, book_lang(job.book))
    return await render_files(job.book_job(), mode, story, portrait, companion, None, None)


async def run_classic_job(db: Session, storage: ObjectStorage, book: Book, mode: str) -> dict[str, Any]:
    try:
        job = setup_classic(db, storage, book)
    except TemplateMissing as e:
        _set_flags(book, ["template_missing"])
        book.status, book.error = BookStatus.failed, str(e)[:500]
        db.commit()
        return {"status": "template_missing"}
    rt = job.rt
    rt.on_cost = CostSink(db, book, job.child.id)
    rt.budget = Budget(cap_usd=float(book.budget_usd or 0.54), spent_usd=float(book.cost_usd or 0))
    story = ensure_text(job)
    _set_flags(book, [], remove=("template_missing", "portrait_missing"))
    try:
        portrait = await ensure_portrait(db, storage, rt, book, job.child, job.ai)
    except (BudgetExceeded, LookupError, QamraError) as e:
        flag = "budget_exceeded" if isinstance(e, BudgetExceeded) else "portrait_missing"
        _set_flags(book, [flag])
        book.status, book.error = BookStatus.failed, f"portrait: {type(e).__name__}: {str(e)[:300]}"
        db.commit()
        return {"status": flag}
    rows = job.pages_by_beat()
    all_beats = wanted_beats(job, mode)
    done = {
        b
        for b, r in rows.items()
        if r.status in (PageStatus.ok, PageStatus.needs_review) and r.print_image_key
    }
    if mode == "preview":  # a page already finished for print only needs its watermarked copy
        for beat in [b for b in all_beats if b in done and not rows[b].preview_image_key]:
            add_preview(job, rows[beat])
    todo = [b for b in all_beats if b not in done]
    progress = {"done": len(all_beats) - len(todo), "total": len(all_beats), "beats": all_beats}
    book.generation = {**book.generation, "mode": mode, "progress": progress}
    db.commit()
    style = load_style(book.art_style)
    ctx = ClassicContext(child=job.ai, style=style, portrait=portrait, seed=int(book.generation["seed"]))
    jobs = _page_jobs(job, todo, mode)

    def saved(res: HeroEdit) -> None:
        save_page(job, res.beat, mode, page=res.page, status=res.status, flags=res.flags, edit=res)

    await edit_pages(rt, ctx, jobs, on_page=saved)
    if rt.budget.exceeded:
        _set_flags(book, ["budget_exceeded"])
        db.commit()
    if mode == "final":
        await review_texts(job, story)
    db.refresh(book)
    return await render(job, mode, story, portrait)


async def classic_redraw_pages(
    db: Session, storage: ObjectStorage, book: Book, beats: list[int]
) -> dict[str, Any]:
    """One manual re-edit per hero page (admin 'regenerate'): counts toward the budget, then new PDFs."""
    job = setup_classic(db, storage, book)
    rt = job.rt
    rt.on_cost = CostSink(db, book, job.child.id)
    rt.budget = Budget(cap_usd=float(book.budget_usd or 0.54), spent_usd=float(book.cost_usd or 0))
    story = ensure_text(job)
    portrait = await ensure_portrait(db, storage, rt, book, job.child, job.ai)
    mode = str(book.generation.get("mode", "final"))
    wanted = [b for b in sorted(set(beats)) if b in job.plan.beats]
    style = load_style(book.art_style)
    ctx = ClassicContext(child=job.ai, style=style, portrait=portrait, seed=int(book.generation["seed"]))
    results = await edit_pages(rt, ctx, _page_jobs(job, wanted, mode, manual=True), manual=True)
    redrawn = []
    for beat, res in sorted(results.items()):
        if res.page is None:  # keep the old page when the new attempt failed or was unsafe
            row = job.pages_by_beat().get(beat)
            if row is not None:
                row.attempts = [*(row.attempts or []), *[a.to_dict() for a in res.attempts]]
                db.commit()
            continue
        save_page(job, beat, mode, page=res.page, status=res.status, flags=res.flags, edit=res)
        row = job.pages_by_beat()[beat]
        row.regen_count = (row.regen_count or 0) + 1
        db.commit()
        redrawn.append(beat)
    if rt.budget.exceeded:
        _set_flags(book, ["budget_exceeded"])
        db.commit()
    return {**await render(job, mode, story, portrait), "redrawn": redrawn}


async def classic_rerender(db: Session, storage: ObjectStorage, book: Book) -> dict[str, Any]:
    """After text edits: rebuild the PDFs from the stored pages (no image calls)."""
    job = setup_classic(db, storage, book)
    job.rt.on_cost = CostSink(db, book, job.child.id)
    job.rt.budget = Budget(cap_usd=float(book.budget_usd or 0.54), spent_usd=float(book.cost_usd or 0))
    story = ensure_text(job)
    portrait = await ensure_portrait(db, storage, job.rt, book, job.child, job.ai)
    mode = str(book.generation.get("mode", "final"))
    if mode == "final":
        await review_texts(job, story)
    return await render(job, mode, story, portrait)


async def classic_book_flow(db: Session, storage: ObjectStorage, book: Book, mode: str) -> dict[str, Any]:
    """The preview; then, if the order was confirmed while it was drawing, the whole book right away."""
    result = await run_classic_job(db, storage, book, mode)
    db.refresh(book)
    if mode == "preview" and book.generation.get("final_requested") and book.status == BookStatus.preview:
        book.generation = {k: v for k, v in book.generation.items() if k != "final_requested"}
        book.status = BookStatus.generating
        db.commit()
        result = await run_classic_job(db, storage, book, "final")
    return result


# ---- RQ entry points ------------------------------------------------------------------------------------


def _book_entry(book_id: str, label: str, work: Any) -> dict[str, Any]:
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        book = db.get(Book, book_id)
        if book is None:
            return {"status": "missing"}
        previous = book.status
        book.status = BookStatus.generating
        book.error = None
        db.commit()
        try:
            return asyncio.run(work(db, storage, book))
        except Exception as e:
            db.rollback()
            book = db.get(Book, book_id)
            if book is not None:
                stuck = label == "generate" or previous == BookStatus.generating
                book.status = BookStatus.failed if stuck else previous
                book.error = f"{label}: {type(e).__name__}: {str(e)[:400]}"
                if label == "generate":
                    _set_flags(book, ["generation_failed"])
                db.commit()
            log.exception("classic.book_failed", book=book_id, step=label)
            raise


def generate_classic_book(book_id: str, mode: str = "final") -> dict[str, Any]:
    return _book_entry(book_id, "generate", lambda db, st, b: classic_book_flow(db, st, b, mode))


def redraw_classic(book_id: str, beats: list[int]) -> dict[str, Any]:
    return _book_entry(book_id, "redraw", lambda db, st, b: classic_redraw_pages(db, st, b, beats))


def rerender_classic(book_id: str) -> dict[str, Any]:
    return _book_entry(book_id, "rerender", classic_rerender)


def _template_entry(template_id: str, work: Any) -> dict[str, Any]:
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        template = db.get(ClassicTemplate, template_id)
        if template is None:
            return {"status": "missing"}
        template.job, template.error = TemplateJob.running, None
        db.commit()
        try:
            return asyncio.run(work(db, storage, template))
        except Exception as e:
            db.rollback()
            template = db.get(ClassicTemplate, template_id)
            if template is not None:
                template.job = TemplateJob.failed
                template.error = f"{type(e).__name__}: {str(e)[:400]}"
                _set_flags_on(template, ["job_failed"])
                db.commit()
            log.exception("classic.template_failed", template=template_id)
            raise


def generate_template(template_id: str, beats: list[int] | None = None) -> dict[str, Any]:
    return _template_entry(template_id, lambda db, st, t: run_template_job(db, st, t, beats))


def template_from_book(template_id: str, book_id: str) -> dict[str, Any]:
    async def work(db: Session, st: ObjectStorage, t: ClassicTemplate) -> dict[str, Any]:
        book = db.get(Book, book_id)
        if book is None:
            raise ValueError("the sample book is gone")
        return await run_template_from_book(db, st, t, book)

    return _template_entry(template_id, work)


def synthetic_face(key: str, spec: dict[str, Any]) -> dict[str, Any]:
    """An invented child's photo for the cost proof, drawn by the configured image model (never a real
    person). Stored under `classic/synthetic/`; its cost is logged without a book or a child."""
    if not key.startswith(SYNTHETIC_PREFIX):
        raise ValueError("synthetic faces live under classic/synthetic/")
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        settings = ai_settings(resolved_settings(db), get_settings(), offline=spec.get("offline") or False)
        rt = make_runtime(settings)
        rt.on_cost = CostSink(db, None, None)
        request = synthetic_face_request(
            gender="m" if spec.get("gender") == "m" else "f",
            age=int(spec.get("age", 5)),
            hijab=bool(spec.get("hijab")),
            glasses=bool(spec.get("glasses")),
            skin=str(spec.get("skin") or "light olive"),
            hair=str(spec.get("hair") or "dark brown"),
            top=str(spec.get("top") or "light blue"),
            seed=int(spec.get("seed", 1)),
        )
        image = asyncio.run(rt.draw(request))
        storage.put(key, image.data, image.mime)
        db.add(
            AuditLog(
                actor_user_id=None,
                action="classic.synthetic_face",
                entity_type="synthetic",
                entity_id=key.removeprefix(SYNTHETIC_PREFIX)[:64],
                data={"usd": image.cost.usd},
            )
        )
        db.commit()
        return {"key": key, "usd": image.cost.usd}


def vowelize_template(template_id: str, refresh: bool = False) -> dict[str, Any]:
    """Admin «شكّل النصوص»: vowelize the template's Arabic texts for its gender (again, with `refresh`)."""

    async def work(db: Session, st: ObjectStorage, t: ClassicTemplate) -> dict[str, Any]:
        offline = t.generation.get("offline") or False
        rt = make_runtime(ai_settings(resolved_settings(db), get_settings(), offline=offline))
        rt.on_cost = TemplateCostSink(db, t)
        await ensure_texts(db, rt, t, refresh=refresh)
        t.job, t.error = TemplateJob.idle, None
        db.commit()
        texts = t.generation.get("texts") or {}
        return {"status": t.status.value, "kept": texts.get("kept", []), "cost_usd": float(t.cost_usd or 0)}

    return _template_entry(template_id, work)
