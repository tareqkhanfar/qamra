"""The store hub (Addendum 9): the «أي كتاب يناسب طفلي؟» quiz (rules: qamra_api.store.quiz) and the shop's
public facts.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api.deps import (
    AdminUser,
    CurrentUser,
    OptionalUser,
    SessionDep,
    SettingsDep,
    require_admin,
    require_permission,
)
from qamra_api.errors import ApiError
from qamra_api.store.cart import ensure_cart
from qamra_api.store.catalog import PRINTED_FORMATS, Catalog, load_catalog
from qamra_api.store.quiz import (
    AGES,
    QUIZ_KEY,
    STORIES,
    Goal,
    Pen,
    ProductRef,
    QuizRule,
    QuizRules,
    gaps,
    load_rules,
    match,
)
from qamra_api.store.router import CartOut, _own_item, cart_out, check_copies, check_item
from qamra_api.store.workbooks import (
    ACTIVITY,
    TRACES_NAME,
    FamilyIn,
    accepted_styles,
    ages_for,
    asks_family,
    clean_latin,
    family_personalization,
    name_problem,
    needs_name_en,
    orderable,
    reusable_character,
)
from qamra_core.db.models import AppSetting, AuditLog, Character, Child, Currency, User
from qamra_core.db.store import CartItem, CatalogProduct, Variant

router = APIRouter(prefix="/api/shop", tags=["shop"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

STORY_PRODUCTS = ("classic-book", "magic-book")
PUBLIC_CACHE = {"Cache-Control": "public, max-age=60"}


# ---- recommendations ----------------------------------------------------------------------------------


class Pick(BaseModel):
    slug: str
    options: dict[str, str]
    kind: Literal["stories", "product"]
    name_ar: str
    name_en: str
    why_ar: str
    why_en: str
    from_price: Decimal | None  # the cheapest printed copy that fits (digital-only products: the cheapest)
    currency: Currency
    available: bool


class QuizAnswer(BaseModel):
    product: Pick
    alternative: Pick


def from_price(
    catalog: Catalog, slugs: tuple[str, ...], options: dict[str, str], currency: Currency
) -> Decimal | None:
    """What "from" means on the store's cards: the cheapest printed variant, else the cheapest one."""
    printed: list[Decimal] = []
    other: list[Decimal] = []
    for variant in catalog.variants.values():
        product = catalog.product_of(variant)
        if product.slug not in slugs or any(variant.options.get(k) != v for k, v in options.items()):
            continue
        price = catalog.price(variant, currency)
        if price is None:
            continue
        (printed if variant.options.get("format") in PRINTED_FORMATS else other).append(price)
    return min(printed or other) if (printed or other) else None


def pick(catalog: Catalog, ref: ProductRef, currency: Currency) -> Pick:
    if ref.slug == STORIES:
        names = [p for p in catalog.products.values() if p.slug in STORY_PRODUCTS]
        price = from_price(catalog, STORY_PRODUCTS, {}, currency)
        return Pick(
            slug=STORIES,
            options={},
            kind="stories",
            name_ar=ref.title_ar or "قصص قمرة",
            name_en=ref.title_en or "Qamra stories",
            why_ar=ref.why_ar,
            why_en=ref.why_en,
            from_price=price,
            currency=currency,
            available=bool(names) and price is not None,
        )
    product = next((p for p in catalog.products.values() if p.slug == ref.slug), None)
    price = from_price(catalog, (ref.slug,), ref.options, currency)
    options, title_ar, title_en = ref.options, ref.title_ar, ref.title_en
    if price is None and options and product is not None:
        # the rule names a volume or stage the store doesn't sell yet: recommend the book as it is sold now
        price = from_price(catalog, (ref.slug,), {}, currency)
        options, title_ar, title_en = {}, "", ""
    return Pick(
        slug=ref.slug,
        options=options,
        kind="product",
        name_ar=title_ar or (product.name_ar if product else ref.slug),
        name_en=title_en or (product.name_en if product else ref.slug),
        why_ar=ref.why_ar or (product.description_ar if product else ""),
        why_en=ref.why_en or (product.description_en if product else ""),
        from_price=price,
        currency=currency,
        available=product is not None and price is not None,
    )


