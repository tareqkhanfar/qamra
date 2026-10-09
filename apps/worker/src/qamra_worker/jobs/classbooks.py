"""«كتاب الصف» jobs (Addendum 1 §2, Addendum 4 §1C): one batch draws the whole class, then every copy's files.

- One RQ job per class: the shared pages (several children per picture, capped per provider), then every
  child's personal cover, then the print files of every copy and the combined print file.
- Resumable: a page already drawn for the same children stays; a retry only draws what is missing or what
  the school asked to redraw.
- Each child's copy is a `Book` with `generation.line = "class"`, so the admin review queue and print
  approval apply unchanged. It waits in `preview` until the school approves the class book.
- Costs: covers go to the child's book (`generation_costs`); shared pages carry the class book id in
  `units` and add up on the class book. One budget cap for the whole batch.
- Storage: shared pictures under the class prefix; covers and print files under each child's prefix, so a
  parent's "delete my child's data" removes that child's copy. Nothing here ever reads a child's photo.
"""

import asyncio
import dataclasses
import io
import math
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.cost import CostEntry, CostLedger
from qamra_ai.pipeline.budget import Budget, BudgetExceeded
from qamra_ai.pipeline.classbook import (
    ClassPicture,
    ClassTemplate,
    Kid,
    draw_picture,
    install_fakes,
    load_class_template,
    picture_request,
    print_version,
)
from qamra_ai.pipeline.layout import PrintSpec
from qamra_ai.pipeline.models import Gender, Lang
from qamra_ai.pipeline.printimg import downscale, fit_exact
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import load_theme
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Classroom,
    Companion,
    GenerationCost,
    Locale,
    Organization,
    PageStatus,
    SafetyStatus,
)
from qamra_core.db.models import Gender as ChildGender
from qamra_core.db.portal import ClassBook, ClassBookPage, ClassBookStatus
from qamra_pdf.classbook import (
    ChildCopy,
    ClassBookSpec,
    Classmate,
    SchoolPage,
    StoryPage,
    file_stem,
    render_class_book,
)
from qamra_pdf.lettering import DEFAULT_TITLE_STYLE
from qamra_worker import context
from qamra_worker.ai import ai_settings, make_runtime
from qamra_worker.jobs.books import CostSink, brand, file_key, page_key, resolved_settings
from qamra_worker.settings import get_settings

log = structlog.get_logger("qamra.worker.classbooks")
THUMB_PX = 520
PICTURES_PER_BUDGET = 20  # the per-book budget covers about 20 pictures (Addendum 3)
KEPT = (BookStatus.preview, BookStatus.in_review, BookStatus.approved)  # approvals an unchanged copy keeps


def class_prefix(cb: ClassBook) -> str:
    return f"orgs/{cb.organization_id}/classes/{cb.classroom_id}/book/"


def shared_key(cb: ClassBook, index: int, kind: str) -> str:
    ext = "png" if kind == "raw" else "jpg"
    return f"{class_prefix(cb)}{kind}/{index:02d}.{ext}"


def ready_characters(db: Session, cb: ClassBook) -> dict[str, tuple[Child, Character]]:
    """The class's children with a parent-approved character in the class book's style, by child id."""
    out: dict[str, tuple[Child, Character]] = {}
    children = db.scalars(select(Child).where(Child.classroom_id == cb.classroom_id)).all()
    for child in children:
        character = db.scalars(
            select(Character)
            .where(
                Character.child_id == child.id,
                Character.status == CharacterStatus.approved,
                Character.art_style == cb.art_style,
                Character.sheet_image_key.is_not(None),
            )
            .order_by(Character.approved_at.desc())
        ).first()
        if character is not None:
            out[str(child.id)] = (child, character)
    return out


@dataclass
class ClassSink:
    """Shared-page costs: one `generation_costs` row per call, tagged with the class book, summed on it."""

    db: Session
    cb: ClassBook

    def __call__(self, entry: CostEntry) -> None:
        usd = Decimal(str(round(entry.usd, 5)))
        self.db.add(
            GenerationCost(
                step=entry.step[:64],
                provider=entry.provider[:32],
                model=entry.model[:100],
                units={**entry.units, "class_book": str(self.cb.id)},
                usd=usd,
                estimated=entry.estimated,
            )
        )
        self.cb.cost_usd = (self.cb.cost_usd or Decimal("0")) + usd  # committed with the page


