"""Book generation jobs (Addendum 3): character sheet → companion → book (preview or final) → print files.

- Settings (models, keys, thresholds, budget) come from the admin settings at job start.
- Jobs are resumable: pages already drawn stay drawn, so an RQ retry after a crash only draws what is missing.
- Every paid call is written to `generation_costs` as it happens and added to the book's running cost; the
  book's budget cap stops a run early with a flag instead of overspending.
- Final books end in `in_review`: nothing reaches print or the parent's reader without an admin's approval
  (Addendum 3 §5), which is also the review of the story's words (docs/plans/admin-story-text-review.md).
All objects live under the child's storage prefix, so "delete my child's data" removes them in one call.
"""

import asyncio
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.cost import CostEntry
from qamra_ai.errors import QamraError
from qamra_ai.image.base import GeneratedImage, sniff_mime
from qamra_ai.pipeline.assemble import AssemblyInputs, BookFiles, assemble_book, plan_pages
from qamra_ai.pipeline.bible import StyleBible, build_bible
from qamra_ai.pipeline.book import BookRun, choose_outfits, default_companion, new_seed
from qamra_ai.pipeline.budget import Budget, BudgetExceeded
from qamra_ai.pipeline.character import generate_character_sheet
from qamra_ai.pipeline.character_feedback import appearance_instruction
from qamra_ai.pipeline.companion import generate_companion_options
from qamra_ai.pipeline.custom_story import BriefRejected, CustomBrief, write_custom_story
from qamra_ai.pipeline.drawing import clean_drawing
from qamra_ai.pipeline.gender_check import FLAG as GENDER_FLAG
from qamra_ai.pipeline.gender_check import GenderIssue, gender_issues
from qamra_ai.pipeline.layout import BookPlan, PrintSpec, plan_book
from qamra_ai.pipeline.models import Child as AIChild
from qamra_ai.pipeline.models import CompanionSpec, Lang, StoryOut
from qamra_ai.pipeline.pages import (
    BookContext,
    Mode,
    PageResult,
    beats_for,
    generate_beat,
    generate_pages,
    prepare_book,
    theme_companion_sheet,
)
from qamra_ai.pipeline.photo_crop import crop_photo
from qamra_ai.pipeline.printimg import downscale
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.story import missing_text, write_story
from qamra_ai.pipeline.style import house_style
from qamra_ai.pipeline.theme import ArtStyle, Theme, load_style
from qamra_core.crypto import cipher_for
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    Companion,
    GenerationCost,
    Locale,
    PageStatus,
    PhotoStatus,
    SafetyStatus,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.settings_store import Resolved, load_sync
from qamra_core.storage import ObjectNotFound, ObjectStorage
from qamra_pdf import Brand
from qamra_pdf.mockups import mockups_from_pdfs, spread_from_pages
from qamra_pdf.spec import Series
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.notify import queue as notify_queue
from qamra_worker.settings import get_settings
from qamra_worker.voice import voice_url

log = structlog.get_logger("qamra.worker.books")

THUMB_PX = 520


# ---- storage keys (everything under the child's prefix) -------------------------------------------


def book_prefix(book: Book) -> str:
    return f"children/{book.child_id}/books/{book.id}/"


def page_key(book: Book, beat: int, kind: str) -> str:
    ext = "jpg" if kind in ("print", "thumb") else "png"
    return f"{book_prefix(book)}{kind}/{beat:02d}.{ext}"


def file_key(book: Book, name: str) -> str:
    return f"{book_prefix(book)}files/{name}"


MOCKUP_TIMEOUT_S = 180


async def store_mockups(storage: ObjectStorage, book: Book, files: BookFiles, work: Path) -> dict[str, str]:
    """Addendum 11 §2.7: the hardcover and open-spread product mockups, rendered from the print files and
    stored beside them (`files/mockup-hardcover.png`, `files/mockup-spread.png`). Marketing material only:
    any failure is logged and the book carries on without them."""
    if files.interior_pdf is None or files.cover_pdf is None:
        return {}
    try:
        made = await asyncio.wait_for(
            mockups_from_pdfs(
                files.cover_pdf,
                files.interior_pdf,
                files.spec.lang,
                work / "mockups",
                spread=spread_from_pages(files.spec.pages, files.spec.lang),
            ),
            MOCKUP_TIMEOUT_S,
        )
        keys: dict[str, str] = {}
        for name, path in (("hardcover", made.hardcover), ("spread", made.spread)):
            if path is not None and path.is_file():
                keys[name] = file_key(book, f"mockup-{name}.png")
                storage.put(keys[name], path.read_bytes(), "image/png")
        return keys
    except Exception as e:  # never fail a book over its mockups
        log.warning("book.mockups_failed", book=str(book.id), error=f"{type(e).__name__}: {str(e)[:200]}")
        return {}


class S3PlateStore:
    """Theme-level background plates: shared by every book, never tied to a child."""

    def __init__(self, storage: ObjectStorage) -> None:
        self.storage = storage

    def get(self, key: str) -> bytes | None:
        try:
            return self.storage.get(key)
        except ObjectNotFound:
            return None

    def put(self, key: str, data: bytes) -> None:
        self.storage.put(key, data, "image/png")


# ---- loading ----------------------------------------------------------------------------------------


