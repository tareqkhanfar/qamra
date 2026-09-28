"""Seed the store from `content/store/catalog.yaml` and the art-style guides (runs on every deploy).

Insert-only: rows that already exist are left alone, so prices, costs and prompts edited in the admin are
never overwritten by a deploy. New rows added to the files (a new variant, add-on or style) are inserted.
"""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.style import style_guides
from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_core.db.models import Currency
from qamra_core.db.store import (
    AddOn,
    AddOnPrice,
    AddOnPricing,
    ArtStyle,
    Audience,
    Bundle,
    BundleKind,
    CatalogProduct,
    Coupon,
    CouponKind,
    PriceList,
    PriceListItem,
    ProductLine,
    ShippingZone,
    Variant,
    VariantPrice,
)

CATALOG = CONTENT_DIR / "store" / "catalog.yaml"
LEGACY_STYLES = CONTENT_DIR / "styles" / "styles.yaml"  # crayon and paper-cut, kept inactive


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def expand_variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    """Plain `variants`, or a `variant_matrix` of levels × rows (the workbook)."""
    matrix = product.get("variant_matrix")
    if not matrix:
        return list(product.get("variants", []))
    out = []
    for level in matrix["levels"]:
        for row in matrix["rows"]:
            volume = row["volume"]
            tag = "set" if volume == "set" else f"v{volume}"
            options = {"level": level, "volume": volume, "interior": row["interior"], "format": row["format"]}
            sku = f"wb-{level}-{tag}-{row['interior']}-{row['format']}"
            out.append({"sku": sku, "options": options, "price": row["price"], "cost": row.get("cost", {})})
    return out


async def _exists(db: AsyncSession, column: Any, value: Any) -> Any:
    return (await db.execute(select(column.class_).where(column == value))).scalar_one_or_none()


async def _styles(db: AsyncSession) -> list[str]:
    added = []
    for sort, g in enumerate(style_guides()):
        if await _exists(db, ArtStyle.slug, g.slug):
            continue
        db.add(
            ArtStyle(
                slug=g.slug,
                name_ar=g.name_ar,
                name_en=g.name_en,
                prompt=g.look,
                negative=g.negative,
                version=g.version,
                lines=list(g.lines),
                qa_threshold=Decimal(str(g.qa_threshold)),
                likeness_min=g.likeness_min,
                sort=sort,
            )
        )
        added.append(f"+style:{g.slug}")
    legacy = yaml.safe_load(LEGACY_STYLES.read_text(encoding="utf-8")) if LEGACY_STYLES.exists() else {}
    for slug in ("crayon", "papercut"):
        entry = legacy.get(slug)
        if entry and not await _exists(db, ArtStyle.slug, slug):
            db.add(
                ArtStyle(
                    slug=slug,
                    name_ar=entry["title_ar"],
                    name_en=entry["title_en"],
                    prompt=entry["guide"],
                    lines=["magic"],
                    sort=90,
                    active=False,
                )
            )
            added.append(f"+style:{slug}")
    return added


async def _products(db: AsyncSession, products: list[dict[str, Any]]) -> list[str]:
    added = []
    for sort, p in enumerate(products):
        product = await _exists(db, CatalogProduct.slug, p["slug"])
        if product is None:
            product = CatalogProduct(
                slug=p["slug"],
                line=ProductLine(p["line"]),
                audience=Audience(p.get("audience", "b2c")),
                name_ar=p["name_ar"],
                name_en=p["name_en"],
                description_ar=p.get("description_ar", ""),
                description_en=p.get("description_en", ""),
                option_names=p.get("option_names", []),
                min_qty=p.get("min_qty", 1),
                features=p.get("features", {}),
                sort=sort,
            )
            db.add(product)
            await db.flush()
            added.append(f"+product:{p['slug']}")
        for vsort, v in enumerate(expand_variants(p)):
            if await _exists(db, Variant.sku, v["sku"]):
                continue
            cost = v.get("cost", {})
            variant = Variant(
                product_id=product.id,
                sku=v["sku"],
                options={k: str(x) for k, x in v["options"].items()},
                cost_print_ils=money(cost.get("print", 0)),
                cost_packaging_ils=money(cost.get("packaging", 0)),
                cost_handling_ils=money(cost.get("handling", 0)),
                cost_ai_usd=Decimal(str(cost.get("ai_usd", 0))),
                sort=vsort,
            )
            db.add(variant)
            await db.flush()
            for currency, amount in v["price"].items():
                db.add(VariantPrice(variant_id=variant.id, currency=Currency(currency), amount=money(amount)))
            added.append(f"+variant:{v['sku']}")
    return added


