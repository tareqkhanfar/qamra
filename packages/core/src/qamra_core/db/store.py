"""The store (Addendum 4 §1–§6, and the workbook lines of Addenda 5 and 6): catalog, art styles, add-ons,
pricing rules, shipping, carts, order history, invoices and staff roles.

Money is `Numeric(10, 2)` in the sale currency (ILS or JOD). Unit costs are what one unit costs us: print,
packaging and shipping in ILS, AI in USD (the real AI cost of an order comes from `generation_costs`). Margins
are computed with the exchange rates in admin settings. Rows the pricing engine reads are plain data, so
every price, rule and cost is editable in the admin without a deploy.
"""

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qamra_core.db.base import Base, CreatedAtMixin, IdMixin, TimestampMixin, str_enum
from qamra_core.db.models import Currency, OrderStatus


class ProductLine(enum.StrEnum):
    classic = "classic"  # «قمرة كلاسيك»: template books, only the hero is adapted
    magic = "magic"  # «قمرة سحري»: every page drawn for the child
    coloring = "coloring"  # black-and-white line-art books
    workbook = "workbook"  # «دوسية التأسيس» (Addendum 5)
    journey = "journey"  # «رحلتي الأولى للتعلّم» (Addendum 6)
    family = "family"  # «مغامراتي مع عائلتي» (Addendum 7)


class Audience(enum.StrEnum):
    b2c = "b2c"
    b2b = "b2b"  # class books and kindergarten orders: priced from price lists


class AddOnPricing(enum.StrEnum):
    fixed = "fixed"  # a price per currency
    percent_of_item = "percent_of_item"  # e.g. an extra copy at 50% of the book


class CouponKind(enum.StrEnum):
    percent = "percent"
    fixed = "fixed"


class BundleKind(enum.StrEnum):
    min_items = "min_items"  # e.g. 2 books −15%
    siblings = "siblings"  # books for at least `min_items` different children in one order
    # Addendum 9 «الكتاب الثاني −15%»: in every `min_items` books, only the cheapest one is discounted
    cheapest = "cheapest"


class CartStatus(enum.StrEnum):
    open = "open"
    ordered = "ordered"
    abandoned = "abandoned"


class StaffRole(enum.StrEnum):
    owner = "owner"  # everything
    admin = "admin"  # settings, prices, users
    editor = "editor"  # themes, templates, workbook content
    reviewer = "reviewer"  # approves content and books
    production = "production"  # print batches, shipping
    support = "support"  # orders, customers, refunds and reprints


# ---- catalog --------------------------------------------------------------------------------------------