def book_theme(db: Session, book: Book) -> Theme:
    """The theme as it was when this book started: content edits never move an already drawn book."""
    snapshot = (book.generation or {}).get("theme_def")
    if snapshot:
        return Theme.model_validate(snapshot)
    row = db.get(ThemeRow, book.theme_id)
    if row is None:
        raise ValueError("theme not found")
    book.generation = {**(book.generation or {}), "theme_def": row.definition}
    book.theme_version = row.version
    return Theme.model_validate(row.definition)


def ai_child(child: Child) -> AIChild:
    age = max(2, min(12, date.today().year - child.birth_year))
    return AIChild(
        name=child.first_name,
        gender=child.gender.value,
        age=age,
        interests=list(child.interests or []),
        hijab=child.wears_hijab,
        glasses=child.wears_glasses,
    )


def book_lang(book: Book) -> Lang:
    return "ar" if book.language == Locale.ar else "en"


def as_mode(value: object) -> Mode:
    return "preview" if value == "preview" else "final"


def resolved_settings(db: Session) -> Resolved:
    return load_sync(db, cipher_for(get_settings()))


def brand() -> Brand:
    s = get_settings()
    return Brand(s.brand_name_ar, s.brand_name_en, s.brand_domain, "", "")


@dataclass
class CostSink:
    """Writes each paid call to generation_costs and the book/page running totals, as it happens."""

    db: Session
    book: Book | None
    child_id: Any

    def __call__(self, entry: CostEntry) -> None:
        usd = Decimal(str(round(entry.usd, 5)))
        self.db.add(
            GenerationCost(
                book_id=self.book.id if self.book else None,
                child_id=self.child_id,
                step=entry.step[:64],
                provider=entry.provider[:32],
                model=entry.model[:100],
                units=entry.units,
                usd=usd,
                estimated=entry.estimated,
            )
        )
        if self.book is not None:
            self.book.cost_usd = (self.book.cost_usd or Decimal("0")) + usd
            beat = _beat_of(entry.step)
            if beat is not None:
                page = self.db.scalar(
                    select(BookPage).where(BookPage.book_id == self.book.id, BookPage.index == beat)
                )
                if page is not None:
                    page.cost_usd = (page.cost_usd or Decimal("0")) + usd
        self.db.commit()


def _beat_of(step: str) -> int | None:
    parts = step.split(":")
    if parts[0] == "cover" or (parts[0] in ("qa", "upscale") and len(parts) > 1 and parts[1] == "cover"):
        return 0
    if parts[0] in ("page", "hero") and len(parts) > 1 and parts[1].isdigit():  # hero: Classic edits
        return int(parts[1])
    if parts[0] == "hero" and len(parts) > 1 and parts[1] == "cover":
        return 0
    if parts[0] in ("qa", "upscale") and len(parts) > 1:
        tail = parts[-1] if parts[0] == "upscale" else parts[1]
        return int(tail) if tail.isdigit() else None
    return None


# ---- per-child steps ------------------------------------------------------------------------------


# What the parent asked for a drawing (the API's) and what their note became, kept next to how it was drawn:
# the redraw's number, the chips, their own words and the appearance-only instruction made of them.
ASKED = ("attempt", "fixes", "note", "note_instruction", "note_outcome")


async def _read_note(
    db: Session, rt: Runtime, character: Character, child: Child, asked: dict[str, Any]
) -> None:
    """The parent's note → the redraw's instruction, saved before drawing (a retried job doesn't ask
    again). An unsafe or off-topic note, or a failed text step, leaves the chips alone; the log has the
    outcome only, never the note."""
    result = await appearance_instruction(rt, ai_child(child), str(asked["note"]))
    asked["note_outcome"] = result.outcome
    if result.instruction:
        asked["note_instruction"] = result.instruction
    character.params = {**(character.params or {}), **asked}
    db.commit()
    log.info("character.note", character=str(character.id), outcome=result.outcome, reasons=result.reasons)


async def _character(db: Session, storage: ObjectStorage, rt: Runtime, character: Character) -> bytes:
    if character.status in (CharacterStatus.ready, CharacterStatus.approved) and character.sheet_image_key:
        return storage.get(character.sheet_image_key)
    child = db.get(Child, character.child_id)
    if child is None:
        raise ValueError("child not found")
    photos = db.scalars(
        select(ChildPhoto).where(
            ChildPhoto.child_id == child.id,
            ChildPhoto.status == PhotoStatus.accepted,
            ChildPhoto.storage_key.is_not(None),
        )
    ).all()
    data = [d for p in photos[:3] if (d := photo_bytes(storage, p)) is not None]  # as the parent framed it
    if not data:
        raise ValueError("no accepted photos (they may have been deleted after approval)")
    asked: dict[str, Any] = {k: v for k, v in (character.params or {}).items() if k in ASKED}
    if asked.get("note") and "note_outcome" not in asked:
        await _read_note(db, rt, character, child, asked)
    sheet = await generate_character_sheet(
        rt,
        ai_child(child),
        data,
        load_style(character.art_style),
        attempt=int(asked.get("attempt", 1)),  # a redraw gets a new seed
        fixes=[str(f) for f in asked.get("fixes", [])],
        note=str(asked["note_instruction"]) if asked.get("note_instruction") else None,
    )
    key = f"children/{child.id}/characters/{character.id}.png"
    storage.put(key, sheet.data, sheet.mime)
    character.sheet_image_key = key
    character.status = CharacterStatus.ready
    character.provider = str(sheet.params.get("provider", rt.image.name))[:32]
    character.model = str(sheet.params.get("model", rt.image.model))[:100]
    drawn = {k: v for k, v in sheet.params.items() if isinstance(v, str | int | float)}
    character.params = {**asked, **drawn}  # keeps what the parent asked for next to how it was drawn
    db.commit()
    return sheet.data


