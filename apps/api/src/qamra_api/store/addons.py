"""The add-ons step after the preview (Addendum 9, design AddOns): what a book in the cart can still add.

Everything comes from the catalog (admin data): which add-ons exist, their prices, the product lines and
formats they fit, the ones they can't be combined with (`excludes`) and the ones they depend on (`needs`).
The step gathers the add-ons chosen after the preview (`step` format or checkout); those of earlier steps
(the dedication written on the story step, a companion drawn on the character step) stay as they are.

- An add-on whose needs can't go on this book is locked (reason `needs`, with the missing add-ons).
- One that can't be combined with an add-on that is on is locked (reason `excludes`, with that add-on).
- Turning one on turns on what it needs; turning a needed one off turns off what depends on it. The web does
  that as the parent taps, and the cart checks the final set (`catalog.addon_problems`).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from qamra_api.store.catalog import Catalog, addon_lines, automatic_addons
from qamra_core.db.models import Currency
from qamra_core.db.store import AddOn, Variant
from qamra_core.pricing import addon_amount

AFTER_PREVIEW = ("format", "checkout")  # the steps whose add-ons this screen offers


@dataclass
class Offer:
    addon: AddOn
    price: Decimal  # one of it on this book, in the cart currency (percent add-ons: of the book's price)
    included: bool  # free in this product line
    on: bool
    qty: int
    locked: str | None = None  # needs | excludes
    blockers: list[str] = field(default_factory=list)  # the add-ons behind the lock


def fits(catalog: Catalog, variant: Variant, addon: AddOn) -> bool:
    """Offered for this book's line and format (the `requires` options)."""
    line = catalog.product_of(variant).line.value
    in_line = line in addon.lines or line in addon.included_lines
    return in_line and all(variant.options.get(k) in allowed for k, allowed in addon.requires.items())


def with_needs(catalog: Catalog, slugs: list[str]) -> list[str]:
    """The add-ons and, transitively, everything they need (in order, no repeats)."""
    out: list[str] = []
    todo = list(slugs)
    while todo:
        slug = todo.pop(0)
        if slug in out:
            continue
        out.append(slug)
        addon = catalog.addons.get(slug)
        todo += list(addon.needs) if addon is not None else []
    return out


def clash(catalog: Catalog, a: str, b: str) -> bool:
    x, y = catalog.addons.get(a), catalog.addons.get(b)
    return (x is not None and b in x.excludes) or (y is not None and a in y.excludes)


def managed(catalog: Catalog, variant: Variant) -> list[AddOn]:
    """The add-ons this step offers for a book, in the catalog's order."""
    automatic = set(automatic_addons(catalog, variant))
    return [
        a
        for a in sorted(catalog.addons.values(), key=lambda x: (x.sort, x.slug))
        if a.step in AFTER_PREVIEW and a.slug not in automatic and fits(catalog, variant, a)
    ]


def offers(
    catalog: Catalog,
    variant: Variant,
    currency: Currency,
    unit_price: Decimal,
    chosen: list[dict[str, Any]],
) -> list[Offer]:
    offered = managed(catalog, variant)
    here = {a.slug for a in offered}
    qty = {str(a["slug"]): int(a.get("qty", 1)) for a in chosen}
    out = []
    for addon in offered:
        [line] = addon_lines(catalog, variant, currency, [{"slug": addon.slug, "qty": 1}])
        on = addon.slug in qty
        offer = Offer(addon, addon_amount(line, unit_price), line.included, on, qty.get(addon.slug, 1))
        missing = [x for x in with_needs(catalog, list(addon.needs)) if x not in here]
        group = with_needs(catalog, [addon.slug])
        clashes = [x for x in qty if x not in group and any(clash(catalog, x, n) for n in group)]
        if missing:
            offer.locked, offer.blockers = "needs", missing
        elif clashes and not on:
            offer.locked, offer.blockers = "excludes", clashes
        out.append(offer)
    return out


def merge(
    catalog: Catalog, variant: Variant, current: list[dict[str, Any]], picked: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The item's add-ons after this step: the ones it doesn't offer stay, the ones it offers are `picked`."""
    mine = {a.slug for a in managed(catalog, variant)}
    kept = [a for a in current if str(a["slug"]) not in mine]
    return kept + [
        {"slug": str(a["slug"]), "qty": int(a.get("qty", 1))} for a in picked if str(a["slug"]) in mine
    ]
