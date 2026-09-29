"""Classic jobs end to end with offline providers: templates (generated and from a sample book), the identity
portrait, hero edits, the preview and the final book, redraws, the budget stop and a missing template."""

import io
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from qamra_ai.config import Settings as AISettings
from qamra_ai.cost import CostEntry, fal_cost
from qamra_ai.image.base import GeneratedImage, ImageRequest
from qamra_ai.pipeline.fakes import default_fake_text_provider
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.pipeline.theme import CONTENT_DIR, Theme
from qamra_core.db.classic import ChildPortrait, ClassicTemplate, ClassicTemplatePage, TemplateStatus
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    Gender,
    GenerationCost,
    Locale,
    PageStatus,
    PhotoStatus,
    User,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectStorage
from qamra_worker.jobs import classic as jobs
from qamra_worker.jobs.classic import (
    classic_book_flow,
    classic_redraw_pages,
    classic_rerender,
    ensure_texts,
    run_template_from_book,
    run_template_job,
    setup_classic,
    template_pages,
)

FIXTURE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
KLEIN = "fal-ai/flux-2/klein/4b/edit"


def _theme(db: Session, slug: str = "graduation") -> ThemeRow:
    raw = yaml.safe_load((CONTENT_DIR / f"themes/{slug}/theme.yaml").read_text(encoding="utf-8"))
    row = ThemeRow(
        slug=slug, version=raw["version"], title_ar="t", title_en="t", age_min=5, age_max=6,
        companion_slot=True, definition=raw,
    )  # fmt: skip
    db.add(row)
    db.flush()
    return row


def _template(db: Session, theme: ThemeRow, variant: str = "girl_hijab", **kw: Any) -> ClassicTemplate:
    t = ClassicTemplate(
        theme_id=theme.id,
        theme_version=theme.version,
        art_style="watercolor",
        variant=variant,
        generation={"theme_def": theme.definition, "offline": "fake"},
        **kw,
    )
    db.add(t)
    db.commit()
    return t


def _child(db: Session, storage: ObjectStorage, *, hijab: bool = True, sample: bool = False) -> Child:
    user = User(email=f"p{id(db)}{hijab}{sample}@example.com", full_name="P")
    db.add(user)
    db.flush()
    child = Child(
        guardian_user_id=user.id, first_name="ليان", gender=Gender.f, birth_year=2021, wears_hijab=hijab,
        is_sample=sample,
    )  # fmt: skip
    db.add(child)
    db.flush()
    key = f"children/{child.id}/photos/p1.jpg"
    storage.put(key, FIXTURE.read_bytes(), "image/png")
    db.add(ChildPhoto(child_id=child.id, storage_key=key, status=PhotoStatus.accepted))
    db.commit()
    return child


def _book(db: Session, theme: ThemeRow, child: Child, *, lang: Locale = Locale.ar, **gen: Any) -> Book:
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=theme.version,
        language=lang,
        art_style="watercolor",
        status=BookStatus.generating,
        is_sample=child.is_sample,
        generation={"line": "classic", "offline": "fake", **gen},
    )
    db.add(book)
    db.commit()
    return book


def _pages(db: Session, book: Book) -> dict[int, BookPage]:
    return {p.index: p for p in db.scalars(select(BookPage).where(BookPage.book_id == book.id))}


async def test_a_generated_template(db: Session, storage: ObjectStorage) -> None:
    theme = _theme(db)
    t = _template(db, theme)
    result = await run_template_job(db, storage, t)
    assert result["status"] == "in_review" and result["missing"] == [], (result, t.flags, t.error)
    pages = template_pages(db, t)
    assert sorted(pages) == list(range(18))
    assert all(p.image_key and p.preview_key and storage.exists(p.image_key) for p in pages.values())
    assert pages[7].has_hero is False and pages[7].hero_box is None  # the empty hall: no hero
    assert pages[1].hero_box == {"x": 0.3, "y": 0.3, "w": 0.35, "h": 0.6}  # the fake vision model's box
    assert pages[4].text_box is None and pages[1].text_box and pages[1].text_box["area"] == "top"
    assert t.generation["placeholder_key"] and t.generation["seed"]
    steps = {
        c.step.split(":")[1]
        for c in db.scalars(select(GenerationCost).where(GenerationCost.book_id.is_(None)))
    }
    assert {"placeholder", "cover", "page", "qa"} <= steps  # one-time costs, logged as tpl:<step>
    with Image.open(io.BytesIO(storage.get(pages[3].image_key or ""))) as spread:
        assert spread.size == (5031, 2551)  # print resolution with bleed

    again = await run_template_job(db, storage, t, beats=[5])  # one manual redraw
    assert again["status"] == "in_review" and template_pages(db, t)[5].regen_count == 1

    # the Arabic words, vowelized once for the variant's gender and cached by their hash
    texts = t.generation["texts"]
    assert texts["gender"] == "f" and texts["hash"] and texts["kept"] == []
    assert "tpl:vowelize:f" in {c.step for c in db.scalars(select(GenerationCost))}
    sibling = _template(db, theme, "girl")  # another look of the same gender: the words are lent, no call
    text_rt = Runtime(
        settings=AISettings(_env_file=None), text=default_fake_text_provider(), image=PricedEdits()
    )  # type: ignore[call-arg]
    await ensure_texts(db, text_rt, sibling)
    assert sibling.generation["texts"]["hash"] == texts["hash"] and text_rt.text.calls == []  # type: ignore[attr-defined]