class ArtStyle(IdMixin, TimestampMixin, Base):
    """Addendum 4 §2: styles are data, seeded from `qamra_ai/prompts/style/<slug>.md` and edited in admin."""

    __tablename__ = "art_styles"

    slug: Mapped[str] = mapped_column(String(40), unique=True)
    name_ar: Mapped[str] = mapped_column(String(80))
    name_en: Mapped[str] = mapped_column(String(80))
    description_ar: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text)  # the style block injected into every image prompt
    negative: Mapped[str] = mapped_column(Text, default="")  # look-specific negatives
    version: Mapped[int] = mapped_column(Integer, default=1)  # bumped on prompt edits; books pin it
    lines: Mapped[list[str]] = mapped_column(JSONB, default=list)  # product lines it can be sold in
    price_modifier_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    price_modifier_jod: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    cost_modifier_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    qa_threshold: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0.75"))
    likeness_min: Mapped[int] = mapped_column(SmallInteger, default=7)
    sample_images: Mapped[list[str]] = mapped_column(JSONB, default=list)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CatalogProduct(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    line: Mapped[ProductLine] = mapped_column(str_enum(ProductLine, "product_line"))
    audience: Mapped[Audience] = mapped_column(str_enum(Audience, "product_audience"), default=Audience.b2c)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    description_ar: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    option_names: Mapped[list[str]] = mapped_column(JSONB, default=list)  # the variant options it uses
    min_qty: Mapped[int] = mapped_column(SmallInteger, default=1)  # class books: 20+
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # e.g. custom_story, page counts
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Variant(IdMixin, TimestampMixin, Base):
    """One sellable combination: format, size, level, volume, interior… with its unit costs."""

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    options: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)  # {"format": "hardcover", …}
    name_ar: Mapped[str] = mapped_column(String(160), default="")
    name_en: Mapped[str] = mapped_column(String(160), default="")
    cost_print_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    cost_packaging_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    cost_handling_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # per item
    cost_ai_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))  # estimate
    # the printer's price per copy by run length (Addendum 7 §3.9): [{"min_qty": 50, "unit_ils": "30.00"}, …]
    print_cost_tiers: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class VariantPrice(Base):
    __tablename__ = "variant_prices"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True
    )
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "variant_price_currency"), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class AddOn(IdMixin, TimestampMixin, Base):
    """Addendum 4 §4 and Addendum 5 §6. `requires` limits it to variants whose options match, e.g.
    {"format": ["softcover", "hardcover"]}; `excludes` lists add-ons it can't be combined with."""

    __tablename__ = "addons"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    description_ar: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str | None] = mapped_column(String(300))
    pricing: Mapped[AddOnPricing] = mapped_column(
        str_enum(AddOnPricing, "addon_pricing"), default=AddOnPricing.fixed
    )
    percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # for percent_of_item
    cost_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    cost_ai_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    lines: Mapped[list[str]] = mapped_column(JSONB, default=list)  # lines it is offered in
    included_lines: Mapped[list[str]] = mapped_column(JSONB, default=list)  # lines where it is free
    requires: Mapped[dict[str, list[str]]] = mapped_column(JSONB, default=dict)
    excludes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Addendum 9: add-ons this one depends on (turning it on turns them on; it is locked without them)
    needs: Mapped[list[str]] = mapped_column(JSONB, default=list)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)  # the add-ons step's open list, not «more»
    badge_ar: Mapped[str | None] = mapped_column(String(40))  # e.g. «الأكثر اختياراً», «توفير»
    badge_en: Mapped[str | None] = mapped_column(String(40))
    max_qty: Mapped[int] = mapped_column(SmallInteger, default=1)
    daily_capacity: Mapped[int | None] = mapped_column(Integer)  # express production
    step: Mapped[str] = mapped_column(String(24), default="format")  # where the flow offers it
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AddOnPrice(Base):
    __tablename__ = "addon_prices"

    addon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("addons.id", ondelete="CASCADE"), primary_key=True)
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "addon_price_currency"), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))


# ---- pricing rules --------------------------------------------------------------------------------------


class Bundle(IdMixin, TimestampMixin, Base):
    __tablename__ = "bundles"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    kind: Mapped[BundleKind] = mapped_column(str_enum(BundleKind, "bundle_kind"))
    min_items: Mapped[int] = mapped_column(SmallInteger, default=2)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    lines: Mapped[list[str]] = mapped_column(JSONB, default=list)  # empty = every line
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Coupon(IdMixin, TimestampMixin, Base):
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(32), unique=True)  # stored upper-case
    kind: Mapped[CouponKind] = mapped_column(str_enum(CouponKind, "coupon_kind"))
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # percent, or an amount in `currency`
    currency: Mapped[Currency | None] = mapped_column(str_enum(Currency, "coupon_currency"))
    min_subtotal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    per_customer: Mapped[int | None] = mapped_column(SmallInteger, default=1)
    first_order_only: Mapped[bool] = mapped_column(Boolean, default=False)
    lines: Mapped[list[str]] = mapped_column(JSONB, default=list)  # empty = every line
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CouponRedemption(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "coupon_redemptions"

    coupon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)  # guests are limited by phone
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class GiftCard(IdMixin, TimestampMixin, Base):
    """Addendum 9 §1.4: stored value issued by staff (not sold on the site), redeemed at checkout after every
    discount. The balance only goes down through one conditional UPDATE (`qamra_api.store.gift_cards`), and
    the CHECK keeps it within [0, amount], so two orders can never spend the same money."""

    __tablename__ = "gift_cards"
    __table_args__ = (CheckConstraint("balance >= 0 AND balance <= amount", name="balance_range"),)

    code: Mapped[str] = mapped_column(String(24), unique=True)  # "QG" + 12 random characters, stored bare
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "gift_card_currency"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # the value it was issued with
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # staff can switch a card off
    note: Mapped[str | None] = mapped_column(String(200))  # who it is for and why (staff only)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class GiftCardRedemption(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "gift_card_redemptions"

    gift_card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gift_cards.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class Sale(IdMixin, TimestampMixin, Base):
    """A seasonal sale: a percent off every matching item between two dates."""

    __tablename__ = "sales"

    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    lines: Mapped[list[str]] = mapped_column(JSONB, default=list)  # empty = every line
    products: Mapped[list[str]] = mapped_column(JSONB, default=list)  # product slugs; empty = every product
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceList(IdMixin, TimestampMixin, Base):
    """B2B prices with volume tiers. `organization_id = NULL` is the default list for new kindergartens."""

    __tablename__ = "price_lists"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "price_list_currency"))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceListItem(IdMixin, Base):
    __tablename__ = "price_list_items"

    price_list_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("price_lists.id", ondelete="CASCADE"), index=True
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), index=True
    )
    tiers: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # [{"min_qty": 20, "unit_price": "45.00"}, …]