@dataclass
class ClassJob:
    db: Session
    storage: Any
    cb: ClassBook
    classroom: Classroom
    org: Organization
    template: ClassTemplate
    rt: Runtime
    spec: PrintSpec
    ready: dict[str, tuple[Child, Character]]
    sheets: dict[str, bytes] = field(default_factory=dict)
    redrawn_pages: set[int] = field(default_factory=set)  # drawn in this run: every copy changed
    redrawn_covers: set[str] = field(default_factory=set)  # child ids whose cover was drawn in this run

    @property
    def lang(self) -> Lang:
        return "ar" if self.cb.language == "ar" else "en"

    def kid(self, child_id: str) -> Kid:
        child, character = self.ready[child_id]
        if child_id not in self.sheets:
            self.sheets[child_id] = self.storage.get(str(character.sheet_image_key))
        return Kid(
            child_id,
            child.first_name,
            _gender(child),
            max(2, min(12, date.today().year - child.birth_year)),
            child.wears_hijab,
            child.wears_glasses,
            self.sheets[child_id],
        )

    def progress(self, **parts: Any) -> None:
        self.cb.progress = {**(self.cb.progress or {}), **parts}
        self.db.commit()


def _gender(child: Child) -> Gender:
    return "f" if child.gender == ChildGender.f else "m"


def _theme_cover(slug: str) -> tuple[str, tuple[int, int] | None]:
    """The class book's theme: its cover lettering and its ages (the default lettering when the class
    template has no story theme of the same name)."""
    try:
        theme = load_theme(slug)
    except (OSError, ValueError):
        return DEFAULT_TITLE_STYLE, None
    return theme.cover_title_style, (theme.age_range[0], theme.age_range[1])


def _seed(cb: ClassBook) -> int:
    gen = dict(cb.generation or {})
    if "seed" not in gen:
        gen["seed"] = uuid.uuid4().int % 2_000_000_000
        cb.generation = gen
    return int(gen["seed"])


def _setup(db: Session, storage: Any, cb: ClassBook) -> ClassJob:
    classroom = db.get(Classroom, cb.classroom_id)
    org = db.get(Organization, cb.organization_id)
    if classroom is None or org is None:
        raise ValueError("class book without its class or school")
    template = load_class_template(str((cb.plan or {}).get("template") or ""))
    settings = ai_settings(
        resolved_settings(db), get_settings(), offline=(cb.generation or {}).get("offline") or False
    )
    rt = make_runtime(settings)
    install_fakes(rt)
    spec = PrintSpec.from_settings(settings)
    ready = ready_characters(db, cb)
    included = [c for c in (cb.plan or {}).get("children", []) if c in ready]
    pictures = len((cb.plan or {}).get("pages", [])) + len(included)
    cap = float(settings.book_budget_usd) * max(1.0, pictures / PICTURES_PER_BUDGET)
    rt.budget = Budget(cap_usd=round(cap, 2))  # per run: a resumed batch only draws what is missing
    _seed(cb)
    cb.generation = {**(cb.generation or {}), "budget_usd": round(cap, 2), "models": {"image": rt.image.name}}
    db.commit()
    return ClassJob(db, storage, cb, classroom, org, template, rt, spec, {c: ready[c] for c in included})


def _store(storage: Any, key: str, data: bytes, mime: str) -> str:
    storage.put(key, data, mime)
    return key


async def _draw_shared(job: ClassJob, page: dict[str, Any], sem: asyncio.Semaphore) -> None:
    db, cb = job.db, job.cb
    index, key = int(page["index"]), str(page["key"])
    kids_ids = [c for c in page.get("children", []) if c in job.ready]
    names = [job.ready[c][0].first_name for c in kids_ids]
    text = job.template.page_text(key, job.lang, names, job.classroom.name)
    row = db.scalars(
        select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id, ClassBookPage.index == index)
    ).first()
    same = row is not None and row.scene_key == key and list(row.child_ids or []) == kids_ids
    if row is not None and same and row.print_image_key and not row.redraw:
        row.text = text  # a renamed class or child changes only the words
        db.commit()
        return
    row = row or ClassBookPage(class_book_id=cb.id, index=index, scene_key=key)
    manual = same and bool(row.redraw)  # the school's "redraw": one new attempt with the same children
    scene = job.template.scene(key)
    seed = _seed(cb)
    async with sem:
        kids = [job.kid(c) for c in kids_ids]
        rt = dataclasses.replace(job.rt, on_cost=ClassSink(db, cb), ledger=CostLedger())
        pic = await draw_picture(
            rt,
            lambda n: picture_request(
                job.template,
                scene,
                kids,
                cb.art_style,
                kind="page",
                step=f"class:{index}:a{n}",
                seed=(seed + index * 101 + n * 7) % 2_147_483_647,
                resolution=rt.settings.final_resolution,
            ),
            kids,
            scene.scene,
            label=f"class:{index}",
            first_attempt=len(row.attempts or []) + 1,
            manual=manual,
        )
        printed = None
        if pic.image is not None:
            printed, more = await print_version(
                rt, pic.image.data, label=f"class:{index}", px=job.spec.page_px[0], dpi=job.spec.dpi
            )
            pic.flags += more
    _save_shared(job, row, pic, printed, kids_ids, text)
    if pic.image is not None:
        job.redrawn_pages.add(index)