async def _companion(
    db: Session, storage: ObjectStorage, rt: Runtime, comp: Companion, style: str
) -> tuple[CompanionSpec, bytes, bytes]:
    """(spec, final sheet, cleaned drawing) — generated once per child and reused (Addendum 3 §2.2)."""
    spec = CompanionSpec(
        name=comp.name,
        type_hint=comp.type_hint.value,
        type_other=comp.type_other,
        traits=comp.traits,
        description_en=comp.description_en or "",
        from_drawing=True,
    )
    if comp.sheet_key and comp.cleaned_key:
        return spec, storage.get(comp.sheet_key), storage.get(comp.cleaned_key)
    if comp.cleaned_key:
        cleaned = storage.get(comp.cleaned_key)
    elif comp.drawing_key:
        cleaned = clean_drawing(storage.get(comp.drawing_key)).png
        comp.cleaned_key = f"children/{comp.child_id}/companions/{comp.id}/cleaned.png"
        storage.put(comp.cleaned_key, cleaned, "image/png")
    else:
        raise ValueError("the companion has no drawing")
    options = await generate_companion_options(rt, cleaned, spec, load_style(style))
    chosen = options.options[0]
    comp.sheet_key = f"children/{comp.child_id}/companions/{comp.id}/sheet.png"
    storage.put(comp.sheet_key, chosen.data, chosen.mime)
    comp.description_en = options.spec.description_en
    comp.provider = str(chosen.params.get("provider", rt.image.name))[:32]
    comp.model = str(chosen.params.get("model", rt.image.model))[:100]
    db.commit()
    return options.spec, chosen.data, cleaned


# ---- the book ---------------------------------------------------------------------------------------


@dataclass
class BookJob:
    db: Session
    storage: ObjectStorage
    book: Book
    child: Child
    theme: Theme
    rt: Runtime
    plan: BookPlan

    def pages_by_beat(self) -> dict[int, BookPage]:
        rows = self.db.scalars(select(BookPage).where(BookPage.book_id == self.book.id)).all()
        return {r.index: r for r in rows}

    def save_page(self, res: PageResult, mode: str) -> None:
        rows = self.pages_by_beat()
        row = rows.get(res.beat) or BookPage(book_id=self.book.id, index=res.beat)
        beat = self.plan.beats[res.beat]
        row.layout = beat.layout
        row.status = PageStatus(res.status)
        row.flags = list(dict.fromkeys(res.flags))
        row.attempts = [*(row.attempts or []), *[a.to_dict() for a in res.attempts]]
        if res.qa is not None:
            row.qa = res.qa.model_dump()
            row.safety_status = SafetyStatus.passed if res.qa.safe else SafetyStatus.failed
        if res.verdict is not None:
            row.qa_score = Decimal(str(res.verdict.score))
        if res.image is not None:
            kind = "preview" if mode == "preview" else "raw"
            key = page_key(self.book, res.beat, kind)
            self.storage.put(key, res.image.data, res.image.mime)
            if mode == "preview":
                row.preview_image_key = key
            row.image_key = key
            self.storage.put(
                page_key(self.book, res.beat, "thumb"), downscale(res.image.data, THUMB_PX, 82), "image/jpeg"
            )
        if res.print_image is not None:
            key = page_key(self.book, res.beat, "print")
            self.storage.put(key, res.print_image, "image/jpeg")
            row.print_image_key = key
        if row.id is None:
            self.db.add(row)
        self.db.flush()
        progress = dict(self.book.generation.get("progress", {}))

        def drawn(r: BookPage) -> bool:
            key = r.print_image_key if mode == "final" else r.preview_image_key
            return bool(key) or r.status in (PageStatus.failed, PageStatus.skipped)

        progress["done"] = sum(drawn(r) for b, r in self.pages_by_beat().items() if b in self.plan.beats)
        self.book.generation = {**self.book.generation, "progress": progress}
        self.db.commit()

    def image_bytes(self, key: str | None) -> bytes | None:
        if not key:
            return None
        try:
            return self.storage.get(key)
        except ObjectNotFound:
            return None


def _set_flags(book: Book, add: list[str], remove: tuple[str, ...] = ()) -> None:
    """Drop the flags in `remove` (they are re-evaluated), then add `add`."""
    kept = [f for f in (book.flags or []) if f not in remove]
    book.flags = list(dict.fromkeys([*kept, *add]))