async def test_a_template_from_an_approved_sample_book(db: Session, storage: ObjectStorage) -> None:
    theme = _theme(db, "first-day")
    child = _child(db, storage, hijab=False, sample=True)
    sheet_key = f"children/{child.id}/characters/sheet.png"
    storage.put(sheet_key, FIXTURE.read_bytes(), "image/png")
    character = Character(
        child_id=child.id, art_style="watercolor", status=CharacterStatus.approved, sheet_image_key=sheet_key
    )
    db.add(character)
    db.flush()
    book = Book(
        child_id=child.id, character_id=character.id, theme_id=theme.id, theme_version=theme.version,
        language=Locale.ar, art_style="watercolor", status=BookStatus.approved, is_sample=True,
        generation={"theme_def": theme.definition, "seed": 5, "outfits": {"day": "x"}},
        cost_usd=Decimal("1.9"),
    )  # fmt: skip
    db.add(book)
    db.flush()
    plan = plan_book(Theme.model_validate(theme.definition), "ar", companion_page=False)
    for beat in plan.beats:
        key = f"children/{child.id}/books/{book.id}/print/{beat:02d}.jpg"
        buf = io.BytesIO()
        Image.new("RGB", (300, 300), "#406080").save(buf, format="JPEG")
        storage.put(key, buf.getvalue(), "image/jpeg")
        db.add(
            BookPage(book_id=book.id, index=beat, print_image_key=key, image_key=key, status=PageStatus.ok)
        )
    db.commit()
    t = _template(db, theme, "girl", source="sample_book", source_book_id=book.id)
    result = await run_template_from_book(db, storage, t, book)
    assert result["status"] == "in_review" and result["missing"] == []
    pages = template_pages(db, t)
    assert len(pages) == len(plan.beats) and all(p.image_key and p.preview_key for p in pages.values())
    assert all(p.hero_box for p in pages.values() if p.has_hero)
    assert t.generation["source_cost_usd"] == 1.9 and t.generation["seed"] == 5
    assert not any(k.startswith(f"children/{child.id}") for p in pages.values() for k in [p.image_key or ""])


async def _live_template(
    db: Session, storage: ObjectStorage, theme: ThemeRow, variant: str
) -> ClassicTemplate:
    t = _template(db, theme, variant)
    await run_template_job(db, storage, t)
    t.status = TemplateStatus.live
    db.commit()
    return t