def _save_shared(
    job: ClassJob,
    row: ClassBookPage,
    pic: ClassPicture,
    printed: bytes | None,
    kids_ids: list[str],
    text: str,
) -> None:
    db, cb, storage = job.db, job.cb, job.storage
    row.attempts = [*(row.attempts or []), *pic.attempts]
    row.redraw = False
    if pic.image is None or printed is None:
        if not row.image_key:  # keep an earlier picture when a redraw fails
            row.status, row.flags, row.child_ids, row.text = PageStatus.failed, pic.flags, kids_ids, text
        if row.id is None:
            db.add(row)
        db.commit()
        return
    row.image_key = _store(storage, shared_key(cb, row.index, "raw"), pic.image.data, pic.image.mime)
    row.print_image_key = _store(storage, shared_key(cb, row.index, "print"), printed, "image/jpeg")
    _store(storage, shared_key(cb, row.index, "thumb"), downscale(pic.image.data, THUMB_PX, 82), "image/jpeg")
    row.status = PageStatus.ok if pic.status == "ok" else PageStatus.needs_review
    row.flags = list(pic.flags)
    row.child_ids, row.text = kids_ids, text
    row.qa = {
        "unrecognized": pic.unrecognized,
        "checks": [c.model_dump() for c in pic.qa.children] if pic.qa else [],
        "safe": pic.qa.safe if pic.qa else None,
    }
    if row.id is None:
        db.add(row)
    db.commit()


def copy_book(db: Session, cb: ClassBook, child: Child) -> Book | None:
    return db.scalars(
        select(Book).where(Book.child_id == child.id, Book.generation["class_book_id"].astext == str(cb.id))
    ).first()


def _copy_for(job: ClassJob, child: Child, character: Character) -> Book:
    """Each child's own copy: a `Book` the admin review queue and print approval know."""
    db, cb = job.db, job.cb
    book = copy_book(db, cb, child)
    title = f"{child.first_name} — {job.template.title(job.lang, job.classroom.name)}"
    if book is None:
        book = Book(
            child_id=child.id,
            character_id=character.id,
            theme_id=cb.theme_id,
            theme_version=job.template.version,
            language=Locale(cb.language),
            art_style=cb.art_style,
            status=BookStatus.generating,
            title=title[:200],
            budget_usd=Decimal(str(job.rt.settings.book_budget_usd)),
            generation={
                "line": "class",
                "class_book_id": str(cb.id),
                "class_line": cb.line,
                "classroom_id": str(cb.classroom_id),
                "organization_id": str(cb.organization_id),
            },
        )
        db.add(book)
        db.flush()
    book.title = title[:200]
    if book.character_id != character.id:  # the parent approved a new drawing: a new cover
        book.character_id = character.id
        for old in db.scalars(select(BookPage).where(BookPage.book_id == book.id)).all():
            old.print_image_key = None
    book.status = BookStatus.generating
    db.commit()
    return book