def review_gender(
    job: "BookJob", story: StoryOut, companion: CompanionSpec | None, found: list[GenderIssue] | None = None
) -> list[dict[str, str]]:
    """«تحقق من التذكير والتأنيث» (`qamra_ai.pipeline.gender_check`): the hero's gender read in the book's
    words as they are now (the family's and the staff's edits included). Words worth a second look flag the
    book `gender_check` for the staff text review, with the hints in `generation.gender_check`; nothing found
    clears both. The safety review's own notes (`generation.gender_notes`) count while no page was reworded.
    It never fails a book."""
    book = job.book
    child = ai_child(job.child)
    issues = (
        found
        if found is not None
        else gender_issues(
            story,
            child.name,
            child.gender,
            book_lang(book),
            companion=companion.name if companion else "",
            theme=job.theme,
        )
    )
    hints = [i.to_dict() for i in issues if i.rule != "text_review"]
    rows = job.pages_by_beat()
    reworded = any(r.text != r.original_text for b, r in rows.items() if b > 0 and r.original_text)
    notes = [] if reworded else list((book.generation or {}).get("gender_notes") or [])
    hints += [n for n in notes if n not in hints]
    gen = {k: v for k, v in (book.generation or {}).items() if k != "gender_check"}
    book.generation = {**gen, "gender_check": hints} if hints else gen
    _set_flags(book, [GENDER_FLAG] if hints else [], remove=(GENDER_FLAG,))
    return hints


def _qa_summary(rows: dict[int, BookPage], plan: BookPlan) -> dict[str, Any]:
    story = [r for b, r in rows.items() if b in plan.beats and r.status != PageStatus.pending]
    likeness = [
        int(r.qa.get("likeness", 0))
        for b, r in rows.items()
        if b in plan.beats and r.qa and not plan.beats[b].no_child and r.status != PageStatus.pending
    ]
    whys = [a.get("why") for r in story for a in (r.attempts or [])]
    redraws = whys.count("qa")  # automatic redraws after failing QA; see qamra_ai.pipeline.pages.Why
    return {
        "pages": len(story),
        "ok": sum(r.status == PageStatus.ok for r in story),
        "needs_review": sum(r.status == PageStatus.needs_review for r in story),
        "failed": sum(r.status in (PageStatus.failed, PageStatus.skipped) for r in story),
        "avg_likeness": round(sum(likeness) / len(likeness) / 10, 3) if likeness else None,
        "recognizable_ratio": round(sum(v >= 7 for v in likeness) / len(likeness), 3) if likeness else None,
        "avg_score": round(
            sum(float(r.qa_score) for r in story if r.qa_score is not None)
            / max(1, sum(r.qa_score is not None for r in story)),
            3,
        ),
        "redraws": redraws,
        "redraw_rate": round(redraws / max(1, len(story)), 3),
        "manual_redraws": whys.count("manual"),
        "fallback_used": sum("fallback_used" in (r.flags or []) for r in story),
    }


def book_bible(
    book: Book, theme: Theme, child: Child, style: ArtStyle, companion: CompanionSpec | None
) -> StyleBible:
    """The book's style bible (Addendum 11 §4.1): stored on its first run, reused unchanged afterwards."""
    stored = (book.generation or {}).get("bible")
    if stored:
        return StyleBible.model_validate(stored)
    bible = build_bible(
        theme, ai_child(child), int(book.generation["seed"]), style=style.slug, companion=companion
    )
    book.generation = {**book.generation, "bible": bible.model_dump(mode="json")}
    return bible


def photo_bytes(storage: ObjectStorage, photo: ChildPhoto | None) -> bytes | None:
    """A child's photo as the image model gets it: the parent's framing of the original (head and shoulders,
    upright: `qamra_ai.pipeline.photo_crop`), else the whole photo. None once the photo is deleted."""
    if photo is None or not photo.storage_key:
        return None
    try:
        data = storage.get(photo.storage_key)
    except ObjectNotFound:
        return None
    return crop_photo(data, photo.crop)


def cover_photo(db: Session, storage: ObjectStorage, child: Child) -> bytes | None:
    """The child's first accepted photo while it is still kept (Addendum 11 §1: the cover's likeness
    reference). It goes to the image model only, like the character sheet's photos, never to QA."""
    now = datetime.now(UTC)
    for photo in db.scalars(
        select(ChildPhoto)
        .where(
            ChildPhoto.child_id == child.id,
            ChildPhoto.status == PhotoStatus.accepted,
            ChildPhoto.storage_key.is_not(None),
            ChildPhoto.deleted_at.is_(None),
        )
        .order_by(ChildPhoto.created_at)
    ).all():
        kept = photo.delete_after is None or photo.delete_after > now
        if kept and (data := photo_bytes(storage, photo)) is not None:
            return data
    return None


def load_group_refs(job: "BookJob", ctx: BookContext, rows: dict[int, BookPage]) -> None:
    """Outfit references of a resumed book: each scene group's first accepted page (Addendum 11 §4.1)."""
    for beat in sorted(rows):
        row = rows[beat]
        plan = job.plan.beats.get(beat)
        if beat == 0 or plan is None or plan.no_child or row.status != PageStatus.ok:
            continue
        group = ctx.group(beat)
        if group == ctx.locks.main_group or group in ctx.group_refs:
            continue
        data = job.image_bytes(row.image_key)
        if data is not None:
            ctx.group_refs[group] = (beat, data)


