"""The pricing engine (Addendum 4 §5): one fixed, tested order of steps, the same for the cart and the order.

1. unit price: the variant's retail price, or its B2B price-list tier by the order's total quantity of that
   variant, plus the art style's modifier;
2. add-ons: fixed prices, or a percent of the item's unit price (the extra copy at 50%); included add-ons are
   free in that line;
3. seasonal sale: percent off matching items' base price (never on price-list items);
4. bundle: the single best bundle that applies (2+ books, siblings, «الكتاب الثاني −15%» on the cheaper);
5. coupon: percent or fixed on the matching items after the discounts above (validity — dates, uses, first
   order — is checked where the coupon is loaded);
6. shipping: the zone's fee unless the discounted subtotal reaches its free threshold, plus its COD fee;
   orders with nothing to ship pay neither;
7. gift card (Addendum 9): stored value paying what is left after every discount, delivery included; it is
   a payment, not a discount, so it never changes the free-delivery threshold.

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
    kind: str  # min_items | siblings | cheapest
    min_items: int
    discount_pct: Decimal
    lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class GiftCardRule:
    code: str
    balance: Decimal  # in the cart currency (a card only pays in its own currency)


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
    total: Decimal  # what is left to pay (cash on delivery), after the gift card
    notes: list[str] = field(default_factory=list)
    gift_card: str | None = None
    gift_card_amount: Decimal = ZERO
    gift_card_problem: str | None = None  # set where the card is loaded (unknown, expired, currency…)

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


def addon_amount(a: AddOnLine, unit: Decimal) -> Decimal:
    """One add-on line of an item: free when included, a percent of the unit price, or its fixed price."""
    if a.included:
        return ZERO
    each = unit * a.percent / 100 if a.percent is not None else a.unit_price
    return r2(each) * a.qty


def addons_total(item: ItemInput, unit: Decimal) -> Decimal:
    return sum((addon_amount(a, unit) for a in item.addons), ZERO)


def cheapest_cut(
    eligible: Sequence[ItemInput], prices: dict[str, ItemPrice], b: BundleRule
) -> dict[str, Decimal]:
    """«الكتاب الثاني −15%»: in every `min_items` copies, the cheapest copy is discounted (2 books: the
    cheaper one; 4 books: the two cheapest). On the book's price after the sale, never on its add-ons.
    Between copies at the same price, the later one in the cart is "the second book"."""
    copies: list[tuple[Decimal, int, str]] = []
    for n, i in enumerate(eligible):
        p = prices[i.key]
        each = (p.base - p.sale_discount) / i.qty
        copies += [(each, -n, i.key)] * i.qty
    cut: dict[str, Decimal] = {}
    for each, _, key in sorted(copies)[: len(copies) // max(b.min_items, 1)]:
        cut[key] = cut.get(key, ZERO) + r2(each * b.discount_pct / 100)
    return cut


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
        cut = (
            cheapest_cut(eligible, prices, b)
            if b.kind == "cheapest"
            else {
                i.key: r2((prices[i.key].base - prices[i.key].sale_discount) * b.discount_pct / 100)
                for i in eligible
            }
        )
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
    gift_card: GiftCardRule | None = None,
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
    due = after + shipping + cod
    paid = r2(min(gift_card.balance, due)) if gift_card is not None and gift_card.balance > 0 else ZERO  # 7.
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
        total=due - paid,
        notes=notes,
        gift_card=gift_card.code if paid > 0 and gift_card is not None else None,
        gift_card_amount=paid,
    )


# ---- price by quantity (Addendum 7 §3.9 and §8) --------------------------------------------------------


@dataclass(frozen=True)
class QuantityPrice:
    qty: int
    unit_cost: Decimal  # the printer's tier + the other unit costs, in ILS
    unit_price: Decimal
    total: Decimal
    margin_pct: Decimal


def tier_cost(tiers: Sequence[tuple[int, Decimal]], qty: int) -> Decimal | None:
    """The printer's price per copy for a run of `qty`: the tier with the highest minimum it reaches."""
    reached = [t for t in tiers if qty >= t[0]]
    return max(reached)[1] if reached else None


def quantity_prices(
    retail: Decimal,
    print_tiers: Sequence[tuple[int, Decimal]],
    other_unit_cost: Decimal,
    quantities: Sequence[int],
    *,
    bulk_margin_pct: Decimal,
    floor_pct: Decimal,
) -> list[QuantityPrice]:
    """One copy sells at retail. From 2 copies up, the price per copy is the tier's cost plus the bulk margin,
    rounded up to a whole shekel, never above retail and never below the margin floor."""
    out = []
    for qty in quantities:
        printing = tier_cost(print_tiers, qty)
        if printing is None:
            raise ValueError(f"no print cost tier covers {qty} copies")
        cost = r2(printing + other_unit_cost)
        with_margin = (cost / (1 - bulk_margin_pct / 100)).to_integral_value(rounding="ROUND_CEILING")
        at_floor = (cost / (1 - floor_pct / 100)).to_integral_value(rounding="ROUND_CEILING")
        price = retail if qty == 1 else min(retail, with_margin)
        price = r2(max(price, at_floor))
        margin = ((price - cost) / price * 100).quantize(Decimal("0.1")) if price else Decimal("0")
        out.append(QuantityPrice(qty, cost, price, r2(price * qty), margin))
    return out
