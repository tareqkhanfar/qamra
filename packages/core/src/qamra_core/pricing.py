"""The pricing engine (Addendum 4 §5): one fixed, tested order of steps, the same for the cart and the order.

1. unit price: the variant's retail price, or its B2B price-list tier by the order's total quantity of that
   variant, plus the art style's modifier;
2. add-ons: fixed prices, or a percent of the item's unit price (the extra copy at 50%); included add-ons are
   free in that line;
3. seasonal sale: percent off matching items' base price (never on price-list items);
4. bundle: the single best bundle that applies (2+ books, siblings);
5. coupon: percent or fixed on the matching items after the discounts above (validity — dates, uses, first
   order — is checked where the coupon is loaded);
6. shipping: the zone's fee unless the discounted subtotal reaches its free threshold, plus its COD fee;
   orders with nothing to ship pay neither.

Pure functions on plain data: no database, so every rule is unit-tested. Amounts are rounded half-up to 0.01
at every step, so what the cart shows is exactly what the order stores.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
CENT = Decimal("0.01")


def r2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class AddOnLine:
    slug: str
    qty: int
    unit_price: Decimal  # fixed price in the cart currency (ignored for percent add-ons)
    percent: Decimal | None = None  # percent of the item's unit price
    included: bool = False  # free in this product line


@dataclass(frozen=True)
class ItemInput:
    key: str
    line: str
    product: str
    sku: str
    unit_price: Decimal  # retail price in the cart currency
    qty: int = 1
    style_modifier: Decimal = ZERO
    addons: tuple[AddOnLine, ...] = ()
    child_key: str | None = None  # the siblings bundle counts different children
    physical: bool = True  # digital items need no shipping
    tiers: tuple[tuple[int, Decimal], ...] = ()  # B2B price list: (min_qty, unit_price)


@dataclass(frozen=True)
class SaleRule:
    name: str
    discount_pct: Decimal
    lines: tuple[str, ...] = ()  # empty = every line
    products: tuple[str, ...] = ()  # empty = every product


@dataclass(frozen=True)
class BundleRule:
    slug: str
    kind: str  # min_items | siblings
    min_items: int
    discount_pct: Decimal
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class CouponRule:
    code: str
    kind: str  # percent | fixed
    value: Decimal
    min_subtotal: Decimal | None = None
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class ZoneRule:
    slug: str
    fee: Decimal
    free_over: Decimal | None = None
    cod_fee: Decimal = ZERO


@dataclass
class ItemPrice:
    key: str
    unit_price: Decimal  # after the price-list tier and style modifier
    base: Decimal  # unit_price × qty
    addons: Decimal
    sale_discount: Decimal = ZERO
    bundle_discount: Decimal = ZERO
    coupon_discount: Decimal = ZERO
    price_list: bool = False

    @property
    def total(self) -> Decimal:
        return self.base + self.addons - self.sale_discount - self.bundle_discount - self.coupon_discount


@dataclass
class Quote:
    items: list[ItemPrice]
    subtotal: Decimal  # items and add-ons before any discount
    sale_discount: Decimal
    bundle: str | None
    bundle_discount: Decimal
    coupon: str | None
    coupon_discount: Decimal
    coupon_problem: str | None
    shipping: Decimal
    cod_fee: Decimal
    total: Decimal
    notes: list[str] = field(default_factory=list)

    @property
    def discount(self) -> Decimal:
        return self.sale_discount + self.bundle_discount + self.coupon_discount


def _matches(line: str, product: str, lines: tuple[str, ...], products: tuple[str, ...] = ()) -> bool:
    return (not lines or line in lines) and (not products or product in products)


def unit_price(item: ItemInput, sku_qty: int) -> tuple[Decimal, bool]:
    """The tier with the highest minimum the order reaches, else the retail price."""
    reached = [t for t in item.tiers if sku_qty >= t[0]]
    if reached:
        return r2(max(reached)[1] + item.style_modifier), True
    return r2(item.unit_price + item.style_modifier), False


def addons_total(item: ItemInput, unit: Decimal) -> Decimal:
    total = ZERO
    for a in item.addons:
        if a.included:
            continue
        each = unit * a.percent / 100 if a.percent is not None else a.unit_price
        total += r2(each) * a.qty
    return total


def best_bundle(
    items: Sequence[ItemInput], prices: dict[str, ItemPrice], bundles: Sequence[BundleRule]
) -> tuple[str | None, dict[str, Decimal]]:
    best: tuple[Decimal, str | None, dict[str, Decimal]] = (ZERO, None, {})
    for b in bundles:
        eligible = [i for i in items if _matches(i.line, i.product, b.lines) and not prices[i.key].price_list]
        if b.kind == "siblings":
            reached = len({i.child_key for i in eligible if i.child_key}) >= b.min_items
        else:
            reached = sum(i.qty for i in eligible) >= b.min_items
        if not reached:
            continue
        cut = {
            i.key: r2((prices[i.key].base - prices[i.key].sale_discount) * b.discount_pct / 100)
            for i in eligible
        }
        amount = sum(cut.values(), ZERO)
        if amount > best[0]:
            best = (amount, b.slug, cut)
    return best[1], best[2]


def coupon_cut(
    items: Sequence[ItemInput], prices: dict[str, ItemPrice], coupon: CouponRule
) -> tuple[dict[str, Decimal], str | None]:
    eligible = [i for i in items if _matches(i.line, i.product, coupon.lines)]
    base = {i.key: prices[i.key].total for i in eligible}
    amount = sum(base.values(), ZERO)
    subtotal = sum((p.total for p in prices.values()), ZERO)
    if coupon.min_subtotal is not None and subtotal < coupon.min_subtotal:
        return {}, "min_subtotal"
    if amount <= 0:
        return {}, "no_matching_items"
    if coupon.kind == "percent":
        return {k: r2(v * coupon.value / 100) for k, v in base.items()}, None
    total = min(coupon.value, amount)
    cut: dict[str, Decimal] = {}
    left = total
    keys = list(base)
    for n, k in enumerate(keys):  # spread a fixed coupon over the items in proportion, cents to the last
        share = left if n == len(keys) - 1 else r2(total * base[k] / amount)
        cut[k] = share
        left -= share
    return cut, None


def quote(
    items: Sequence[ItemInput],
    *,
    sales: Sequence[SaleRule] = (),
    bundles: Sequence[BundleRule] = (),
    coupon: CouponRule | None = None,
    zone: ZoneRule | None = None,
    cash_on_delivery: bool = True,
) -> Quote:
    sku_qty = Counter[str]()
    for i in items:
        sku_qty[i.sku] += i.qty
    prices: dict[str, ItemPrice] = {}
    notes: list[str] = []
    for i in items:
        unit, listed = unit_price(i, sku_qty[i.sku])
        if i.tiers and not listed:
            notes.append(
                f"{i.sku}: {sku_qty[i.sku]} is below the price list's minimum {min(t[0] for t in i.tiers)}"
            )
        prices[i.key] = ItemPrice(i.key, unit, unit * i.qty, addons_total(i, unit), price_list=listed)
    subtotal = sum((p.base + p.addons for p in prices.values()), ZERO)

    for i in items:  # 3. the best matching sale per item
        p = prices[i.key]
        pct = max(
            (s.discount_pct for s in sales if _matches(i.line, i.product, s.lines, s.products)), default=ZERO
        )
        if pct and not p.price_list:
            p.sale_discount = r2(p.base * pct / 100)

    bundle, bundle_cut = best_bundle(items, prices, bundles)  # 4.
    for k, v in bundle_cut.items():
        prices[k].bundle_discount = v

    coupon_problem = None  # 5.
    if coupon is not None:
        cut, coupon_problem = coupon_cut(items, prices, coupon)
        for k, v in cut.items():
            prices[k].coupon_discount = v

    after = sum((p.total for p in prices.values()), ZERO)
    shipping = cod = ZERO  # 6.
    if zone is not None and any(i.physical for i in items):
        free = zone.free_over is not None and after >= zone.free_over
        shipping = ZERO if free else zone.fee
        cod = zone.cod_fee if cash_on_delivery else ZERO
    return Quote(
        items=[prices[i.key] for i in items],
        subtotal=subtotal,
        sale_discount=sum((p.sale_discount for p in prices.values()), ZERO),
        bundle=bundle,
        bundle_discount=sum((p.bundle_discount for p in prices.values()), ZERO),
        coupon=coupon.code if coupon is not None and coupon_problem is None else None,
        coupon_discount=sum((p.coupon_discount for p in prices.values()), ZERO),
        coupon_problem=coupon_problem,
        shipping=shipping,
        cod_fee=cod,
        total=after + shipping + cod,
        notes=notes,
    )
