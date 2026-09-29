"""Addendum 9 order path: «الكتاب الثاني −15%», gift cards with coupons, and rounding in ₪ and JD."""

from decimal import Decimal as D

from qamra_core.pricing import (
    AddOnLine,
    BundleRule,
    CouponRule,
    GiftCardRule,
    ItemInput,
    SaleRule,
    ZoneRule,
    addon_amount,
    quote,
)

SECOND = BundleRule("two-books", "cheapest", 2, D("15"), ("classic", "magic"))
SIBLINGS = BundleRule("siblings", "siblings", 2, D("20"), ("classic", "magic"))
ZONE = ZoneRule(slug="west-bank", fee=D("20"), free_over=D("200"), cod_fee=D("0"))


def book(
    key: str,
    price: str,
    *,
    line: str = "classic",
    qty: int = 1,
    child: str | None = None,
    addons: tuple[AddOnLine, ...] = (),
) -> ItemInput:
    return ItemInput(
        key=key,
        line=line,
        product=f"{line}-book",
        sku=f"{line}-{price}",
        unit_price=D(price),
        qty=qty,
        child_key=child,
        addons=addons,
    )


GIFT_BOX = AddOnLine("gift-box", 1, D("15"))
EXTRA_COPY = AddOnLine("extra-copy", 1, D("0"), percent=D("50"))


def test_second_book_discount_goes_to_the_cheaper_book_never_its_add_ons() -> None:
    soft = book("soft", "69", addons=(GIFT_BOX, EXTRA_COPY))  # 69 + 15 + 34.50
    magic = book("magic", "139", line="magic")
    q = quote([soft, magic], bundles=[SECOND])
    assert q.bundle == "two-books"
    assert q.items[0].bundle_discount == D("10.35")  # 15% of 69: the cheaper book, not its add-ons
    assert q.items[1].bundle_discount == 0
    assert q.subtotal == D("257.50") and q.total == D("247.15")


def test_between_books_at_the_same_price_the_later_one_is_the_second() -> None:
    q = quote([book("a", "69"), book("b", "69")], bundles=[SECOND])
    assert [p.bundle_discount for p in q.items] == [0, D("10.35")]
    assert q.total == D("127.65")  # the design's cart: 138 − 10.35


def test_one_discounted_book_in_every_pair() -> None:
    three = quote([book("a", "99"), book("b", "69"), book("c", "139", line="magic")], bundles=[SECOND])
    assert [p.bundle_discount for p in three.items] == [0, D("10.35"), 0]  # 3 books: one pair
    four = quote([book("a", "99"), book("b", "69", qty=2), book("c", "139", line="magic")], bundles=[SECOND])
    assert four.items[1].bundle_discount == D("20.70")  # 4 copies: the two cheapest (both 69)
    assert four.bundle_discount == D("20.70")
    alone = quote([book("a", "69")], bundles=[SECOND])
    assert alone.bundle is None and alone.bundle_discount == 0


def test_the_second_book_follows_the_sale_price_and_its_lines() -> None:
    q = quote([book("a", "69"), book("b", "99")], sales=[SaleRule("Eid", D("10"))], bundles=[SECOND])
    assert q.items[0].sale_discount == D("6.90") and q.items[0].bundle_discount == D("9.32")  # 15% of 62.10
    coloring = quote([book("a", "69"), book("b", "39", line="coloring")], bundles=[SECOND])
    assert coloring.bundle is None  # the coloring book isn't in the rule's lines


def test_the_best_single_bundle_still_wins() -> None:
    kids = [book("a", "69", child="kid-1"), book("b", "139", line="magic", child="kid-2")]
    q = quote(kids, bundles=[SECOND, SIBLINGS])
    assert q.bundle == "siblings" and q.bundle_discount == D("41.60")  # 20% of both beats 15% of one
    same_child = [book("a", "69", child="kid-1"), book("b", "139", line="magic", child="kid-1")]
    q = quote(same_child, bundles=[SECOND, SIBLINGS])
    assert q.bundle == "two-books" and q.bundle_discount == D("10.35")


def test_gift_card_pays_after_every_discount_delivery_included() -> None:
    items = [book("a", "69", addons=(GIFT_BOX,)), book("b", "69")]
    coupon = CouponRule("EID10", "percent", D("10"))
    q = quote(items, bundles=[SECOND], coupon=coupon, zone=ZONE, gift_card=GiftCardRule("QG-…-AB12", D("50")))
    # 153 − 10.35 (second book) = 142.65; coupon 10% per item: 8.40 + 5.87 = 14.27 → 128.38; + 20 delivery
    assert q.coupon_discount == D("14.27") and q.shipping == D("20")
    assert q.gift_card == "QG-…-AB12" and q.gift_card_amount == D("50")
    assert q.total == D("98.38")  # 148.38 − 50
    assert q.discount == D("24.62")  # the card is a payment, not a discount


def test_gift_card_never_pays_more_than_the_order_and_keeps_the_free_delivery_rule() -> None:
    items = [book("a", "139", line="magic"), book("b", "99")]
    q = quote(items, zone=ZONE, gift_card=GiftCardRule("QG-…-1", D("500")))
    assert q.shipping == 0  # 238 ≥ 200: delivery is free whatever the card pays
    assert q.gift_card_amount == D("238") and q.total == 0
    empty = quote(items, gift_card=GiftCardRule("QG-…-2", D("0")))
    assert empty.gift_card is None and empty.gift_card_amount == 0 and empty.total == D("238")


def test_rounding_in_shekels_and_dinars_is_half_up_to_the_cent_at_every_step() -> None:
    # ₪: 15% of 69 = 10.35; a percent add-on of 50% on 69 = 34.50
    ils = quote([book("a", "69", addons=(EXTRA_COPY,)), book("b", "99")], bundles=[SECOND])
    assert ils.items[0].addons == D("34.50") and ils.bundle_discount == D("10.35")
    # JD: 15% of 13 = 1.95; of 5.5 = 0.825 → 0.83; 50% of 9.25 = 4.625 → 4.63
    jod = quote([book("a", "13"), book("b", "19")], bundles=[SECOND])
    assert jod.bundle_discount == D("1.95") and jod.total == D("30.05")
    small = quote([book("a", "5.5"), book("b", "9.5")], bundles=[SECOND])
    assert small.bundle_discount == D("0.83")
    assert addon_amount(EXTRA_COPY, D("9.25")) == D("4.63")
    # a fixed JD coupon spread over the items to the fils: the parts add up to the whole
    q = quote(
        [book("a", "13"), book("b", "17"), book("c", "19")],
        coupon=CouponRule("JD5", "fixed", D("5")),
        gift_card=GiftCardRule("QG-…-JD", D("10")),
    )
    assert sum(p.coupon_discount for p in q.items) == D("5") == q.coupon_discount
    assert q.total == sum(p.total for p in q.items) - q.gift_card_amount


def test_every_line_adds_up_to_the_total() -> None:
    items = [
        book("a", "69", addons=(GIFT_BOX, EXTRA_COPY)),
        book("b", "139", line="magic", addons=(GIFT_BOX,)),
        book("c", "99"),
    ]
    q = quote(
        items,
        sales=[SaleRule("x", D("5"))],
        bundles=[SECOND],
        coupon=CouponRule("X", "fixed", D("20")),
        zone=ZONE,
        gift_card=GiftCardRule("QG-…-3", D("33.33")),
    )
    lines = sum((p.total for p in q.items), D("0"))
    assert q.total == lines + q.shipping + q.cod_fee - q.gift_card_amount
    assert q.subtotal - q.discount == lines