async def _draw_cover(job: ClassJob, child_id: str, sem: asyncio.Semaphore) -> None:
    db, cb = job.db, job.cb
    child, character = job.ready[child_id]
    existing = copy_book(db, cb, child)
    row = (
        db.scalars(select(BookPage).where(BookPage.book_id == existing.id, BookPage.index == 0)).first()
        if existing is not None
        else None
    )
    unchanged = (
        existing is not None
        and row is not None
        and bool(row.print_image_key)
        and existing.character_id == character.id
        and not (row.review or {}).get("redraw")
    )
    if unchanged:
        return  # nothing new for this child: the copy keeps its approvals
    book = _copy_for(job, child, character)
    row = db.scalars(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 0)).first()
    row = row or BookPage(book_id=book.id, index=0, layout="cover")
    if row.id is None:
        db.add(row)
        db.commit()
    seed = _seed(cb)
    async with sem:
        kid = job.kid(child_id)
        rt = dataclasses.replace(job.rt, on_cost=CostSink(db, book, child.id), ledger=CostLedger())
        pic = await draw_picture(
            rt,
            lambda n: picture_request(
                job.template,
                job.template.cover,
                [kid],
                cb.art_style,
                kind="cover",
                step=f"cover:a{n}",
                seed=(seed + 7919 * (1 + sorted(job.ready).index(child_id)) + n * 7) % 2_147_483_647,
                resolution=rt.settings.final_resolution,
            ),
            [kid],
            job.template.cover.scene,
            label="cover",
            first_attempt=len(row.attempts or []) + 1,
            manual=bool((row.review or {}).get("redraw")),
        )
        printed = None
        if pic.image is not None:
            printed, more = await print_version(
                rt, pic.image.data, label="cover", px=job.spec.page_px[0], dpi=job.spec.dpi
            )
            pic.flags += more
    row.attempts = [*(row.attempts or []), *pic.attempts]
    row.review = {**(row.review or {}), "redraw": False}
    if pic.image is not None and printed is not None:
        row.image_key = _store(job.storage, page_key(book, 0, "raw"), pic.image.data, pic.image.mime)
        row.print_image_key = _store(job.storage, page_key(book, 0, "print"), printed, "image/jpeg")
        _store(job.storage, page_key(book, 0, "thumb"), downscale(pic.image.data, THUMB_PX, 82), "image/jpeg")
        row.status = PageStatus.ok if pic.status == "ok" else PageStatus.needs_review
        row.safety_status = SafetyStatus.passed
        job.redrawn_covers.add(child_id)
    elif not row.print_image_key:
        row.status = PageStatus.failed
    row.flags = list(pic.flags)
    row.qa = {"unrecognized": pic.unrecognized}
    db.commit()


# ---- print files ------------------------------------------------------------------------------------

MEMORIES = {"ar": "ذِكْرَيَاتِي مَعَ أَصْدِقَائِي", "en": "Memories with my friends"}
FACE_MM, PORTRAIT_MM, COMPANION_MM = 38.0, 124.0, 34.0
LOGO_MM, CLASS_PHOTO_MM = (60.0, 24.0), (150.0, 88.0)


def _px(spec: PrintSpec, mm: float) -> int:
    """Pixels for `mm` at the print DPI, rounded up (+1) so preflight never sees 299.5 DPI."""
    return math.ceil(mm / 25.4 * spec.dpi) + 1


