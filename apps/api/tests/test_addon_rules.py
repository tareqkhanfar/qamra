"""Addendum 9 add-ons step: dependencies (`needs`), exclusions and what the step offers, from catalog rows."""

import uuid
from decimal import Decimal as D
from typing import Any

from qamra_api.store.addons import managed, merge, offers, with_needs
from qamra_api.store.catalog import Catalog, addon_problems
from qamra_core.db.models import Currency
from qamra_core.db.store import AddOn, AddOnPricing, Audience, CatalogProduct, ProductLine, Variant

PRODUCT = CatalogProduct(
    id=uuid.uuid4(),
    slug="classic-book",
    line=ProductLine.classic,
    audience=Audience.b2c,
    name_ar="-",
    name_en="-",
)
SOFT = Variant(id=uuid.uuid4(), product_id=PRODUCT.id, sku="classic-soft", options={"format": "softcover"})
DIGITAL = Variant(id=uuid.uuid4(), product_id=PRODUCT.id, sku="classic-pdf", options={"format": "digital"})
PRINTED = {"format": ["softcover", "hardcover"]}


def addon(slug: str, sort: int, **kw: Any) -> AddOn:
    fields: dict[str, Any] = {
        "lines": ["classic"],
        "included_lines": [],
        "requires": {},
        "excludes": [],
        "needs": [],
        "pricing": AddOnPricing.fixed,
        "percent": None,
        "max_qty": 1,
        "step": "checkout",
        "featured": False,
        "description_ar": "",
        "description_en": "",
    }
    return AddOn(id=uuid.uuid4(), slug=slug, name_ar=slug, name_en=slug, sort=sort, **{**fields, **kw})


def catalog(*rows: AddOn, prices: dict[str, str] | None = None) -> Catalog:
    addons = {a.slug: a for a in rows}
    amounts = {(addons[s].id, Currency.ILS): D(v) for s, v in (prices or {}).items()}
    return Catalog(
        products={PRODUCT.id: PRODUCT},
        variants={SOFT.sku: SOFT, DIGITAL.sku: DIGITAL},
        prices={(SOFT.id, Currency.ILS): D("69"), (DIGITAL.id, Currency.ILS): D("19")},
        styles={},
        addons=addons,
        addon_prices=amounts,
        zones={},
    )


BOX = addon("gift-box", 1, requires=PRINTED, featured=True)
RIBBON = addon("gift-ribbon", 2, needs=["gift-box"])  # an add-on that depends on another
BOW = addon("gift-bow", 3, needs=["gift-ribbon"])  # …transitively
POSTER = addon("cover-poster", 4, excludes=["express"])
EXPRESS = addon("express", 5, requires=PRINTED)
COPY = addon("extra-copy", 6, pricing=AddOnPricing.percent_of_item, percent=D("50"), requires=PRINTED)
DEDICATION = addon("dedication-page", 7, step="story")
FREE_DIGITAL = addon("digital-copy", 8, requires=PRINTED)
PRICES = {"gift-box": "15", "gift-ribbon": "5", "gift-bow": "3", "cover-poster": "25", "express": "20"}
FULL = catalog(BOX, RIBBON, BOW, POSTER, EXPRESS, COPY, DEDICATION, FREE_DIGITAL, prices=PRICES)


def picked(*slugs: str) -> list[dict[str, Any]]:
    return [{"slug": s, "qty": 1} for s in slugs]


def test_an_add_on_needs_the_ones_it_depends_on() -> None:
    assert addon_problems(FULL, SOFT, picked("gift-ribbon")) == ["gift-ribbon: needs gift-box"]
    assert addon_problems(FULL, SOFT, picked("gift-ribbon", "gift-box")) == []
    assert addon_problems(FULL, SOFT, picked("gift-bow", "gift-ribbon")) == ["gift-ribbon: needs gift-box"]
    assert with_needs(FULL, ["gift-bow"]) == ["gift-bow", "gift-ribbon", "gift-box"]  # transitively, in order


def test_dependencies_in_a_loop_resolve_once() -> None:
    a, b = addon("a", 1, needs=["b"]), addon("b", 2, needs=["a"])
    assert with_needs(catalog(a, b), ["a"]) == ["a", "b"]


def test_exclusions_still_hold() -> None:
    assert addon_problems(FULL, SOFT, picked("cover-poster", "express")) == [
        "cover-poster: can't be combined with express"
    ]


def test_the_step_offers_post_preview_add_ons_that_fit_the_format() -> None:
    slugs = [a.slug for a in managed(FULL, SOFT)]
    # not the dedication (asked on the story step) nor the free digital copy (automatic)
    assert slugs == ["gift-box", "gift-ribbon", "gift-bow", "cover-poster", "express", "extra-copy"]
    assert [a.slug for a in managed(FULL, DIGITAL)] == ["gift-ribbon", "gift-bow", "cover-poster"]


def test_offers_price_lock_and_explain() -> None:
    by = {o.addon.slug: o for o in offers(FULL, SOFT, Currency.ILS, D("69"), picked("express"))}
    assert by["gift-box"].price == D("15") and by["gift-box"].addon.featured
    assert by["extra-copy"].price == D("34.50")  # 50% of this book's price
    assert by["express"].on and by["express"].locked is None
    assert by["cover-poster"].locked == "excludes" and by["cover-poster"].blockers == ["express"]
    assert by["gift-ribbon"].locked is None  # its gift box can go on this book: turning it on turns both on
    # on a digital book there is no gift box, so what needs it is locked, with the reason
    digital = {o.addon.slug: o for o in offers(FULL, DIGITAL, Currency.ILS, D("19"), [])}
    assert digital["gift-ribbon"].locked == "needs" and digital["gift-ribbon"].blockers == ["gift-box"]
    assert digital["gift-bow"].locked == "needs" and digital["gift-bow"].blockers == ["gift-box"]


def test_an_exclusion_counts_what_the_add_on_brings_with_it() -> None:
    wrap = addon("gift-wrap", 9, excludes=["gift-box"])
    c = catalog(BOX, RIBBON, wrap, prices={"gift-box": "15", "gift-ribbon": "5", "gift-wrap": "4"})
    by = {o.addon.slug: o for o in offers(c, SOFT, Currency.ILS, D("69"), picked("gift-wrap"))}
    assert by["gift-box"].locked == "excludes" and by["gift-box"].blockers == ["gift-wrap"]
    assert by["gift-ribbon"].locked == "excludes"  # it would bring the gift box along


def test_merge_keeps_the_add_ons_of_other_steps() -> None:
    current = [{"slug": "dedication-page", "qty": 1}, {"slug": "express", "qty": 1}]
    assert merge(FULL, SOFT, current, picked("gift-box", "dedication-page", "unknown")) == [
        {"slug": "dedication-page", "qty": 1},
        {"slug": "gift-box", "qty": 1},
    ]