async def test_a_classic_book_preview_then_final(db: Session, storage: ObjectStorage) -> None:
    theme = _theme(db)
    t = await _live_template(db, storage, theme, "girl_hijab")
    words = t.generation["texts"]["texts"]
    words["pages"][0]["text"] = words["pages"][0]["text"].replace("اليوم", "اَلْيَوْمَ")  # as the model would
    t.generation = {**t.generation, "texts": {**t.generation["texts"], "texts": words}}
    db.commit()
    child = _child(db, storage)
    book = _book(db, theme, child)
    result = await classic_book_flow(db, storage, book, "preview")
    assert result["status"] == "preview", (result, book.error, book.flags)
    db.refresh(book)
    assert book.generation["template_id"] == str(t.id) and book.budget_usd == Decimal("0.54")  # 2₪ / 3.70
    pages = _pages(db, book)
    previewed = sorted(b for b, p in pages.items() if p.preview_image_key)
    assert previewed == [0, 1, 2]  # the cover and the first two hero pages
    assert all(storage.exists(pages[b].print_image_key or "") for b in previewed)
    assert book.proof_pdf_key and not book.pdf_interior_key
    assert pages[1].text and "ليان" in pages[1].text and pages[1].text == pages[1].original_text
    assert pages[1].text.startswith("اَلْيَوْمَ") and "text_not_vowelized" not in book.flags  # vowelized once
    portrait = db.scalar(select(ChildPortrait).where(ChildPortrait.child_id == child.id))
    assert portrait is not None and portrait.image_key.startswith(f"children/{child.id}/")
    assert portrait.source == "photo"
    photos = db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == child.id)).all()
    assert all(p.delete_after is not None for p in photos)  # the photo did its job: deletion scheduled

    book.generation = {**book.generation, "final_requested": True}  # the order was confirmed meanwhile
    db.commit()
    result = await classic_book_flow(db, storage, book, "preview")
    assert result["status"] == "in_review", (result, book.error, book.flags)
    db.refresh(book)
    pages = _pages(db, book)
    assert sorted(pages) == list(range(18)) and all(p.print_image_key for p in pages.values())
    assert "template_page" in pages[7].flags and pages[7].qa == {}  # no hero: the template as it is
    assert pages[1].status == PageStatus.ok and pages[1].qa["likeness"] == 9
    assert len(pages[1].attempts) == 1  # the preview's edit was reused, not redrawn
    assert book.pdf_interior_key and book.pdf_cover_key
    assert book.preflight["interior"]["passed"] and book.preflight["cover"]["passed"]
    steps = {
        c.step.split(":")[0]
        for c in db.scalars(select(GenerationCost).where(GenerationCost.book_id == book.id))
    }
    assert {"portrait", "hero", "qa"} <= steps

    redone = await classic_redraw_pages(db, storage, book, [2, 7])  # page 7 has no hero: nothing to redo
    assert redone["redrawn"] == [2] and redone["status"] == "in_review"
    page2 = _pages(db, book)[2]
    assert (
        page2.regen_count == 1
        and page2.attempts[-1]["why"] == "manual"
        and page2.attempts[-1]["attempt"] == 2
    )

    page3 = _pages(db, book)[3]
    page3.text, page3.flags = "نصّ جديد كتبه الأهل.", ["parent_edited"]
    db.commit()
    again = await classic_rerender(db, storage, book)
    assert again["status"] == "in_review" and book.generation["text_review"]["safe"] is True


async def test_an_english_book_uses_the_mirrored_template(db: Session, storage: ObjectStorage) -> None:
    theme = _theme(db)
    t = _template(db, theme, "girl_hijab", status=TemplateStatus.live)
    book = _book(db, theme, _child(db, storage), lang=Locale.en)
    job = setup_classic(db, storage, book)
    assert job.mirrored and job.template.id == t.id


async def test_no_template_means_a_clear_flag(db: Session, storage: ObjectStorage) -> None:
    theme = _theme(db)
    _template(db, theme, "boy", status=TemplateStatus.live)  # another look only
    book = _book(db, theme, _child(db, storage))
    result = await classic_book_flow(db, storage, book, "preview")
    assert result["status"] == "template_missing"
    assert book.status == BookStatus.failed and "template_missing" in book.flags


class PricedEdits:
    """klein on fal, priced as the adapter prices it (output + references, each at most 1 MP)."""

    name, model = "fal", KLEIN

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        w, h = req.size or (512, 512)
        buf = io.BytesIO()
        Image.new("RGB", (w, h), "#c08060").save(buf, format="PNG")
        in_mp = 0.0
        for ref in req.refs:
            with Image.open(io.BytesIO(ref.data)) as im:
                in_mp += min(1.0, im.size[0] * im.size[1] / 1024**2)
        usd = fal_cost(KLEIN, out_px=(w, h), in_megapixels=in_mp) or 0.0
        return GeneratedImage(buf.getvalue(), "image/png", CostEntry(req.step, "fal", KLEIN, {}, usd))


def _small_template(db: Session, storage: ObjectStorage, theme: ThemeRow, variant: str) -> ClassicTemplate:
    """A live template with small stored pages (fast; not print quality)."""
    t = _template(db, theme, variant, status=TemplateStatus.live)
    plan = plan_book(Theme.model_validate(theme.definition), "ar", companion_page=False)
    for beat, bp in plan.beats.items():
        key = f"classic/templates/{t.id}/print/{beat:02d}.jpg"
        buf = io.BytesIO()
        Image.new("RGB", (400, 400), "#305080").save(buf, format="JPEG")
        storage.put(key, buf.getvalue(), "image/jpeg")
        db.add(
            ClassicTemplatePage(
                template_id=t.id, beat=beat, image_key=key, has_hero=not bp.no_child,
                hero_box=None if bp.no_child else {"x": 0.3, "y": 0.3, "w": 0.3, "h": 0.5},
            )
        )  # fmt: skip
    db.commit()
    return t


