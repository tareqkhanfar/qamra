from decimal import Decimal as D

from qamra_core.pricing import AddOnLine, BundleRule, CouponRule, ItemInput, SaleRule, ZoneRule, quote

SOFT = ItemInput(key="a", line="classic", product="classic-book", sku="classic-soft-21", unit_price=D("69"))
MAGIC = ItemInput(key="m", line="magic", product="magic-book", sku="magic-hard-21", unit_price=D("139"))
ZONE = ZoneRule(slug="west-bank", fee=D("20"), free_over=D("200"), cod_fee=D("0"))


def test_unit_price_style_and_addons() -> None:
    item = ItemInput(
        key="a",
        line="classic",
        product="classic-book",
        sku="classic-soft-21",
        unit_price=D("69"),
        style_modifier=D("10"),
        addons=(
            AddOnLine("gift-box", 1, D("15")),
            AddOnLine("extra-copy", 2, D("0"), percent=D("50")),  # 50% of 79 = 39.50, twice
            AddOnLine("drawing-companion", 1, D("20"), included=True),
        ),
    )
    q = quote([item])
    assert q.items[0].unit_price == D("79.00")
    assert q.items[0].addons == D("15") + D("79.00")
    assert q.subtotal == q.total == D("173.00")


def test_sale_applies_to_matching_lines_only() -> None:
    q = quote([SOFT, MAGIC], sales=[SaleRule("Eid", D("20"), lines=("magic",))])
    assert q.items[0].sale_discount == 0 and q.items[1].sale_discount == D("27.80")
    assert q.total == D("69") + D("139") - D("27.80")


def test_the_best_single_bundle_wins() -> None:
    sibling = ItemInput(**{**SOFT.__dict__, "key": "b", "child_key": "kid-2"})
    first = ItemInput(**{**SOFT.__dict__, "child_key": "kid-1"})
    bundles = [
        BundleRule("two-books", "min_items", 2, D("15"), ("classic", "magic")),
        BundleRule("siblings", "siblings", 2, D("20"), ("classic", "magic")),
    ]
    q = quote([first, sibling], bundles=bundles)
    assert q.bundle == "siblings" and q.bundle_discount == D("27.60")
    same_child = ItemInput(**{**SOFT.__dict__, "key": "b", "child_key": "kid-1"})
    q = quote([first, same_child], bundles=bundles)
    assert q.bundle == "two-books" and q.bundle_discount == D("20.70")


def test_coupon_after_discounts_with_its_limits() -> None:
    q = quote([SOFT], sales=[SaleRule("x", D("10"))], coupon=CouponRule("WELCOME10", "percent", D("10")))
    assert q.items[0].coupon_discount == D("6.21")  # 10% of 62.10
    capped = quote([SOFT], coupon=CouponRule("BIG", "fixed", D("100")))
    assert capped.coupon_discount == D("69") and capped.total == 0
    small = quote([SOFT], coupon=CouponRule("MIN", "percent", D("10"), min_subtotal=D("100")))
    assert small.coupon is None and small.coupon_problem == "min_subtotal" and small.total == D("69")
    other = quote([SOFT], coupon=CouponRule("MAGIC", "percent", D("10"), lines=("magic",)))
    assert other.coupon_problem == "no_matching_items"


def test_fixed_coupon_is_spread_to_the_cent() -> None:
    q = quote([SOFT, MAGIC], coupon=CouponRule("TEN", "fixed", D("10")))
    assert sum(i.coupon_discount for i in q.items) == D("10")


def test_shipping_is_free_over_the_threshold_and_skipped_for_digital() -> None:
    assert quote([SOFT], zone=ZONE).shipping == D("20")
    assert quote([SOFT, MAGIC], zone=ZONE).shipping == 0  # 208 ≥ 200
    digital = ItemInput(
        key="d",
        line="classic",
        product="classic-book",
        sku="classic-digital",
        unit_price=D("19"),
        physical=False,
    )
    assert quote([digital], zone=ZONE).shipping == 0
    cod = ZoneRule(slug="z", fee=D("20"), cod_fee=D("5"))
    assert (
        quote([SOFT], zone=cod).cod_fee == D("5")
        and quote([SOFT], zone=cod, cash_on_delivery=False).cod_fee == 0
    )


def test_price_list_tiers_use_the_orders_total_quantity() -> None:
    tiers = ((20, D("45")), (50, D("40")), (100, D("35")))
    books = [
        ItemInput(
            key=str(n),
            line="workbook",
            product="wb",
            sku="wb-kg2-v1-color-spiral",
            unit_price=D("69"),
            tiers=tiers,
        )
        for n in range(55)
    ]
    q = quote(books, sales=[SaleRule("x", D("50"))])
    assert {i.unit_price for i in q.items} == {D("40.00")}
    assert q.sale_discount == 0  # sales never touch price-list prices
    few = quote(books[:5])
    assert {i.unit_price for i in few.items} == {
        D("69.00")
    } and "below the price list's minimum 20" in few.notes[0]


def test_price_by_quantity_follows_the_tiers_and_the_margin_rules() -> None:
    from qamra_core.pricing import quantity_prices

    tiers = ((1, D("42")), (10, D("36")), (50, D("30")), (100, D("26")), (500, D("19")))
    rows = quantity_prices(
        D("89"), tiers, D("4"), (1, 10, 50, 100, 500), bulk_margin_pct=D("45"), floor_pct=D("35")
    )
    assert [r.unit_price for r in rows] == [D("89"), D("73"), D("62"), D("55"), D("42")]
    assert rows[0].unit_cost == D("46") and rows[-1].total == D("21000")
    assert all(r.margin_pct >= 35 for r in rows)
    # a printer quote that pushes the cost up can't sell below the floor, even above the bulk price
    dear = quantity_prices(
        D("89"), ((1, D("70")),), D("4"), (1, 10), bulk_margin_pct=D("45"), floor_pct=D("35")
    )
    assert dear[0].unit_price == D("114") and dear[1].unit_price == D("114")