async def _setup(db: Session, storage: ObjectStorage, book: Book) -> BookJob:
    core = get_settings()
    resolved = resolved_settings(db)
    offline = book.generation.get("offline") or False
    settings = ai_settings(resolved, core, offline=offline)
    rt = make_runtime(settings)
    child = db.get(Child, book.child_id)
    if child is None:
        raise ValueError("child not found")
    theme = book_theme(db, book)
    spec = PrintSpec.from_settings(settings)
    has_companion_page = bool(book.companion_id)
    plan = plan_book(theme, book_lang(book), companion_page=has_companion_page, spec=spec)
    gen = dict(book.generation)
    gen.setdefault("seed", new_seed())
    gen.setdefault("outfits", choose_outfits(theme, ai_child(child), int(gen["seed"])))
    gen["plan"] = plan_pages(plan)
    gen["models"] = {
        "image": settings.image_provider
        if offline
        else f"{settings.image_provider}:{settings.fal_image_model}",
        "fallback": settings.fal_fallback_model,
        "cover": settings.cover_image_model or None,
        "upscale": settings.fal_upscale_model,
        "text": settings.text_model,
        "text_fast": settings.text_model_fast,
        "final_mode": settings.final_mode,
        "style": house_style().prompt_id,
    }
    book.generation = gen
    if book.budget_usd is None:
        book.budget_usd = Decimal(str(settings.book_budget_usd))
    db.commit()
    return BookJob(db, storage, book, child, theme, rt, plan)


async def run_book_job(db: Session, storage: ObjectStorage, book: Book, mode: str) -> dict[str, Any]:
    job = await _setup(db, storage, book)
    rt, child, theme = job.rt, job.child, job.theme
    sink_child = CostSink(db, None, child.id)
    rt.on_cost = sink_child  # per-child steps: not counted against the book cap
    character = db.get(Character, book.character_id) if book.character_id else None
    if character is None:
        raise ValueError("the book has no character")
    sheet = await _character(db, storage, rt, character)
    if character.status == CharacterStatus.ready and book.is_sample:
        character.status = CharacterStatus.approved  # samples: the admin reviews the whole book instead
        character.approved_at = datetime.now(UTC)
        retention = int(resolved_settings(db).values["photo_retention_hours"])
        for photo in db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == child.id)).all():
            photo.delete_after = photo.delete_after or datetime.now(UTC) + timedelta(hours=retention)
        db.commit()
    companion: CompanionSpec | None = default_companion(theme, book_lang(book))
    companion_sheet = drawing = None
    comp_row = db.get(Companion, book.companion_id) if book.companion_id else None
    if comp_row is not None:
        companion, companion_sheet, drawing = await _companion(db, storage, rt, comp_row, book.art_style)

    rt.on_cost = CostSink(db, book, child.id)
    rt.budget = Budget(cap_usd=float(book.budget_usd or 3), spent_usd=float(book.cost_usd or 0))
    lang = book_lang(book)
    story_out: StoryOut | None = StoryOut.model_validate(book.story) if book.story else None
    try:
        brief = book.generation.get("custom")  # «حكاية خاصة» (W3): text and pictures from the family's brief
        if story_out is None and brief:
            wish, note = CustomBrief.model_validate(brief), book.parent_message
            custom = await write_custom_story(rt, theme, ai_child(child), lang, companion, wish, note)
            story, theme = custom.story, custom.theme
            job.theme = theme  # the pages are drawn from the story's own scenes, pinned with the book
            book.generation = {**book.generation, "theme_def": theme.model_dump(mode="json")}
        elif story_out is None:
            story = await write_story(rt, theme, ai_child(child), lang, companion, book.parent_message)
        if story_out is None:
            story_out = story.out
            book.story = story_out.model_dump()
            book.title = story_out.title[:200]
            book.dedication = story_out.dedication
            rows = job.pages_by_beat()
            for p in story_out.pages:
                row = rows.get(p.index) or BookPage(book_id=book.id, index=p.index)
                row.text = row.original_text = p.text
                if row.id is None:
                    db.add(row)
            if 0 not in rows:
                db.add(
                    BookPage(book_id=book.id, index=0, text=story_out.title, original_text=story_out.title)
                )
            if story.long_pages:
                _set_flags(book, ["long_text"])
            notes = [i.to_dict() for i in story.gender_issues if i.rule == "text_review"]
            book.generation = {**book.generation, "gender_notes": notes}
            db.flush()
            review_gender(job, story_out, companion, story.gender_issues)
            db.commit()
    except BriefRejected as e:  # the parent edits the brief and starts again (not retried)
        _set_flags(book, ["brief_unsafe"])
        book.status, book.error = BookStatus.failed, str(e)[:500]
        db.commit()
        return {"status": "brief_unsafe"}
    except BudgetExceeded:
        _set_flags(book, ["budget_exceeded"])
        book.status = BookStatus.failed
        db.commit()
        return {"status": "budget_exceeded"}

    rows = job.pages_by_beat()
    done = {
        b
        for b, r in rows.items()
        if r.status in (PageStatus.ok, PageStatus.needs_review)
        and (r.print_image_key if mode == "final" else r.preview_image_key)
    }
    cover_row = rows.get(0)
    cover_bytes = job.image_bytes(cover_row.image_key) if cover_row and 0 in done else None
    cover_print = job.image_bytes(cover_row.print_image_key) if cover_row and 0 in done else None
    previews = (
        {
            b: data
            for b, r in rows.items()
            if r.preview_image_key and (data := job.image_bytes(r.preview_image_key))
        }
        if mode == "final"
        else {}
    )
    empty = missing_text(theme, story_out)
    if empty:  # Addendum 11 §4.4: a page the theme expects text on is empty — never draw or print it
        _set_flags(book, ["text_missing"])
        book.status, book.error = BookStatus.failed, f"story pages without text: {empty}"
        db.commit()
        return {"status": "text_missing"}
    style = load_style(book.art_style)
    ctx = BookContext(
        child=ai_child(child),
        lang=lang,
        theme=theme,
        style=style,
        house=house_style(),
        plan=job.plan,
        character_sheet=sheet,
        outfits=dict(book.generation["outfits"]),
        seed=int(book.generation["seed"]),
        mode=as_mode(mode),
        companion=companion,
        companion_sheet=companion_sheet,
        cover=cover_bytes,
        cover_qa=cover_print,
        previews=previews,
        plates=S3PlateStore(storage),
        on_page=lambda r: job.save_page(r, mode),
        bible=book_bible(book, theme, child, style, companion),
    )
    load_group_refs(job, ctx, rows)
    wanted = [b for b in beats_for(ctx, rt.settings.preview_pages) if b not in done]
    if 0 in wanted:
        ctx.photo = cover_photo(db, storage, child)
    book.generation = {
        **book.generation,
        "mode": mode,
        "progress": {"done": len(done), "total": len(beats_for(ctx, rt.settings.preview_pages))},
    }
    db.commit()
    await generate_pages(rt, ctx, wanted)
    if rt.budget.exceeded:
        _set_flags(book, ["budget_exceeded"])
    db.refresh(book)
    sheet_for_print = await print_companion_sheet(rt, ctx, companion_sheet)
    return await render_files(job, mode, story_out, sheet, companion, sheet_for_print, drawing)


