"""Test-only fixtures for the end-to-end tests (tests/e2e): mounted only when `E2E_FIXTURES=true` and never
in prod (the settings refuse it). They create what the paid steps would have made, with placeholder art and
no AI call: a child with the guardian's consent, an approved character, and a book waiting at its preview.
Everything belongs to the signed-in parent, so the real create, cart and checkout APIs run unchanged.

The order flows' tests (tests/e2e/test_order_flows.py) also finish what the real flow asked the worker for,
again with placeholders and no AI: the character drawn after the photo (`/characters/{id}/ready`, the parent
then approves it in the flow), the story preview (`/books/{id}/preview`), a live «قمرة كلاسيك» template so a
Classic preview can start (`/classic-templates`), and the staff's order confirmation with the activity books
"rendered" as placeholder PDFs (`/orders/{code}/confirm`), so the parent's download can be tested. One test
machine signs up and orders more than any family: `/rate-limits/reset` clears its own per-address counters.

The template studio's test (tests/e2e/test_admin_studio.py) signs in as staff (`/staff`: the roles asked for,
two-step verification passed) and edits a Classic template drawn with placeholder art (`/studio-templates`).
"""

import io
import secrets
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Request, Response
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from rq import Queue
from sqlalchemy import delete, select

from qamra_ai.pipeline.classic_geometry import text_box
from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.theme import Theme as ThemeDef
from qamra_ai.pipeline.theme import fill_title
from qamra_ai.pipeline.vowelize import source_hash, sources
from qamra_api.auth import mfa
from qamra_api.auth import service as auth
from qamra_api.auth.router import client_ip, set_session_cookies
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.store import gift_cards
from qamra_core import downloads as dl
from qamra_core.crypto import cipher_for, encrypt
from qamra_core.db.classic import ClassicTemplate, ClassicTemplatePage, TemplateStatus
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Consent,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PageStatus,
    Theme,
    UserRole,
)
from qamra_core.db.store import Coupon, CouponKind, GiftCard, OrderEvent, StaffRole, UserStaffRole
from qamra_core.storage import ObjectStorage
from qamra_pdf.arabic_names import genitive

router = APIRouter(prefix="/api/e2e", tags=["e2e"])
PREVIEW_BEATS = (0, 1, 2, 3)  # the cover and three pages, like a real preview
ACTIVITY_THEME = "e2e-activity-book"  # the hidden theme the placeholder activity books hang on


def _placeholder(color: tuple[int, int, int], fmt: str, side: int = 512) -> bytes:
    """A night sky with a moon: clearly not a real drawing."""
    img = Image.new("RGB", (side, side), color)
    draw = ImageDraw.Draw(img)
    draw.ellipse((side * 0.55, side * 0.12, side * 0.85, side * 0.42), fill=(242, 179, 61))
    draw.rectangle((0, side * 0.72, side, side), fill=(62, 107, 77))
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def _preview_pages(db: SessionDep, storage: ObjectStorage, book: Book, text: str | None = None) -> None:
    """The cover and the first pages of a preview, with placeholder art (and `text` on the story pages)."""
    for beat in PREVIEW_BEATS:
        key = f"children/{book.child_id}/books/{book.id}/preview/{beat:02d}.jpg"
        storage.put(key, _placeholder((22, 32, 74), "JPEG"), "image/jpeg")
        db.add(
            BookPage(
                book_id=book.id,
                index=beat,
                status=PageStatus.ok,
                preview_image_key=key,
                layout="full",
                text=text if beat else None,
                original_text=text if beat else None,
            )
        )


def _drop_queued(queue: Queue, target: uuid.UUID) -> None:
    """The worker's job for what a fixture just finished (a drawing, a preview), taken off the queue while it
    still waits, so it never reaches a provider. Run the e2e stack with no worker on this queue: a job a
    worker already took can't be called back."""
    for job in queue.get_jobs():
        if job.args and str(job.args[0]) == str(target):
            job.cancel()


async def _my_child(db: SessionDep, user_id: uuid.UUID, child_id: uuid.UUID) -> Child:
    child = await db.get(Child, child_id)
    if child is None or child.guardian_user_id != user_id:
        raise ApiError("not_found", 404)
    return child