@router.get("/quiz")
async def quiz(
    db: SessionDep,
    response: Response,
    age: int,
    goal: Goal,
    pen: Pen | None = None,
    currency: Literal["ILS", "JOD"] = "ILS",
) -> QuizAnswer:
    """The recommendation and its alternative for the quiz's answers."""
    rule = match((await load_rules(db)).rules, max(AGES[0], min(AGES[-1], age)), goal, pen)
    if rule is None:  # the admin editor refuses gaps; an old row might still have one
        rule = QuizRule(goal=goal, product=ProductRef(slug=STORIES), alternative=ProductRef(slug=STORIES))
    catalog = await load_catalog(db)
    response.headers.update(PUBLIC_CACHE)
    cur = Currency(currency)
    product, alternative = pick(catalog, rule.product, cur), pick(catalog, rule.alternative, cur)
    if goal == "faith":  # «قلبي يعرف الله» is recommended only while a volume is on sale (Addendum 10 §3.3)
        product, alternative = _on_sale(catalog, [product, alternative], cur)
    return QuizAnswer(product=product, alternative=alternative)


def _on_sale(catalog: Catalog, picks: list[Pick], currency: Currency) -> tuple[Pick, Pick]:
    """The picks that can be ordered, in order and without repeating one, then the story books."""
    out: list[Pick] = []
    for p in picks:
        if p.available and all((p.slug, p.options) != (o.slug, o.options) for o in out):
            out.append(p)
    stories = pick(catalog, ProductRef(slug=STORIES), currency)
    if len(out) > 1:
        return out[0], out[1]
    return (out[0], stories) if out else (stories, stories)  # the site doesn't offer the goal then


class ShopSummary(BaseModel):
    class_book_from: Decimal | None  # kindergartens: the cheapest class book per child
    class_book_min_qty: int | None
    currency: Currency
    orderable: dict[str, bool]  # per product: can it be ordered now (store/workbooks.py)


@router.get("/summary")
async def summary(db: SessionDep, response: Response, currency: Literal["ILS", "JOD"] = "ILS") -> ShopSummary:
    """Facts the shop's B2B banner shows, from the (otherwise private) class-book products."""
    catalog = await load_catalog(db, include_b2b=True)
    class_books = tuple(p.slug for p in catalog.products.values() if p.audience.value == "b2b")
    cur = Currency(currency)
    mins = [p.min_qty for p in catalog.products.values() if p.slug in class_books]
    response.headers.update(PUBLIC_CACHE)
    return ShopSummary(
        class_book_from=from_price(catalog, class_books, {}, cur) if class_books else None,
        class_book_min_qty=min(mins) if mins else None,
        currency=cur,
        orderable={p.slug: orderable(p) for p in catalog.products.values() if p.audience.value == "b2c"},
    )


# ---- admin: the rules ---------------------------------------------------------------------------------


class RulesOut(QuizRules):
    saved: bool  # False: the seed is shown until the first save


@admin_router.get("/quiz-rules", dependencies=[Depends(require_permission("prices"))])
async def get_rules(db: SessionDep) -> RulesOut:
    row = await db.get(AppSetting, QUIZ_KEY)
    return RulesOut(rules=(await load_rules(db)).rules, saved=row is not None)


@admin_router.put("/quiz-rules", dependencies=[Depends(require_permission("prices"))])
async def put_rules(body: QuizRules, admin: AdminUser, db: SessionDep) -> RulesOut:
    """Replace the rules. Every answer must still get a recommendation, and every product must exist."""
    missing = gaps(body.rules)
    if missing:
        raise ApiError("quiz_gaps", 422, {"answers": missing[:10]})
    catalog = await load_catalog(db, include_inactive=True)
    known = {p.slug for p in catalog.products.values()} | {STORIES}
    unknown = sorted({r.slug for rule in body.rules for r in (rule.product, rule.alternative)} - known)
    if unknown:
        raise ApiError("invalid_input", 422, {"fields": [f"product:{s}" for s in unknown]})
    row = await db.get(AppSetting, QUIZ_KEY) or AppSetting(key=QUIZ_KEY)
    row.value = body.model_dump(mode="json")
    row.updated_by_user_id = admin.id
    db.add(row)
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.quiz_rules_updated",
            entity_type="settings",
            entity_id=QUIZ_KEY,
            data={"rules": len(body.rules)},
        )
    )
    await db.commit()
    return RulesOut(rules=body.rules, saved=True)


# ---- activity books: what the book needs, the order item for a child, and who can order what ---------------


class NeedsAsks(BaseModel):
    name_en: bool  # the English name page: «دوسية التأسيس», «رحلتي الأولى» stages 2–3 and the set
    family: bool  # the «عائلة …» step: «مغامراتي مع عائلتي»