async def print_companion_sheet(rt: Runtime, ctx: BookContext, drawn: bytes | None) -> bytes | None:
    """The companion's sheet for the printed pages (its cut-out peeks on «ارسم أجمل لحظة»): the child's own
    companion, else the theme's fixed «قمّور» (a content file, or drawn once and kept in the plate store)."""
    if drawn is not None or ctx.companion is None or ctx.companion.from_drawing:
        return drawn
    if ctx.companion_sheet is None:
        ctx.companion_sheet = await theme_companion_sheet(rt, ctx)
    return ctx.companion_sheet


def cover_series(generation: dict[str, Any] | None) -> Series | None:
    """The product line the cover names: a custom story («حكاية خاصة»), else the book's line."""
    gen = generation or {}
    if gen.get("custom"):
        return "custom"
    line = gen.get("line")
    return line if line in ("classic", "magic", "class") else None


async def render_files(
    job: BookJob,
    mode: str,
    story: StoryOut,
    sheet: bytes,
    companion: CompanionSpec | None,
    companion_sheet: bytes | None,
    drawing: bytes | None,
) -> dict[str, Any]:
    """Assemble the PDFs from what is stored (also after text edits and redraws)."""
    db, storage, book = job.db, job.storage, job.book
    rows = job.pages_by_beat()
    texts = {b: r.text for b, r in rows.items() if b > 0 and r.text}
    story = story.model_copy(
        update={"pages": [p.model_copy(update={"text": texts.get(p.index, p.text)}) for p in story.pages]}
    )
    empty = missing_text(job.theme, story)
    if empty:  # Addendum 11 §4.4: the build fails rather than print a page without its text
        _set_flags(book, ["text_missing"])
        book.status, book.error = BookStatus.failed, f"story pages without text: {empty}"
        db.commit()
        return {"status": "text_missing"}
    review_gender(job, story, companion)  # the words as they print now, edits included
    run = BookRun(
        plan=job.plan,
        seed=int(book.generation["seed"]),
        outfits=book.generation["outfits"],
        story=None,
        pages={},
    )
    for beat, row in rows.items():
        if beat not in job.plan.beats:
            continue
        raw = job.image_bytes(row.image_key)
        printed = job.image_bytes(row.print_image_key) if mode == "final" else None
        if raw is None:
            continue
        run.pages[beat] = PageResult(
            beat=beat,
            status="ok" if row.status == PageStatus.ok else "needs_review",
            image=GeneratedImage(raw, sniff_mime(raw), CostEntry("stored", "db", "stored", {}, 0.0)),
            print_image=printed,
        )
    missing = [b for b in (job.plan.beats if mode == "final" else []) if b not in run.pages]
    with tempfile.TemporaryDirectory(prefix="qamra-book-") as tmp:
        try:
            files: BookFiles = await assemble_book(
                AssemblyInputs(
                    run=run,
                    story=story,
                    child=ai_child(job.child),
                    lang=book_lang(book),
                    brand=brand(),
                    character_sheet=sheet,
                    parent_message=book.parent_message,
                    companion_name=companion.name if companion else None,
                    drawing=drawing,
                    companion_sheet=companion_sheet,
                    made_on=date.today(),
                    watermark=mode == "preview",
                    voice_url=voice_url(db, book, brand().domain) if mode == "final" else None,
                    series=cover_series(book.generation),
                ),
                Path(tmp),
                print_files=mode == "final" and not missing,
            )
        except (QamraError, ValueError) as e:
            log.warning("book.render_failed", book=str(book.id), error=str(e)[:200])
            _set_flags(book, ["render_failed"])
            book.status = BookStatus.failed
            book.error = str(e)[:500]
            db.commit()
            return {"status": "render_failed"}
        if files.proof_pdf:
            key = file_key(book, "proof.pdf")
            storage.put(key, files.proof_pdf.read_bytes(), "application/pdf")
            book.proof_pdf_key = key
        if files.interior_pdf and files.cover_pdf:
            book.pdf_interior_key = file_key(book, "interior.pdf")
            storage.put(book.pdf_interior_key, files.interior_pdf.read_bytes(), "application/pdf")
            book.pdf_cover_key = file_key(book, "cover.pdf")
            storage.put(book.pdf_cover_key, files.cover_pdf.read_bytes(), "application/pdf")
            mockups = await store_mockups(storage, book, files, Path(tmp))
            gen = {k: v for k, v in (book.generation or {}).items() if k != "mockups"}
            book.generation = {**gen, "mockups": mockups} if mockups else gen
        book.preflight = {k: v.to_dict() for k, v in files.preflight.items()}
        layout_flags = {str(k): v for k, v in files.flags.items() if v}
    rows = job.pages_by_beat()
    book.qa_summary = {**_qa_summary(rows, job.plan), "layout_flags": layout_flags}
    flags = [
        f for f in ("pages_need_review",) if book.qa_summary["needs_review"] or book.qa_summary["failed"]
    ]
    if missing:
        flags.append("pages_missing")
    if mode == "final" and files.preflight and not files.preflight_passed:
        flags.append("preflight_failed")
    if any("text_overflow" in v for v in layout_flags.values()):
        flags.append("text_overflow")
    _set_flags(  # `text_changed` (staff edited the words): these files now carry them
        book,
        flags,
        remove=(
            "pages_need_review",
            "pages_missing",
            "preflight_failed",
            "text_overflow",
            "render_failed",
            "text_changed",
        ),
    )
    book.status = BookStatus.in_review if mode == "final" else BookStatus.preview
    book.error = None
    db.add(
        AuditLog(
            actor_user_id=None,
            action=f"book.{mode}_ready",
            entity_type="book",
            entity_id=str(book.id),
            data={"flags": book.flags, "cost_usd": float(book.cost_usd)},
        )
    )
    db.commit()
    log.info("book.ready", book=str(book.id), mode=mode, cost=float(book.cost_usd), flags=book.flags)
    notify_queue.book_ready(book, mode)  # "preview ready" / "book ready" email, once per book and stage
    return {"status": book.status.value, "cost_usd": float(book.cost_usd), "flags": book.flags}


