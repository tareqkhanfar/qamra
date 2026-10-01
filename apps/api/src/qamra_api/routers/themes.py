"""Public catalog: story worlds (themes) and prices."""

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from qamra_ai.pipeline.layout import plan_book
from qamra_ai.pipeline.theme import CatalogArt, Theme, render_template
from qamra_api.classic import classic_availability
from qamra_api.deps import SessionDep
from qamra_api.errors import ApiError
from qamra_api.store.catalog import load_catalog
from qamra_core.db.models import Currency
from qamra_core.db.models import Theme as ThemeRow

router = APIRouter(prefix="/api", tags=["catalog"])
Lang = Literal["ar", "en"]


class ThemeCard(BaseModel):
    slug: str
    name: str
    title: str  # the book's title with a {name} slot, e.g. "{name} في رحلة إلى القمر"
    tagline: str
    age_min: int
    age_max: int
    pages: int
    occasions: list[str]
    tag: str | None
    status: Literal["available", "coming_soon"]
    art: dict[str, Any]
    # «قمرة كلاسيك»: art style → the looks (girl, girl_hijab, boy) with a live template; empty = Magic only
    classic: dict[str, list[str]] = {}


class PeekItem(BaseModel):
    kind: Literal["art", "text"]
    art: dict[str, Any] | None = None
    text: str | None = None


class SamplePage(BaseModel):
    index: int
    text: str
    art: dict[str, Any]


class ThemeDetail(ThemeCard):
    description: str
    values: list[str]
    companion_slot: bool
    peek: list[PeekItem]
    sample_name: str | None
    sample_gender: Literal["m", "f"] | None  # fills the title's {masc/fem} for the sample child
    samples: list[SamplePage]


def _parse(row: ThemeRow) -> Theme:
    return Theme.model_validate(row.definition)


def book_pages(theme: Theme) -> int:
    """Interior pages of the printed book (title + story + parents page + fillers), as the design shows."""
    if not theme.pages:
        return 0
    return plan_book(theme, "ar", companion_page=theme.companion_slot).page_count


def _card(theme: Theme, lang: Lang) -> ThemeCard:
    c = theme.catalog
    if c is None:  # themes without catalog metadata are not listed
        raise ValueError(theme.slug)
    return ThemeCard(
        slug=theme.slug,
        name=c.name_ar if lang == "ar" else c.name_en,
        title=theme.title_ar if lang == "ar" else theme.title_en,
        tagline=c.tagline_ar if lang == "ar" else c.tagline_en,
        age_min=theme.age_range[0],
        age_max=theme.age_range[1],
        pages=book_pages(theme) or (c.planned_pages or 0),
        occasions=list(c.occasions),
        tag=c.tag,
        status=c.status,
        art=c.art.model_dump(),
    )


def _peek(theme: Theme, lang: Lang) -> list[PeekItem]:
    """Design: illustration · text · illustration · illustration (text from the real story)."""
    c = theme.catalog
    if c is None:
        return []
    arts: list[CatalogArt] = c.peek or [c.art]
    items = [PeekItem(kind="art", art=arts[0].model_dump())]
    if theme.pages and c.sample_child:
        named = [p for p in theme.pages if "{name}" in (p.text_ar if lang == "ar" else p.text_en)]
        page = next((p for p in named if p.index >= 4), named[0] if named else theme.pages[0])
        name = c.sample_child.name_ar if lang == "ar" else c.sample_child.name_en
        companion = ""
        if theme.default_companion:
            dc = theme.default_companion
            companion = dc.name_ar if lang == "ar" else dc.name_en
        template = page.text_ar if lang == "ar" else page.text_en
        items.append(
            PeekItem(kind="text", text=render_template(template, c.sample_child.gender, name, companion))
        )
    items += [PeekItem(kind="art", art=a.model_dump()) for a in arts[1:]]
    return items


SAMPLE_PAGES = (1, 6, 11, 17)


def _sample_context(theme: Theme, lang: Lang) -> tuple[str, str] | None:
    c = theme.catalog
    if c is None or c.sample_child is None or not theme.pages:
        return None
    name = c.sample_child.name_ar if lang == "ar" else c.sample_child.name_en
    companion = ""
    if theme.default_companion:
        dc = theme.default_companion
        companion = dc.name_ar if lang == "ar" else dc.name_en
    return name, companion


def _samples(theme: Theme, lang: Lang) -> list[SamplePage]:
    """A few real pages of the story, rendered for the catalog's sample child (landing carousel)."""
    ctx = _sample_context(theme, lang)
    c = theme.catalog
    if ctx is None or c is None or c.sample_child is None:
        return []
    name, companion = ctx
    arts = c.peek or [c.art]
    out = []
    for i, page in enumerate(p for p in theme.pages if p.index in SAMPLE_PAGES):
        text = render_template(
            page.text_ar if lang == "ar" else page.text_en, c.sample_child.gender, name, companion
        )
        out.append(SamplePage(index=page.index, text=text, art=arts[i % len(arts)].model_dump()))
    return out


async def _load(db: SessionDep) -> list[Theme]:
    rows = (await db.execute(select(ThemeRow).where(ThemeRow.active.is_(True)))).scalars().all()
    themes = [_parse(r) for r in rows]
    return sorted(
        (t for t in themes if t.catalog), key=lambda t: (t.catalog.rank if t.catalog else 999, t.slug)
    )


@router.get("/themes")
async def list_themes(db: SessionDep, lang: Lang = "ar") -> list[ThemeCard]:
    classic = await classic_availability(db)
    return [_card(t, lang).model_copy(update={"classic": classic.get(t.slug, {})}) for t in await _load(db)]


@router.get("/themes/{slug}")
async def get_theme(slug: str, db: SessionDep, lang: Lang = "ar") -> ThemeDetail:
    row = (
        await db.execute(select(ThemeRow).where(ThemeRow.slug == slug, ThemeRow.active.is_(True)))
    ).scalar_one_or_none()
    if row is None:
        raise ApiError("not_found", 404)
    theme = _parse(row)
    if theme.catalog is None:
        raise ApiError("not_found", 404)
    c = theme.catalog
    classic = (await classic_availability(db)).get(theme.slug, {})
    return ThemeDetail(
        **_card(theme, lang).model_copy(update={"classic": classic}).model_dump(),
        description=c.description_ar if lang == "ar" else c.description_en,
        values=c.values_ar if lang == "ar" else c.values_en,
        companion_slot=theme.companion_slot,
        peek=_peek(theme, lang),
        sample_name=(ctx[0] if (ctx := _sample_context(theme, lang)) else None),
        sample_gender=c.sample_child.gender if ctx and c.sample_child else None,
        samples=_samples(theme, lang),
    )


class Price(BaseModel):
    product: Literal["digital", "softcover", "hardcover"]
    amount: Decimal | None  # None = not set
    currency: Literal["ILS", "JOD"] = "ILS"


@router.get("/pricing")
async def pricing(db: SessionDep, currency: Literal["ILS", "JOD"] = "ILS") -> list[Price]:
    """The Classic book's formats from the store catalog; the full catalog is /api/store/catalog."""
    catalog = await load_catalog(db)
    formats = {
        v.options.get("format"): catalog.price(v, Currency(currency))
        for v in catalog.variants.values()
        if catalog.product_of(v).slug == "classic-book"
    }
    return [
        Price(product=p, amount=formats.get(p), currency=currency)
        for p in ("digital", "softcover", "hardcover")
    ]
