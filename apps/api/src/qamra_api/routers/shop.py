"""The store hub (Addendum 9): the «أي كتاب يناسب طفلي؟» quiz (rules: qamra_api.store.quiz) and the shop's
public facts.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api.deps import AdminUser, CurrentUser, SessionDep, SettingsDep, require_admin, require_permission
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
from qamra_api.store.workbooks import ACTIVITY, FamilyIn, family_personalization, orderable
from qamra_core.db.models import AppSetting, AuditLog, Character, Child, Currency
from qamra_core.db.store import CartItem, CatalogProduct

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


# ---- activity books: the order item for a child, and who can order what ------------------------------------


class WorkbookItemIn(BaseModel):
    sku: str = Field(max_length=64)
    child_id: uuid.UUID
    qty: int = Field(default=1, ge=1, le=50)
    family: FamilyIn | None = None  # «مغامراتي مع عائلتي»: the family's name, city and members (optional)
    item_id: uuid.UUID | None = None  # the cart line added in one tap, which this child completes


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
    AI cost). The order item carries the child, the variant (its options) and the character used. With
    `item_id`, the line added in one tap from the product page gets this child instead of a new line."""
    child = await db.get(Child, body.child_id)
    if child is None or child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)
    character = (
        await db.execute(
            select(Character)
            .where(Character.child_id == child.id, Character.approved_at.is_not(None))
            .order_by(Character.approved_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if character is None:
        raise ApiError("character_not_approved", 409)
    c = await load_catalog(db)
    variant = check_item(c, c.variants.get(body.sku), None, [])  # unknown, off sale or not orderable yet
    line = c.product_of(variant).line.value
    if line not in ACTIVITY:
        raise ApiError("unknown_product", 404)
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
        family = item.personalization.get("family")  # given on the product page
    personalization = {
        "child_name": child.first_name,
        "gender": child.gender.value,
        "age": max(2, min(12, date.today().year - child.birth_year)),
        "hijab": child.wears_hijab,
        "glasses": child.wears_glasses,
        "character_id": str(character.id),
        **({"family": family} if family and line == "family" else {}),
    }
    if item is not None:
        item.child_id, item.personalization = child.id, personalization
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                variant_id=variant.id,
                child_id=child.id,
                qty=body.qty,
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