async def test_the_budget_stops_a_classic_book(db: Session, storage: ObjectStorage, monkeypatch: Any) -> None:
    theme = _theme(db)
    _small_template(db, storage, theme, "girl_hijab")
    book = _book(db, theme, _child(db, storage), budget_pinned=True)
    book.budget_usd = Decimal("0.04")
    db.commit()

    def priced(settings: Any) -> Runtime:
        return Runtime(settings=settings, text=default_fake_text_provider(), image=PricedEdits())

    monkeypatch.setattr(jobs, "make_classic_runtime", priced)
    await classic_book_flow(db, storage, book, "final")
    db.refresh(book)
    assert "budget_exceeded" in book.flags and book.cost_usd <= Decimal("0.04")
    assert _pages(db, book)[0].status == PageStatus.ok  # the cover is edited first
    skipped = [p for p in _pages(db, book).values() if p.status == PageStatus.skipped]
    assert skipped and all("budget" in p.flags for p in skipped)
    assert not book.pdf_interior_key  # an unfinished book never gets print files


async def test_a_free_cover_and_its_photo_rule(db: Session, storage: ObjectStorage) -> None:
    from datetime import timedelta

    from qamra_core.db.classic import FreeCover, FreeCoverStatus
    from qamra_core.settings import get_core_settings
    from qamra_worker.jobs.free_cover import run_free_cover
    from qamra_worker.jobs.maintenance import cleanup_expired_media

    theme = _theme(db)
    t = _small_template(db, storage, theme, "girl_hijab")
    child = _child(db, storage)
    cover = FreeCover(user_id=child.guardian_user_id, child_id=child.id, theme_id=theme.id, template_id=t.id)
    db.add(cover)
    db.commit()
    result = await run_free_cover(db, storage, cover, offline="fake")
    assert result["status"] == "ready" and result["reference"] == "photo", (result, cover.error)
    assert cover.status == FreeCoverStatus.ready and cover.qa["likeness"] == 9
    for key, size in ((cover.image_key, (1024, 1024)), (cover.story_key, (1080, 1920))):
        assert key and key.startswith(f"children/{child.id}/free-covers/")  # deleted with the child
        with Image.open(io.BytesIO(storage.get(key))) as im:
            assert im.size == size and im.format == "JPEG"
    costs = db.scalars(select(GenerationCost).where(GenerationCost.child_id == child.id)).all()
    assert {c.step for c in costs} >= {"free_cover:hero:cover:a1", "free_cover:qa:cover:a1"}
    assert all(c.book_id is None for c in costs)

    # the photo's 24-hour rule: the request set it, the cleanup job deletes the original
    photo = db.scalars(select(ChildPhoto).where(ChildPhoto.child_id == child.id)).one()
    photo.delete_after = photo.created_at + timedelta(hours=24)
    db.commit()
    early = cleanup_expired_media(
        db, storage, get_core_settings(), now=photo.created_at + timedelta(hours=23)
    )
    assert early.photos_deleted == 0 and storage.exists(photo.storage_key or "")
    key = photo.storage_key or ""
    later = cleanup_expired_media(
        db, storage, get_core_settings(), now=photo.created_at + timedelta(hours=25)
    )
    assert later.photos_deleted == 1 and not storage.exists(key)
    assert storage.exists(cover.image_key or "")  # the drawn cover stays until the child's data is deleted


async def test_a_free_cover_stops_at_its_cap(db: Session, storage: ObjectStorage, monkeypatch: Any) -> None:
    from qamra_core.db.classic import FreeCover, FreeCoverStatus
    from qamra_core.db.models import AppSetting
    from qamra_worker.jobs.free_cover import run_free_cover

    theme = _theme(db)
    t = _small_template(db, storage, theme, "girl_hijab")
    child = _child(db, storage)
    db.add(AppSetting(key="free_cover_budget_usd", value="0.005"))
    cover = FreeCover(user_id=child.guardian_user_id, child_id=child.id, theme_id=theme.id, template_id=t.id)
    db.add(cover)
    db.commit()

    def priced(settings: Any) -> Runtime:
        return Runtime(settings=settings, text=default_fake_text_provider(), image=PricedEdits())

    monkeypatch.setattr("qamra_worker.jobs.free_cover.make_classic_runtime", priced)
    result = await run_free_cover(db, storage, cover)  # the edit (~$0.01) would pass the cap: never started
    assert result["status"] == "failed" and cover.status == FreeCoverStatus.failed and not cover.image_key
    assert cover.cost_usd == 0