class NeedsCharacter(BaseModel):
    # the child's newest approved character in an accepted style (in `style` when it was asked);
    # None: draw one
    reuse_id: uuid.UUID | None
    # a new character is drawn in this style: the parent's choice (`style`), else the first accepted one
    draw_style: str | None
    # the styles this book accepts, in the site's order (never coloring): the style step's list
    styles: list[str]


class NeedsChild(BaseModel):
    id: uuid.UUID
    name: str
    name_traceable: bool  # False: the tracing pages can't write this name (see `name_problem`)
    name_problem: Literal["not_arabic", "not_traceable"] | None
    name_latin: str | None  # the English name saved on the child


class NeedsOut(BaseModel):
    line: str
    product: str
    sku: str
    options: dict[str, str]
    ages: list[int] | None  # [min, max] the variant is made for: the review step's non-blocking check
    traces_name: bool  # the Arabic name is traced (the who step asks for Arabic letters)
    asks: NeedsAsks
    character: NeedsCharacter
    child: NeedsChild | None  # with `child_id`


def _activity_variant(catalog: Catalog, sku: str) -> tuple[Variant, CatalogProduct]:
    """An activity book on sale now (404 otherwise: stories go through the create flow)."""
    variant = check_item(catalog, catalog.variants.get(sku), None, [])  # unknown, off sale or closed
    product = catalog.product_of(variant)
    if product.line.value not in ACTIVITY:
        raise ApiError("unknown_product", 404)
    return variant, product


async def _guarded_child(db: SessionDep, user: User | None, child_id: uuid.UUID) -> Child:
    if user is None:
        raise ApiError("not_authenticated", 401)
    child = await db.get(Child, child_id)
    if child is None or child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)  # the same answer for someone else's child
    return child


@router.get("/workbooks/needs")
async def workbook_needs(
    sku: Annotated[str, Query(max_length=64)],
    db: SessionDep,
    user: OptionalUser,
    child_id: uuid.UUID | None = None,
    style: Annotated[str | None, Query(max_length=40)] = None,
) -> NeedsOut:
    """What this activity book needs from the child, so the create flow shows only those steps (and the
    review step's age check). With `child_id` (the parent's own child): the character it reuses, if any,
    and whether the name can be traced. With `style` (the parent's pick on the style step, owner's decision
    of 2026-10-09): the character is drawn in it, and only one already in it is reused; a style the book
    doesn't accept → 422 `invalid_style`. The cart (`POST /workbooks/cart`) checks the same rules."""
    catalog = await load_catalog(db)
    variant, product = _activity_variant(catalog, sku)
    line = product.line.value
    styles = accepted_styles(catalog.styles.values(), line)
    if style is not None and style not in styles:
        raise ApiError("invalid_style", 422)
    wanted = [style] if style is not None else styles
    ages = ages_for(line, variant.options)
    child_out, reuse = None, None
    if child_id is not None:
        child = await _guarded_child(db, user, child_id)
        reuse = await reusable_character(db, child.id, wanted)
        problem = name_problem(line, child.first_name)
        child_out = NeedsChild(
            id=child.id,
            name=child.first_name,
            name_traceable=problem is None,
            name_problem=problem,
            name_latin=child.name_latin,
        )
    return NeedsOut(
        line=line,
        product=product.slug,
        sku=variant.sku,
        options=variant.options,
        ages=list(ages) if ages else None,
        traces_name=line in TRACES_NAME,
        asks=NeedsAsks(name_en=needs_name_en(line, variant.options), family=asks_family(line)),
        character=NeedsCharacter(
            reuse_id=reuse.id if reuse else None, draw_style=wanted[0] if wanted else None, styles=styles
        ),
        child=child_out,
    )


class WorkbookItemIn(BaseModel):
    sku: str = Field(max_length=64)
    child_id: uuid.UUID
    qty: int = Field(default=1, ge=1, le=50)
    family: FamilyIn | None = None  # «مغامراتي مع عائلتي»: the family's name, city and members (optional)
    item_id: uuid.UUID | None = None  # the cart line added in one tap, which this child completes
    # the character the flow chose (default: the newest approved one in a style the book accepts)
    character_id: uuid.UUID | None = None
    name_en: str | None = Field(default=None, max_length=80)  # the English name page; saved on the child