class BookIn(BaseModel):
    child_id: uuid.UUID | None = None  # another book for a child made before (reuses its character)
    name: str = Field(default="ليان", min_length=1, max_length=40)
    gender: Literal["m", "f"] = "f"
    age: int = Field(default=6, ge=2, le=10)
    hijab: bool = False
    line: Literal["classic", "magic"] = "classic"
    theme: str = Field(default="olive-season", max_length=64)
    style: str = Field(default="watercolor", max_length=40)


class BookOut(BaseModel):
    child_id: uuid.UUID
    character_id: uuid.UUID
    book_id: uuid.UUID
    theme: str
    line: str
    characters: int  # how many characters the child has (a second book must not add one)


@router.post("/books", status_code=201)
async def preview_book(body: BookIn, user: CurrentUser, db: SessionDep, storage: StorageDep) -> BookOut:
    theme = (await db.execute(select(Theme).where(Theme.slug == body.theme))).scalar_one_or_none()
    if theme is None:
        raise ApiError("not_found", 404)
    if body.child_id is not None:
        child = await db.get(Child, body.child_id)
        if child is None or child.guardian_user_id != user.id:
            raise ApiError("not_found", 404)
    else:
        child = Child(
            guardian_user_id=user.id,
            first_name=body.name,
            gender=Gender(body.gender),
            birth_year=date.today().year - body.age,
            wears_hijab=body.hijab and body.gender == "f",
        )
        db.add(child)
        await db.flush()
        db.add(Consent(child_id=child.id, guardian_user_id=user.id, consent_text_version=CONSENT_VERSION))
    character = (
        (
            await db.execute(
                select(Character)
                .where(Character.child_id == child.id, Character.approved_at.is_not(None))
                .order_by(Character.approved_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if character is None:
        character = Character(
            child_id=child.id,
            art_style=body.style,
            status=CharacterStatus.approved,
            approved_at=datetime.now(UTC),
            provider="e2e",
            model="placeholder",
        )
        db.add(character)
        await db.flush()
        character.sheet_image_key = f"children/{child.id}/characters/{character.id}.png"
        storage.put(character.sheet_image_key, _placeholder((34, 48, 106), "PNG"), "image/png")
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=theme.id,
        theme_version=theme.version,
        created_by_user_id=user.id,
        language=Locale.ar,
        art_style=character.art_style,
        status=BookStatus.preview,
        title=fill_title(theme.title_ar, child.first_name, "f" if child.gender.value == "f" else "m"),
        budget_usd=Decimal("0"),
        generation={"line": body.line, "offline": "sketch", "e2e": True},
    )
    db.add(book)
    await db.flush()
    _preview_pages(db, storage, book)
    await db.commit()
    count = len(
        (await db.execute(select(Character.id).where(Character.child_id == child.id))).scalars().all()
    )
    return BookOut(
        child_id=child.id,
        character_id=character.id,
        book_id=book.id,
        theme=theme.slug,
        line=body.line,
        characters=count,
    )


class CharacterOut(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    status: str
    style: str


@router.post("/characters/{character_id}/ready")
async def character_ready(
    character_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep, queue: QueueDep
) -> CharacterOut:
    """The drawing the create flow asked for after the photo (`generating`), finished with placeholder art
    instead of the image model: `ready`, for the parent to approve in the flow as usual."""
    character = await db.get(Character, character_id)
    if character is None:
        raise ApiError("not_found", 404)
    child = await _my_child(db, user.id, character.child_id)
    if character.status == CharacterStatus.generating:
        _drop_queued(queue, character.id)
        character.sheet_image_key = f"children/{child.id}/characters/{character.id}.png"
        storage.put(character.sheet_image_key, _placeholder((34, 48, 106), "PNG"), "image/png")
        character.status = CharacterStatus.ready
        character.provider, character.model = "e2e", "placeholder"
        await db.commit()
    return CharacterOut(
        id=character.id, child_id=child.id, status=character.status.value, style=character.art_style
    )


class PreviewOut(BaseModel):
    id: uuid.UUID
    status: str
    title: str | None


@router.post("/books/{book_id}/preview")
async def finish_preview(
    book_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep, queue: QueueDep
) -> PreviewOut:
    """A story the create flow started (`generating`), at its preview with placeholder pages, as the worker
    would leave it: the parent then reviews it (Magic), picks the format and orders it."""
    book = await db.get(Book, book_id)
    if book is None or book.created_by_user_id != user.id:
        raise ApiError("not_found", 404)
    if book.status == BookStatus.generating:
        _drop_queued(queue, book.id)
        child = await _my_child(db, user.id, book.child_id)
        theme = await db.get(Theme, book.theme_id)
        if theme is not None and not book.title:
            title = theme.title_en if book.language == Locale.en else theme.title_ar
            book.title = fill_title(title, child.first_name, child.gender.value)
        _preview_pages(db, storage, book, text=f"نَصٌّ تَجْرِيبِيٌّ لِصَفْحَةٍ مِنْ حِكايَةِ {genitive(child.first_name)}.")
        book.status = BookStatus.preview
        book.generation = {**(book.generation or {}), "offline": "sketch", "e2e": True}
        await db.commit()
    return PreviewOut(id=book.id, status=book.status.value, title=book.title)


class TemplateIn(BaseModel):
    theme: str = Field(default="first-day", max_length=64)
    style: str = Field(default="watercolor", max_length=40)
    variant: Literal["girl", "girl_hijab", "boy"] = "girl"


class TemplateOut(BaseModel):
    id: uuid.UUID
    theme: str
    style: str
    variant: str
    status: str


@router.post("/classic-templates", status_code=201)
async def classic_template(body: TemplateIn, user: CurrentUser, db: SessionDep) -> TemplateOut:
    """A live «قمرة كلاسيك» template for a story, style and look (no pages: nothing draws from it here), so
    the Classic flow is offered and can start its preview; `/books/{id}/preview` finishes that preview.
    An existing template of the same story, style and look is used as it is (never changed)."""
    theme = (await db.execute(select(Theme).where(Theme.slug == body.theme))).scalar_one_or_none()
    if theme is None:
        raise ApiError("not_found", 404)
    template = (
        await db.execute(
            select(ClassicTemplate).where(
                ClassicTemplate.theme_id == theme.id,
                ClassicTemplate.art_style == body.style,
                ClassicTemplate.variant == body.variant,
            )
        )
    ).scalar_one_or_none()
    if template is None:
        now = datetime.now(UTC)
        template = ClassicTemplate(
            theme_id=theme.id,
            theme_version=theme.version,
            art_style=body.style,
            variant=body.variant,
            status=TemplateStatus.live,
            generation={"e2e": True, "offline": "sketch"},
            approved_at=now,
            live_at=now,
        )
        db.add(template)
        await db.commit()
    return TemplateOut(
        id=template.id,
        theme=theme.slug,
        style=template.art_style,
        variant=template.variant,
        status=template.status.value,
    )


# ---- the template studio (tests/e2e/test_admin_studio.py) --------------------------------------------------


class StaffIn(BaseModel):
    roles: list[StaffRole] = Field(default_factory=lambda: [StaffRole.owner], min_length=1, max_length=8)


class StaffOut(BaseModel):
    id: uuid.UUID
    roles: list[str]


@router.post("/staff")
async def staff(
    body: StaffIn,
    user: CurrentUser,
    request: Request,
    response: Response,
    db: SessionDep,
    settings: SettingsDep,
) -> StaffOut:
    """The signed-in test user becomes staff with `roles` (instead of the ones it had), two-step verification
    on, and a session that passed it (what /api/auth/mfa/verify gives): the admin pages open without an
    authenticator app."""
    user.role = UserRole.admin
    if user.totp_enabled_at is None:
        user.totp_secret_ciphertext = encrypt(cipher_for(settings), mfa.new_secret())
        user.totp_enabled_at = datetime.now(UTC)
    await db.execute(delete(UserStaffRole).where(UserStaffRole.user_id == user.id))
    roles = list(dict.fromkeys(body.roles))
    for role in roles:
        db.add(UserStaffRole(user_id=user.id, role=role, granted_at=datetime.now(UTC)))
    session = await auth.start_session(db, user, settings, request.headers.get("user-agent"), "e2e", mfa=True)
    set_session_cookies(response, session, settings)
    return StaffOut(id=user.id, roles=[r.value for r in roles])


class StudioTemplateIn(BaseModel):
    theme: str = Field(default="new-sibling", max_length=64)
    style: str = Field(default="cartoon", max_length=40)
    variant: Literal["girl", "girl_hijab", "boy"] = "boy"
    missing_box: int | None = 2  # this hero page has no hero box yet (the editor adds one)


async def _clear_template(db: SessionDep, queue: Queue, body: StudioTemplateIn) -> Theme:
    """The story's template at this style and look, when these fixtures made it or it is a dry run
    (placeholder art, never sold), is removed with the drafts copied from it and their queued jobs. Any other
    template there is left alone (409)."""
    row = (await db.execute(select(Theme).where(Theme.slug == body.theme))).scalar_one_or_none()
    if row is None:
        raise ApiError("not_found", 404)
    old = (
        await db.execute(
            select(ClassicTemplate).where(
                ClassicTemplate.theme_id == row.id,
                ClassicTemplate.art_style == body.style,
                ClassicTemplate.variant == body.variant,
            )
        )
    ).scalar_one_or_none()
    if old is None:
        return row
    if not (old.generation.get("e2e_studio") or old.generation.get("offline")):
        raise ApiError("template_exists", 409)
    copies = select(ClassicTemplate).where(ClassicTemplate.generation["copied_from"].astext == str(old.id))
    for t in [*(await db.execute(copies)).scalars(), old]:
        _drop_queued(queue, t.id)
        await db.delete(t)
    await db.flush()
    return row


@router.post("/studio-templates/clear", status_code=204)
async def clear_studio_template(
    body: StudioTemplateIn, user: CurrentUser, db: SessionDep, queue: QueueDep
) -> None:
    """Removes a test or dry-run template (see `_clear_template`), so a test can make it again."""
    await _clear_template(db, queue, body)
    await db.commit()


@router.post("/studio-templates", status_code=201)
async def studio_template(
    body: StudioTemplateIn, user: CurrentUser, db: SessionDep, storage: StorageDep, queue: QueueDep
) -> TemplateOut:
    """A «قمرة كلاسيك» template as the generator leaves it, in review, with placeholder art (no AI): every
    page of the theme's live story drawn, a hero box on each hero page (but `missing_box`), the text boxes
    where the book prints its words, and the Arabic marked vowelized (as written). Like a real run, page 1 is
    flagged for review (a framed picture). A test or dry-run template already there is made again
    (`_clear_template`)."""
    row = await _clear_template(db, queue, body)
    theme = ThemeDef.model_validate(row.definition)
    gender: Literal["m", "f"] = "m" if body.variant == "boy" else "f"
    texts = sources(theme, gender)
    template = ClassicTemplate(
        theme_id=row.id,
        theme_version=row.version,
        art_style=body.style,
        variant=body.variant,
        status=TemplateStatus.in_review,
        flags=["pages_need_review"],
        generation={
            "e2e_studio": True,
            "offline": "sketch",
            "theme_def": row.definition,
            "texts": {"hash": source_hash(texts), "gender": gender, "texts": texts.model_dump(), "kept": []},
        },
        created_by_user_id=user.id,
    )
    db.add(template)
    await db.flush()
    for beat, bp in plan_book(theme, "ar", companion_page=False).beats.items():  # as the generator lays out
        key = f"classic/templates/{template.id}/e2e/{beat:02d}.jpg"
        storage.put(key, _placeholder((22, 32, 74), "JPEG"), "image/jpeg")
        hero = not bp.no_child
        box = {"x": 0.3, "y": 0.35, "w": 0.3, "h": 0.5} if hero and beat != body.missing_box else None
        db.add(
            ClassicTemplatePage(
                template_id=template.id,
                beat=beat,
                layout=bp.layout,
                image_key=key,
                raw_key=key,
                preview_key=key,
                has_hero=hero,
                hero_box=box,
                text_box=text_box(bp.layout, bp.text_area),
                status=PageStatus.needs_review if beat == 1 else PageStatus.ok,
                flags=["frame"] if beat == 1 else [],
            )
        )
    await db.commit()
    return TemplateOut(
        id=template.id,
        theme=row.slug,
        style=template.art_style,
        variant=template.variant,
        status=template.status.value,
    )


@router.post("/rate-limits/reset", status_code=204)
async def reset_rate_limits(request: Request, redis: RedisDep) -> None:
    """The caller's own per-address counters (sign-ups, checkouts, order tracking, codes): a test machine
    signs up and orders more in an hour than any family would. Per-account counters stay as they are."""
    keys = [key async for key in redis.scan_iter(match=f"rl:*:{client_ip(request)}")]
    if keys:
        await redis.delete(*keys)


class CodeOut(BaseModel):
    code: str


class CouponIn(BaseModel):
    kind: Literal["percent", "fixed"] = "percent"
    value: Decimal = Field(default=Decimal("10"), gt=0, le=90)


@router.post("/coupons", status_code=201)
async def coupon(body: CouponIn, user: CurrentUser, db: SessionDep) -> CodeOut:
    code = "E2E" + secrets.token_hex(4).upper()
    currency = Currency.ILS if body.kind == "fixed" else None
    db.add(
        Coupon(code=code, kind=CouponKind(body.kind), value=body.value, currency=currency, per_customer=None)
    )
    await db.commit()
    return CodeOut(code=code)


class CardIn(BaseModel):
    amount: Decimal = Field(default=Decimal("50"), gt=0, le=500)


@router.post("/gift-cards", status_code=201)
async def gift_card(body: CardIn, user: CurrentUser, db: SessionDep) -> CodeOut:
    code = gift_cards.new_code()
    db.add(GiftCard(code=code, currency=Currency.ILS, amount=body.amount, balance=body.amount, note="e2e"))
    await db.commit()
    return CodeOut(code=gift_cards.pretty(code))


class ItemOut(BaseModel):
    id: uuid.UUID
    sku: str | None
    line: str | None
    child_id: uuid.UUID | None
    book_id: uuid.UUID | None
    personalization: dict[str, object]


class OrderOut(BaseModel):
    code: str
    status: str
    gift: bool
    gift_message: str | None
    total: Decimal
    discount: Decimal
    pricing: dict[str, object]
    skus: list[str]
    addons: list[list[str]]
    items: list[ItemOut]


async def _my_order(db: SessionDep, user_id: uuid.UUID, code: str) -> tuple[Order, list[OrderItem]]:
    row = (await db.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
    if row is None or row.user_id != user_id:
        raise ApiError("not_found", 404)
    items = (
        (await db.execute(select(OrderItem).where(OrderItem.order_id == row.id).order_by(OrderItem.id)))
        .scalars()
        .all()
    )
    return row, list(items)


@router.get("/orders/{code}")
async def order(code: str, user: CurrentUser, db: SessionDep) -> OrderOut:
    """What the test needs to check after checkout, for the signed-in parent's own orders only."""
    row, items = await _my_order(db, user.id, code)
    return OrderOut(
        code=row.code,
        status=row.status.value,
        gift=row.gift,
        gift_message=row.gift_message,
        total=row.total,
        discount=row.discount,
        pricing=row.pricing,
        skus=[str(i.sku) for i in items],
        addons=[[str(a.get("slug")) for a in i.addons] for i in items],
        items=[
            ItemOut(
                id=i.id,
                sku=i.sku,
                line=i.line,
                child_id=i.child_id,
                book_id=i.book_id,
                personalization=dict(i.personalization or {}),
            )
            for i in items
        ],
    )


def _placeholder_pdf(pages: int, label: str) -> bytes:
    """A small PDF of `pages` A4 pages (595 × 842 pt): no TrimBox, so its home copy is the page itself."""
    sheets = []
    for n in range(pages):
        img = Image.new("RGB", (595, 842), (250, 247, 240))
        draw = ImageDraw.Draw(img)
        draw.ellipse((330, 80, 500, 250), fill=(242, 179, 61))
        draw.text((60, 760), f"qamra e2e placeholder: {label} {n + 1}/{pages}", fill=(22, 32, 74))
        sheets.append(img)
    buf = io.BytesIO()
    sheets[0].save(buf, "PDF", resolution=72, save_all=True, append_images=sheets[1:])
    return buf.getvalue()


async def _activity_theme(db: SessionDep) -> Theme:
    theme = (await db.execute(select(Theme).where(Theme.slug == ACTIVITY_THEME))).scalar_one_or_none()
    if theme is None:
        theme = Theme(
            slug=ACTIVITY_THEME,
            title_ar="كتاب أنشطة (اختبار)",
            title_en="Activity book (test)",
            age_min=3,
            age_max=8,
            active=False,  # never listed as a story
            definition={"e2e": True},
        )
        db.add(theme)
        await db.flush()
    return theme


class ConfirmIn(BaseModel):
    render: bool = False  # also "render" the activity books, with placeholder PDFs (no page engine, no AI)


class MadeBook(BaseModel):
    book_id: uuid.UUID
    line: str
    part: str
    files: list[str]


class ConfirmOut(BaseModel):
    code: str
    status: str
    books: list[MadeBook]


# the extra files each activity book's job stores (worker/*_book.py), by line
EXTRA_FILES: dict[str, tuple[str, ...]] = {
    "workbook": ("answer-key",),
    "journey": ("answer-key",),
    "islamic": ("answer-key",),
    "family": ("stickers", "card-money-recipes", "card-games-roles"),
}


def _part_generation(item: OrderItem, part: str) -> dict[str, object]:
    """What the line's real job writes on each book: the line, the order line, and its volume or stage."""
    gen: dict[str, object] = {"line": item.line, "order_item_id": str(item.id), "e2e": True}
    if item.line == "workbook":
        gen |= {"level": dl.options_of(item).get("level", ""), "volume": int(part)}
    elif item.line == "journey":
        gen["stage"] = part
    elif item.line == "islamic":
        gen["volume"] = part
    return gen


async def _render_placeholders(
    db: SessionDep, storage: ObjectStorage, user_id: uuid.UUID, item: OrderItem
) -> list[MadeBook]:
    """Each book of an activity line as its job leaves a passed render (`in_review`, every preflight passed,
    the print files and extra files stored), with placeholder PDFs instead of the page engine."""
    if item.child_id is None or item.line not in EXTRA_FILES:
        return []
    child = await _my_child(db, user_id, item.child_id)
    theme = await _activity_theme(db)
    character_id = (item.personalization or {}).get("character_id")
    made = []
    for part in dl.parts_of(item.line, dl.options_of(item)):
        book = Book(
            child_id=child.id,
            character_id=uuid.UUID(str(character_id)) if character_id else None,
            theme_id=theme.id,
            theme_version=theme.version,
            language=Locale.ar,
            art_style="3d",
            status=BookStatus.in_review,
            title=f"{(item.title or {}).get('name_ar') or item.sku} · {child.first_name}",
            generation=_part_generation(item, part),
        )
        db.add(book)
        await db.flush()
        prefix = f"children/{child.id}/books/{book.id}/final"
        book.pdf_interior_key = f"{prefix}/interior.pdf"
        storage.put(
            book.pdf_interior_key, _placeholder_pdf(4, f"{item.line} {part} interior"), "application/pdf"
        )
        book.pdf_cover_key = f"{prefix}/cover.pdf"
        storage.put(book.pdf_cover_key, _placeholder_pdf(2, f"{item.line} {part} cover"), "application/pdf")
        files = {}
        for kind in EXTRA_FILES[str(item.line)]:
            files[kind] = f"{prefix}/{kind}.pdf"
            storage.put(files[kind], _placeholder_pdf(1, f"{item.line} {part} {kind}"), "application/pdf")
        book.generation = {**book.generation, "files": files}
        book.preflight = {"interior": {"passed": True}, "cover": {"passed": True}}
        made.append(MadeBook(book_id=book.id, line=str(item.line), part=part, files=["book", *files]))
    return made


@router.post("/orders/{code}/confirm")
async def confirm(
    code: str, body: ConfirmIn, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> ConfirmOut:
    """Staff confirm the parent's cash-on-delivery order (`new` → `confirmed`, with its event), without the
    jobs a real confirmation starts (invoice, renders). With `render`, the activity lines' books are made as
    their jobs would leave them after a passed render, so the parent's downloads can be tested."""
    row, items = await _my_order(db, user.id, code)
    if row.status == OrderStatus.new:
        row.status = OrderStatus.confirmed
        db.add(
            OrderEvent(
                order_id=row.id,
                kind="status",
                from_status=OrderStatus.new,
                to_status=OrderStatus.confirmed,
                note="e2e",
            )
        )
    books: list[MadeBook] = []
    if body.render:
        for item in items:
            books += await _render_placeholders(db, storage, user.id, item)
    await db.commit()
    return ConfirmOut(code=row.code, status=row.status.value, books=books)