async def redraw_pages(db: Session, storage: ObjectStorage, book: Book, beats: list[int]) -> dict[str, Any]:
    """One manual redraw per page (admin 'regenerate'): counts toward the budget, then re-renders the PDFs."""
    job = await _setup(db, storage, book)
    rt, child, theme = job.rt, job.child, job.theme
    rt.on_cost = CostSink(db, book, child.id)
    rt.budget = Budget(cap_usd=float(book.budget_usd or 3), spent_usd=float(book.cost_usd or 0))
    character = db.get(Character, book.character_id) if book.character_id else None
    if character is None or not character.sheet_image_key:
        raise ValueError("character sheet missing")
    sheet = storage.get(character.sheet_image_key)
    companion: CompanionSpec | None = default_companion(theme, book_lang(book))
    companion_sheet = drawing = None
    comp_row = db.get(Companion, book.companion_id) if book.companion_id else None
    if comp_row is not None:
        companion, companion_sheet, drawing = await _companion(db, storage, rt, comp_row, book.art_style)
    rows = job.pages_by_beat()
    mode = str(book.generation.get("mode", "final"))
    cover = job.image_bytes(rows[0].image_key) if 0 in rows else None
    cover_qa = job.image_bytes(rows[0].print_image_key) if 0 in rows and mode == "final" else None
    style = load_style(book.art_style)
    ctx = BookContext(
        child=ai_child(child),
        lang=book_lang(book),
        theme=theme,
        style=style,
        house=house_style(),
        plan=job.plan,
        character_sheet=sheet,
        outfits=dict(book.generation["outfits"]),
        seed=int(book.generation["seed"]),
        mode=as_mode(mode),
        companion=companion,
        companion_sheet=companion_sheet,
        cover=cover,
        cover_qa=cover_qa,  # the same QA prefix as the book's run, so its cache is reused
        plates=S3PlateStore(storage),
        bible=book_bible(book, theme, child, style, companion),
    )
    load_group_refs(job, ctx, rows)
    if 0 in beats:
        ctx.photo = cover_photo(db, storage, child)
    await prepare_book(rt, ctx, beats)
    done: list[int] = []
    for beat in beats:
        if beat not in job.plan.beats:
            continue
        row = rows.get(beat)
        first = len(row.attempts or []) + 1 if row else 1
        try:
            res = await generate_beat(rt, ctx, beat, first_attempt=first, manual=True)
        except BudgetExceeded:
            _set_flags(book, ["budget_exceeded"])
            db.commit()
            break
        if res.image is None:  # keep the old picture when the new attempt failed or was unsafe
            if row is not None:
                row.attempts = [*(row.attempts or []), *[a.to_dict() for a in res.attempts]]
                db.commit()
            continue
        job.save_page(res, mode)
        row = job.pages_by_beat()[beat]
        row.regen_count = (row.regen_count or 0) + 1
        db.commit()
        done.append(beat)
        if beat == 0:
            ctx.cover = res.image.data
    story = StoryOut.model_validate(book.story)
    sheet_for_print = await print_companion_sheet(rt, ctx, companion_sheet)
    result = await render_files(job, mode, story, sheet, companion, sheet_for_print, drawing)
    return {**result, "redrawn": done}


