"""Public catalog: story worlds (themes) and prices."""

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from qamra_ai.pipeline.theme import CatalogArt, Theme, render_template
from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep
from qamra_api.errors import ApiError
from qamra_core.db.models import Theme as ThemeRow

router = APIRouter(prefix="/api", tags=["catalog"])
Lang = Literal["ar", "en"]


class ThemeCard(BaseModel):
    slug: str
    name: str
    tagline: str
    age_min: int
    age_max: int
    pages: int
    occasions: list[str]
    tag: str | None
    status: Literal["available", "coming_soon"]
    art: dict[str, Any]


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
    samples: list[SamplePage]


def _parse(row: ThemeRow) -> Theme:
    return Theme.model_validate(row.definition)


def _card(theme: Theme, lang: Lang) -> ThemeCard:
    c = theme.catalog
    if c is None:  # themes without catalog metadata are not listed
        raise ValueError(theme.slug)
    return ThemeCard(
        slug=theme.slug,
        name=c.name_ar if lang == "ar" else c.name_en,
        tagline=c.tagline_ar if lang == "ar" else c.tagline_en,
        age_min=theme.age_range[0],
        age_max=theme.age_range[1],
        pages=len(theme.pages) or (c.planned_pages or 0),
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


SAMPLE_PAGES = (1, 4, 8, 12)


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
    return [_card(t, lang) for t in await _load(db)]


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
    return ThemeDetail(
        **_card(theme, lang).model_dump(),
        description=c.description_ar if lang == "ar" else c.description_en,
        values=c.values_ar if lang == "ar" else c.values_en,
        companion_slot=theme.companion_slot,
        peek=_peek(theme, lang),
        sample_name=(ctx[0] if (ctx := _sample_context(theme, lang)) else None),
        samples=_samples(theme, lang),
    )


class Price(BaseModel):
    product: Literal["digital", "softcover", "hardcover"]
    amount: Decimal | None  # None = not set
    currency: Literal["ILS", "JOD"] = "ILS"


@router.get("/pricing")
async def pricing(
    db: SessionDep, settings: SettingsDep, currency: Literal["ILS", "JOD"] = "ILS"
) -> list[Price]:
    values = (await runtime_settings.current(db, settings)).values
    suffix = currency.lower()
    return [
        Price(
            product=p,
            amount=Decimal(v) if (v := values.get(f"price_{p}_{suffix}")) not in (None, "") else None,
            currency=currency,
        )
        for p in ("digital", "softcover", "hardcover")
    ]