async def _character_for(
    db: SessionDep, child: Child, styles: list[str], character_id: uuid.UUID | None
) -> Character:
    if character_id is None:
        character = await reusable_character(db, child.id, styles)
        if character is None:
            raise ApiError("character_not_approved", 409)  # the flow draws one first
        return character
    character = await db.get(Character, character_id)
    if character is None or character.child_id != child.id:
        raise ApiError("not_found", 404)
    if character.approved_at is None:
        raise ApiError("character_not_approved", 409)
    if character.art_style not in styles:
        raise ApiError("character_style", 409)  # e.g. a coloring character
    return character


def _english_name(body: WorkbookItemIn, child: Child, needed: bool) -> str | None:
    """The English name for the line: the one sent (saved on the child too), else the child's saved one."""
    if body.name_en is not None and body.name_en.strip():
        try:
            child.name_latin = clean_latin(body.name_en)
        except ValueError as e:
            raise ApiError("name_en_invalid", 422, {"fields": ["name_en"]}) from e
    if not needed:
        return None
    if not child.name_latin:
        raise ApiError("name_en_required", 422, {"fields": ["name_en"]})
    return child.name_latin


@router.post("/workbooks/cart", status_code=201)
async def add_workbook(
    body: WorkbookItemIn,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
) -> CartOut:
    """An activity book for one of the parent's children, drawn with the child's approved character (no new
    AI cost). The order item carries the child, the variant (its options), the character used and, when the
    book prints it, the name in English letters. With `item_id`, the line added in one tap from the product
    page gets this child instead of a new line (the family given there stays unless a new one is sent)."""
    child = await _guarded_child(db, user, body.child_id)
    c = await load_catalog(db)
    variant, product = _activity_variant(c, body.sku)
    line = product.line.value
    character = await _character_for(db, child, accepted_styles(c.styles.values(), line), body.character_id)
    problem = name_problem(line, child.first_name)
    if problem is not None:  # the tracing pages would fail later, in the worker
        raise ApiError(f"name_{problem}", 422, {"fields": ["name"]})
    name_en = _english_name(body, child, needs_name_en(line, variant.options))
    item = None
    if body.item_id is not None:
        cart, item = await _own_item(db, request, user, body.item_id)  # 404 unless it is in the caller's cart
        if item.variant_id != variant.id:
            raise ApiError("item_mismatch", 409)
    else:
        cart = await ensure_cart(db, request, response, user, settings)
        await check_copies(db, cart, variant, body.qty)  # 10+ family books wait for the printer's prices
    family = family_personalization(body.family) if body.family is not None else None
    if family is None and item is not None:
        family = item.personalization.get("family")  # given on the product page, or in an earlier pass
    personalization = {
        "child_name": child.first_name,
        "gender": child.gender.value,
        "age": max(2, min(12, date.today().year - child.birth_year)),
        "hijab": child.wears_hijab,
        "glasses": child.wears_glasses,
        "character_id": str(character.id),
        **({"name_en": name_en} if name_en else {}),
        **({"family": family} if family and asks_family(line) else {}),
    }
    if item is not None:
        item.child_id, item.personalization = child.id, personalization
        item.style_slug = character.art_style  # the style the parent chose (or the reused character's)
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                variant_id=variant.id,
                child_id=child.id,
                qty=body.qty,
                style_slug=character.art_style,
                addons=[],
                personalization=personalization,
            )
        )
    cart.updated_at = datetime.now(UTC)
    await db.commit()
    return await cart_out(db, cart)


class OrderableIn(BaseModel):
    orderable: bool


@admin_router.get("/shop/orderable", dependencies=[Depends(require_permission("catalog"))])
async def orderable_flags(db: SessionDep) -> dict[str, bool]:
    catalog = await load_catalog(db, include_inactive=True)
    return {p.slug: orderable(p) for p in catalog.products.values()}


@admin_router.put("/shop/products/{slug}/orderable", dependencies=[Depends(require_permission("catalog"))])
async def set_orderable(slug: str, body: OrderableIn, admin: AdminUser, db: SessionDep) -> dict[str, Any]:
    """Open or close a product for orders (the cart refuses a closed one)."""
    product = (
        await db.execute(select(CatalogProduct).where(CatalogProduct.slug == slug))
    ).scalar_one_or_none()
    if product is None:
        raise ApiError("not_found", 404)
    before = orderable(product)
    product.features = {**(product.features or {}), "orderable": body.orderable}
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.product_orderable",
            entity_type="product",
            entity_id=slug,
            data={"before": before, "after": body.orderable},
        )
    )
    await db.commit()
    return {"slug": slug, "orderable": body.orderable}