# ---- RQ entry points --------------------------------------------------------------------------------


def _run(coro_factory: Any) -> Any:
    return asyncio.run(coro_factory())


def _classic(book_id: str) -> bool:
    """«قمرة كلاسيك» books have their own jobs (jobs.classic); the admin's actions reach them through here."""
    with context.db_session() as db:
        book = db.get(Book, book_id)
        return book is not None and (book.generation or {}).get("line") == "classic"


def _class_copy(book_id: str) -> bool:
    """A child's copy of a «كتاب الصف» (jobs.classbooks): the admin's actions redraw it within its class."""
    with context.db_session() as db:
        book = db.get(Book, book_id)
        return book is not None and (book.generation or {}).get("line") == "class"


def generate_book(book_id: str, mode: str = "final") -> dict[str, Any]:
    context.init_process()
    if _classic(book_id):
        from qamra_worker.jobs.classic import generate_classic_book

        return generate_classic_book(book_id, mode)
    if _class_copy(book_id):
        from qamra_worker.jobs.classbooks import copy_action

        return copy_action(book_id, [])
    storage = context.storage()
    with context.db_session() as db:
        book = db.get(Book, book_id)
        if book is None:
            return {"status": "missing"}
        book.status = BookStatus.generating
        book.error = None
        db.commit()
        try:
            return _run(lambda: run_book_job(db, storage, book, mode))  # type: ignore[no-any-return]
        except Exception as e:
            db.rollback()
            book = db.get(Book, book_id)
            if book is not None:
                book.status = BookStatus.failed
                book.error = f"{type(e).__name__}: {str(e)[:400]}"
                _set_flags(book, ["generation_failed"])
                db.commit()
            log.exception("book.failed", book=book_id)
            raise


def redraw(book_id: str, beats: list[int]) -> dict[str, Any]:
    context.init_process()
    if _classic(book_id):
        from qamra_worker.jobs.classic import redraw_classic

        return redraw_classic(book_id, beats)
    if _class_copy(book_id):
        from qamra_worker.jobs.classbooks import copy_action

        return copy_action(book_id, beats)
    storage = context.storage()
    with context.db_session() as db:
        book = db.get(Book, book_id)
        if book is None:
            return {"status": "missing"}
        previous = book.status
        book.status = BookStatus.generating
        db.commit()
        try:
            return _run(lambda: redraw_pages(db, storage, book, beats))  # type: ignore[no-any-return]
        except Exception as e:
            db.rollback()
            book = db.get(Book, book_id)
            if book is not None:
                book.status = previous
                book.error = f"redraw: {type(e).__name__}: {str(e)[:400]}"
                db.commit()
            log.exception("book.redraw_failed", book=book_id)
            raise


def rerender(book_id: str) -> dict[str, Any]:
    """After text edits: rebuild the PDFs from the stored pages (no AI calls)."""
    context.init_process()
    if _classic(book_id):
        from qamra_worker.jobs.classic import rerender_classic

        return rerender_classic(book_id)
    if _class_copy(book_id):
        from qamra_worker.jobs.classbooks import copy_action

        return copy_action(book_id, [])
    storage = context.storage()
    with context.db_session() as db:
        book = db.get(Book, book_id)
        if book is None:
            return {"status": "missing"}

        return _run(lambda: rerender_book(db, storage, book))  # type: ignore[no-any-return]


async def rerender_book(db: Session, storage: ObjectStorage, book: Book) -> dict[str, Any]:
    """The PDFs again from what is stored: the pictures, `BookPage.text` and `Book.story` as staff left them
    in the review (no AI calls). The book returns to review (`in_review`) or to its preview."""
    job = await _setup(db, storage, book)
    character = db.get(Character, book.character_id) if book.character_id else None
    if character is None or not character.sheet_image_key:
        raise ValueError("character sheet missing")
    companion: CompanionSpec | None = default_companion(job.theme, book_lang(book))
    companion_sheet = drawing = None
    comp_row = db.get(Companion, book.companion_id) if book.companion_id else None
    if comp_row is not None and comp_row.sheet_key and comp_row.cleaned_key:
        companion, companion_sheet, drawing = await _companion(db, storage, job.rt, comp_row, book.art_style)
    return await render_files(
        job,
        str(book.generation.get("mode", "final")),
        StoryOut.model_validate(book.story),
        storage.get(character.sheet_image_key),
        companion,
        companion_sheet,
        drawing,
    )