class ShippingZone(IdMixin, TimestampMixin, Base):
    __tablename__ = "shipping_zones"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name_ar: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(2))  # PS | JO
    cities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "shipping_zone_currency"))
    fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    free_over: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # free shipping threshold
    cod_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # charged to the customer
    cost_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # a parcel costs us
    eta_days_min: Mapped[int] = mapped_column(SmallInteger, default=2)
    eta_days_max: Mapped[int] = mapped_column(SmallInteger, default=5)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---- carts ---------------------------------------------------------------------------------------------


class Cart(IdMixin, TimestampMixin, Base):
    """Server-side cart. Guests hold it through an httpOnly cookie; only the token's hash is stored."""

    __tablename__ = "carts"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "cart_currency"), default=Currency.ILS)
    coupon_code: Mapped[str | None] = mapped_column(String(32))
    gift_card_code: Mapped[str | None] = mapped_column(String(24))  # Addendum 9: redeemed at checkout
    gift: Mapped[bool] = mapped_column(Boolean, default=False)  # a gift: no prices on the packing slip
    gift_message: Mapped[str | None] = mapped_column(String(200))  # printed on the gift card
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shipping_zones.id", ondelete="SET NULL"))
    status: Mapped[CartStatus] = mapped_column(str_enum(CartStatus, "cart_status"), default=CartStatus.open)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CartItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"

    # a Python timestamp, so lines added in one transaction keep the order they were added in (the cart
    # lists them by created_at; Postgres now() is the same for the whole transaction)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now(), nullable=False
    )

    cart_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"))
    style_slug: Mapped[str | None] = mapped_column(String(40))
    theme_slug: Mapped[str | None] = mapped_column(String(64))
    qty: Mapped[int] = mapped_column(SmallInteger, default=1)
    addons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)  # [{"slug": …, "qty": 1}]
    # child, look variant, dedication, custom-story brief; photos stay in child_photos, never here
    personalization: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    child_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"))
    book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))


# ---- orders: history and invoices -------------------------------------------------------------------------


class OrderEvent(IdMixin, CreatedAtMixin, Base):
    """Every status change, note, customer message and reprint of an order (who, what, when)."""

    __tablename__ = "order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(24))  # status | note | message | reprint | payment
    from_status: Mapped[OrderStatus | None] = mapped_column(str_enum(OrderStatus, "order_event_from"))
    to_status: Mapped[OrderStatus | None] = mapped_column(str_enum(OrderStatus, "order_event_to"))
    note: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Invoice(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "invoices"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), unique=True)
    number: Mapped[str] = mapped_column(String(24), unique=True)  # INV-2026-00001
    year: Mapped[int] = mapped_column(SmallInteger)
    seq: Mapped[int] = mapped_column(Integer)
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "invoice_currency"))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    pdf_key: Mapped[str | None] = mapped_column(String(300))


class Counter(Base):
    """Gap-free sequences (invoice numbers per year), taken with SELECT … FOR UPDATE."""

    __tablename__ = "counters"

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


# ---- staff roles ------------------------------------------------------------------------------------------


class UserStaffRole(Base):
    """Addendum 4 §3.6. A staff member (users.role = admin) can hold several roles."""

    __tablename__ = "user_staff_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[StaffRole] = mapped_column(str_enum(StaffRole, "staff_role"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