def _front_view(sheet: bytes) -> Image.Image:
    """The character sheet shows three views side by side; the first is the front view."""
    with Image.open(io.BytesIO(sheet)) as im:
        img = im.convert("RGB")
    w, h = img.size
    return img.crop((0, 0, max(1, w // 3), h)) if w > h else img


def _jpeg(img: Image.Image, dpi: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, dpi=(dpi, dpi))
    return buf.getvalue()


def _face(sheet: bytes, spec: PrintSpec) -> bytes:
    front = _front_view(sheet)
    w, h = front.size
    head = front.crop((0, 0, w, max(1, min(h, round(w * 1.05)))))  # head and shoulders
    return fit_exact(_jpeg(head, spec.dpi), (_px(spec, FACE_MM), _px(spec, FACE_MM)), dpi=spec.dpi)


def _portrait(sheet: bytes, spec: PrintSpec) -> bytes:
    front = _front_view(sheet)
    h_px = _px(spec, PORTRAIT_MM)
    w_px = max(1, round(front.size[0] * h_px / front.size[1]))
    return _jpeg(front.resize((w_px, h_px), Image.Resampling.LANCZOS), spec.dpi)


def _contain(data: bytes, box: tuple[int, int]) -> bytes:
    """A logo scaled to fill its print box at full resolution, transparency kept."""
    with Image.open(io.BytesIO(data)) as im:
        img = im.convert("RGBA")
    scale = min(box[0] / img.size[0], box[1] / img.size[1])
    img = img.resize(
        (max(1, round(img.size[0] * scale)), max(1, round(img.size[1] * scale))), Image.Resampling.LANCZOS
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def _unique_stems(stems: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for stem in stems:
        seen[stem] = seen.get(stem, 0) + 1
        out.append(stem if seen[stem] == 1 else f"{stem}-{seen[stem]}")
    return out


def _school_page(job: ClassJob, d: Path) -> SchoolPage:
    cb, org, storage, spec = job.cb, job.org, job.storage, job.spec
    logo = photo = None
    if org.logo_key:
        box = (_px(spec, LOGO_MM[0]), _px(spec, LOGO_MM[1]))
        logo = _write(d / "logo.png", _contain(storage.get(org.logo_key), box))
    if cb.class_photo_key and cb.class_photo_consent_at:
        size = (_px(spec, CLASS_PHOTO_MM[0]), _px(spec, CLASS_PHOTO_MM[1]))
        photo = _write(d / "class-photo.jpg", fit_exact(storage.get(cb.class_photo_key), size, dpi=spec.dpi))
    return SchoolPage(
        title=job.template.title(job.lang, job.classroom.name),
        school=org.name,
        year=job.classroom.school_year,
        teacher_title=job.template.teacher_title_ar if job.lang == "ar" else job.template.teacher_title_en,
        teacher_message=cb.teacher_message,
        teacher_name=job.classroom.teacher_name,
        logo=logo,
        class_photo=photo,
    )


def _companion_art(db: Session, child: Child) -> Companion | None:
    return db.scalars(
        select(Companion)
        .where(
            Companion.child_id == child.id,
            Companion.approved_at.is_not(None),
            Companion.sheet_key.is_not(None),
        )
        .order_by(Companion.approved_at.desc())
    ).first()


async def render_files(job: ClassJob) -> dict[str, Any]:
    """Every copy's interior and cover, the combined print file, preflight; copies wait for the school."""
    db, cb, storage, spec, lang = job.db, job.cb, job.storage, job.spec, job.lang
    rows = db.scalars(
        select(ClassBookPage).where(ClassBookPage.class_book_id == cb.id).order_by(ClassBookPage.index)
    ).all()
    planned = [int(p["index"]) for p in (cb.plan or {}).get("pages", [])]
    rows = [r for r in rows if r.index in planned]
    if len(rows) != len(planned) or any(not r.print_image_key for r in rows):
        return {"status": "pages_missing"}
    members = sorted(job.ready, key=lambda c: job.ready[c][0].first_name)
    books = {c: copy_book(db, cb, job.ready[c][0]) for c in members}
    covers: dict[str, str] = {}
    for c, b in books.items():
        cover = (
            db.scalars(select(BookPage).where(BookPage.book_id == b.id, BookPage.index == 0)).first()
            if b
            else None
        )
        if cover is not None and cover.print_image_key:
            covers[c] = cover.print_image_key
    done = [c for c in members if c in covers]
    names = [job.ready[c][0].first_name for c in done]
    stems = _unique_stems([file_stem(job.org.name, job.classroom.name, n) for n in names])
    with tempfile.TemporaryDirectory(prefix="qamra-class-") as tmp:
        d = Path(tmp)
        story = [
            StoryPage(_write(d / f"p{r.index:02d}.jpg", storage.get(str(r.print_image_key))), r.text or "")
            for r in rows
        ]
        mates = [
            Classmate(job.ready[c][0].first_name, _write(d / f"face-{i}.jpg", _face(job.kid(c).sheet, spec)))
            for i, c in enumerate(members)
        ]
        copies = []
        for i, (c, stem) in enumerate(zip(done, stems, strict=True)):
            child = job.ready[c][0]
            comp = _companion_art(db, child)
            copies.append(
                ChildCopy(
                    stem=stem,
                    name=child.first_name,
                    cover_image=_write(d / f"cover-{i}.jpg", storage.get(covers[c])),
                    portrait=_write(d / f"portrait-{i}.jpg", _portrait(job.kid(c).sheet, spec)),
                    portrait_line=job.template.portrait_line(lang, i, _gender(child), child.first_name),
                    companion=_write(
                        d / f"companion-{i}.jpg",
                        fit_exact(
                            storage.get(str(comp.sheet_key)), (_px(spec, COMPANION_MM),) * 2, dpi=spec.dpi
                        ),
                    )
                    if comp
                    else None,
                    companion_name=comp.name if comp else None,
                    gender=_gender(child),
                )
            )
        title_style, ages = _theme_cover(job.template.slug)
        book_spec = ClassBookSpec(
            lang=lang,
            brand=brand(),
            title=job.template.title(lang, job.classroom.name),
            cover_subtitle=job.template.cover_subtitle(lang, job.classroom.name),
            blurb=job.template.blurb(lang, job.classroom.name),
            portrait_title=job.template.portrait_title_ar if lang == "ar" else job.template.portrait_title_en,
            group_title=job.template.group_title(lang, job.classroom.name),
            school=_school_page(job, d),
            pages=story,
            classmates=mates,
            memories_title=MEMORIES[lang],
            trim_mm=spec.trim_mm,
            bleed_mm=spec.bleed_mm,
            safe_mm=spec.safe_mm,
            spine_mm=spec.spine_mm,
            signature=spec.signature,
            dpi=spec.dpi,
            title_style=title_style,
            age_range=ages,
        )
        book_spec = dataclasses.replace(book_spec, spine_mm=spec.spine_for(book_spec.interior_pages))
        job.progress(stage="files", files={"done": 0, "total": len(copies)})
        files = await render_class_book(
            book_spec,
            copies,
            d / "out",
            on_copy=lambda i: job.progress(files={"done": i + 1, "total": len(copies)}),
        )
        combined = _store(
            storage, f"{class_prefix(cb)}files/combined.pdf", files.combined.read_bytes(), "application/pdf"
        )
        listed = []
        for c, copy in zip(done, copies, strict=True):
            book = books[c]
            assert book is not None  # nosec B101 (a cover implies its book)
            book.pdf_interior_key = _store(
                storage,
                file_key(book, "interior.pdf"),
                files.interiors[copy.stem].read_bytes(),
                "application/pdf",
            )
            book.pdf_cover_key = _store(
                storage, file_key(book, "cover.pdf"), files.covers[copy.stem].read_bytes(), "application/pdf"
            )
            book.preflight = {k: v.to_dict() for k, v in files.preflight[copy.stem].items()}
            _copy_review(job, book, c, rows, files.passed(copy.stem))
            listed.append({"child_id": c, "book_id": str(book.id), "stem": copy.stem, "name": copy.name})
    cb.bundle = {
        "combined_key": combined,
        "rendered_at": datetime.now(UTC).isoformat(),
        "school": job.org.name,
        "class": job.classroom.name,
        "stem": file_stem(job.org.name, job.classroom.name),
        "copies": listed,
        "overflow_pages": files.overflow_pages,
    }
    db.commit()
    return {"status": "rendered", "copies": len(listed)}


def _copy_review(job: ClassJob, book: Book, child_id: str, rows: list[ClassBookPage], passed: bool) -> None:
    """Per-child coverage for the review queue (Addendum 1 §2): appearances, and pages where the check
    couldn't recognize the child. The copy then waits for the school's approval."""
    cb = job.cb
    on = [r.index for r in rows if child_id in (r.child_ids or [])]
    missed = [r.index for r in rows if child_id in ((r.qa or {}).get("unrecognized") or [])]
    cover = job.db.scalars(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 0)).first()
    cover_review = cover is not None and cover.status == PageStatus.needs_review
    book.qa_summary = {
        "class_book": str(cb.id),
        "appearances": len(on),
        "recognized": len(on) - len(missed),
        "min_appearances": cb.min_appearances,
        "pages": on,
        "unrecognized_pages": missed,
        "needs_review": len(missed) + int(cover_review),
        "failed": 0,
    }
    flags = [
        name
        for name, bad in (
            ("class_face", bool(missed) or cover_review),
            ("coverage_low", cb.line == "magic" and len(on) - len(missed) < cb.min_appearances),
            ("preflight_failed", not passed),
        )
        if bad
    ]
    book.flags = flags
    changed = bool(job.redrawn_pages) or child_id in job.redrawn_covers or book.status not in KEPT
    if (
        changed
    ):  # the school approves the class first (then the admin review queue); unchanged copies keep theirs
        book.status = BookStatus.in_review if cb.school_approved_at else BookStatus.preview
    book.error = None


async def _all(tasks: list[Any]) -> None:
    """Run the tasks; a budget stop wins over other errors, and one failed picture never stops the others."""
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, BaseException)]
    budget = [e for e in errors if isinstance(e, BudgetExceeded)]
    if budget:
        raise budget[0]
    if errors:
        raise errors[0]


async def run_class_book(
    db: Session, storage: Any, cb: ClassBook, *, keep_status: ClassBookStatus | None = None
) -> dict[str, Any]:
    """The whole batch. `keep_status`: an admin's redraw of one copy leaves the class where it was."""
    job = _setup(db, storage, cb)
    sem = asyncio.Semaphore(max(1, job.rt.settings.image_concurrency))
    pages = list((cb.plan or {}).get("pages", []))
    counts = {"pages": 0, "covers": 0}
    job.progress(
        stage="pages", pages={"done": 0, "total": len(pages)}, covers={"done": 0, "total": len(job.ready)}
    )

    async def one_page(page: dict[str, Any]) -> None:
        await _draw_shared(job, page, sem)
        counts["pages"] += 1
        job.progress(pages={"done": counts["pages"], "total": len(pages)})

    async def one_cover(child_id: str) -> None:
        await _draw_cover(job, child_id, sem)
        counts["covers"] += 1
        job.progress(covers={"done": counts["covers"], "total": len(job.ready)})

    try:
        await _all([one_page(p) for p in pages])
        job.progress(stage="covers")
        await _all([one_cover(c) for c in sorted(job.ready)])
    except BudgetExceeded:
        cb.flags = list(dict.fromkeys([*(cb.flags or []), "budget_exceeded"]))
        cb.status = ClassBookStatus.failed
        cb.error = "budget_exceeded"
        db.commit()
        return {"status": "budget_exceeded"}
    result = await render_files(job)
    if result["status"] != "rendered":
        cb.status, cb.error = ClassBookStatus.failed, result["status"]
        cb.flags = list(dict.fromkeys([*(cb.flags or []), "pages_missing"]))
        db.commit()
        return result
    cb.status, cb.error = keep_status or ClassBookStatus.review, None
    cb.flags = [
        f for f in (cb.flags or []) if f not in ("budget_exceeded", "pages_missing", "generation_failed")
    ]
    job.progress(stage="done")
    db.add(
        AuditLog(
            action="class_book.generated",
            entity_type="class_book",
            entity_id=str(cb.id),
            data={"copies": result["copies"], "pages": len(pages), "cost_usd": float(cb.cost_usd or 0)},
        )
    )
    db.commit()
    log.info("class_book.ready", class_book=str(cb.id), copies=result["copies"], cost=float(cb.cost_usd or 0))
    return {**result, "status": cb.status.value}


def generate_class_book(class_book_id: str) -> dict[str, Any]:
    """RQ entry point (enqueued by the portal's «ارسم كتب الصف»)."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        cb = db.get(ClassBook, uuid.UUID(class_book_id))
        if cb is None:
            return {"status": "missing"}
        try:
            return asyncio.run(run_class_book(db, storage, cb))
        except Exception as e:
            db.rollback()
            cb = db.get(ClassBook, uuid.UUID(class_book_id))
            if cb is not None:
                cb.status = ClassBookStatus.failed
                cb.error = f"{type(e).__name__}: {str(e)[:400]}"
                cb.flags = list(dict.fromkeys([*(cb.flags or []), "generation_failed"]))
                db.commit()
            log.exception("class_book.failed", class_book=class_book_id)
            raise


def copy_action(book_id: str, beats: list[int]) -> dict[str, Any]:
    """The admin review queue's generate / redraw / re-render on one child's class copy (dispatched from
    `jobs.books`): a new cover when beat 0 is asked, then the class's files again, inside the class batch, so
    a copy never turns into a single-hero book. The class and the other copies keep their approvals."""
    context.init_process()
    storage = context.storage()
    with context.db_session() as db:
        book = db.get(Book, uuid.UUID(book_id))
        cb_id = (book.generation or {}).get("class_book_id") if book else None
        cb = db.get(ClassBook, uuid.UUID(str(cb_id))) if cb_id else None
        if book is None or cb is None:
            return {"status": "missing"}
        cover = db.scalars(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == 0)).first()
        if 0 in beats and cover is not None:
            cover.review = {**(cover.review or {}), "redraw": True}
        previous = cb.status
        cb.status = ClassBookStatus.generating
        db.commit()
        try:
            return asyncio.run(run_class_book(db, storage, cb, keep_status=previous))
        except Exception:
            db.rollback()
            cb = db.get(ClassBook, cb.id)
            if cb is not None:
                cb.status = previous
                db.commit()
            log.exception("class_copy.failed", book=book_id)
            raise