async def _addons(db: AsyncSession, addons: list[dict[str, Any]]) -> list[str]:
    added = []
    for sort, a in enumerate(addons):
        if await _exists(db, AddOn.slug, a["slug"]):
            continue
        addon = AddOn(
            slug=a["slug"],
            name_ar=a["name_ar"],
            name_en=a["name_en"],
            pricing=AddOnPricing(a.get("pricing", "fixed")),
            percent=Decimal(str(a["percent"])) if "percent" in a else None,
            cost_ils=money(a.get("cost_ils", 0)),
            cost_ai_usd=Decimal(str(a.get("cost_ai_usd", 0))),
            lines=a.get("lines", []),
            included_lines=a.get("included_lines", []),
            requires=a.get("requires", {}),
            excludes=a.get("excludes", []),
            max_qty=a.get("max_qty", 1),
            daily_capacity=a.get("daily_capacity"),
            step=a.get("step", "format"),
            sort=sort,
        )
        db.add(addon)
        await db.flush()
        for currency, amount in a.get("price", {}).items():
            db.add(AddOnPrice(addon_id=addon.id, currency=Currency(currency), amount=money(amount)))
        added.append(f"+addon:{a['slug']}")
    return added


async def _rules(db: AsyncSession, data: dict[str, Any]) -> list[str]:
    added = []
    for b in data.get("bundles", []):
        if not await _exists(db, Bundle.slug, b["slug"]):
            db.add(
                Bundle(
                    slug=b["slug"],
                    name_ar=b["name_ar"],
                    name_en=b["name_en"],
                    kind=BundleKind(b["kind"]),
                    min_items=b.get("min_items", 2),
                    discount_pct=Decimal(str(b["discount_pct"])),
                    lines=b.get("lines", []),
                )
            )
            added.append(f"+bundle:{b['slug']}")
    for c in data.get("coupons", []):
        code = c["code"].upper()
        if not await _exists(db, Coupon.code, code):
            db.add(
                Coupon(
                    code=code,
                    kind=CouponKind(c["kind"]),
                    value=money(c["value"]),
                    currency=Currency(c["currency"]) if c.get("currency") else None,
                    first_order_only=c.get("first_order_only", False),
                    active=c.get("active", True),
                )
            )
            added.append(f"+coupon:{code}")
    for sort, z in enumerate(data.get("shipping_zones", [])):
        if not await _exists(db, ShippingZone.slug, z["slug"]):
            eta = z.get("eta", [2, 5])
            db.add(
                ShippingZone(
                    slug=z["slug"],
                    name_ar=z["name_ar"],
                    name_en=z["name_en"],
                    country=z["country"],
                    cities=z.get("cities", []),
                    currency=Currency(z["currency"]),
                    fee=money(z["fee"]),
                    free_over=money(z["free_over"]) if z.get("free_over") is not None else None,
                    cod_fee=money(z.get("cod_fee", 0)),
                    cost_ils=money(z.get("cost_ils", 0)),
                    eta_days_min=eta[0],
                    eta_days_max=eta[1],
                    sort=sort,
                )
            )
            added.append(f"+zone:{z['slug']}")
    for pl in data.get("price_lists", []):
        exists = (
            await db.execute(
                select(PriceList).where(PriceList.name == pl["name"], PriceList.organization_id.is_(None))
            )
        ).scalar_one_or_none()
        if exists:
            continue
        price_list = PriceList(
            name=pl["name"], currency=Currency(pl["currency"]), valid_from=datetime.now(UTC)
        )
        db.add(price_list)
        await db.flush()
        for item in pl["items"]:
            variant = await _exists(db, Variant.sku, item["sku"])
            if variant is None:
                raise ValueError(f"price list {pl['name']!r}: unknown sku {item['sku']}")
            tiers = [
                {"min_qty": t["min_qty"], "unit_price": str(money(t["unit_price"]))} for t in item["tiers"]
            ]
            db.add(PriceListItem(price_list_id=price_list.id, variant_id=variant.id, tiers=tiers))
        added.append(f"+price_list:{pl['name']}")
    return added


async def seed_store(db: AsyncSession, path: Path = CATALOG) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    added = await _styles(db)
    added += await _products(db, data["products"])
    added += await _addons(db, data.get("addons", []))
    added += await _rules(db, data)
    await db.commit()
    return added
