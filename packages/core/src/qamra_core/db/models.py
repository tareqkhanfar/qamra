"""Data model (CLAUDE.md §6 + Addendum 1). Changes vs the spec are recorded in docs/decisions.md.

Deletion rules:
- child-owned rows (consents, photos, characters, companions, books, pages, recordings) cascade
  from `children`, so "delete all my child's data" is one DELETE after the storage objects are removed;
- financial and analytics rows (order items, generation costs) keep existing with the FK set to NULL;
- audit logs never hold FKs or PII, only ids and actions.
"""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from qamra_core.db.base import Base, CreatedAtMixin, IdMixin, TimestampMixin, str_enum

# ---- enums ---------------------------------------------------------------------------------


class UserRole(enum.StrEnum):
    parent = "parent"
    school_admin = "school_admin"
    admin = "admin"


class Locale(enum.StrEnum):
    ar = "ar"
    en = "en"


class OrgStatus(enum.StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    suspended = "suspended"


class Gender(enum.StrEnum):
    m = "m"
    f = "f"


class PhotoStatus(enum.StrEnum):
    uploaded = "uploaded"
    rejected = "rejected"
    accepted = "accepted"
    deleted = "deleted"


class CharacterStatus(enum.StrEnum):
    generating = "generating"
    ready = "ready"
    approved = "approved"
    discarded = "discarded"
    failed = "failed"


class CompanionType(enum.StrEnum):
    creature = "creature"
    animal = "animal"
    robot = "robot"
    other = "other"


class BookStatus(enum.StrEnum):
    draft = "draft"
    generating = "generating"
    preview = "preview"
    in_review = "in_review"  # final files ready; waiting for the admin's print approval (Addendum 3 §5)
    approved = "approved"  # approved for print by an admin (the only way to reach print batches)
    ordered = "ordered"
    printed = "printed"
    failed = "failed"


class PageStatus(enum.StrEnum):
    pending = "pending"
    ok = "ok"  # passed automatic QA
    needs_review = "needs_review"  # best attempt kept after the automatic redraws; a human decides
    failed = "failed"
    skipped = "skipped"  # not drawn (budget cap, missing cover)


class SafetyStatus(enum.StrEnum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    needs_review = "needs_review"


class Product(enum.StrEnum):
    digital = "digital"
    softcover = "softcover"
    hardcover = "hardcover"
    class_book = "class_book"


class Currency(enum.StrEnum):
    ILS = "ILS"
    JOD = "JOD"


class PaymentMethod(enum.StrEnum):
    cod = "cod"
    card = "card"


class PaymentStatus(enum.StrEnum):
    unpaid = "unpaid"
    paid = "paid"
    refunded = "refunded"


class OrderStatus(enum.StrEnum):
    """Addendum 4 §5: new → confirmed → generating → review → printing → shipped → delivered."""

    new = "new"
    confirmed = "confirmed"
    generating = "generating"
    review = "review"
    printing = "printing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    reprint = "reprint"


class PrintBatchStatus(enum.StrEnum):
    open = "open"
    sent = "sent"
    printing = "printing"
    done = "done"


class ShareScope(enum.StrEnum):
    read = "read"  # web reader / share link
    listen = "listen"  # QR → page audio (Addendum 1 §3)
    record = "record"  # remote grandparent recording link


# ---- accounts ------------------------------------------------------------------------------


class Organization(IdMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[OrgStatus] = mapped_column(str_enum(OrgStatus, "org_status"), default=OrgStatus.pending)
    country: Mapped[str] = mapped_column(String(2), default="PS")  # PS | JO
    city: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(300))  # the school: where class orders are delivered
    logo_key: Mapped[str | None] = mapped_column(String(300))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # pricing tier etc.
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-cased
    password_hash: Mapped[str | None] = mapped_column(String(255))  # None → Google-only account
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "user_role"), default=UserRole.parent)
    locale: Mapped[Locale] = mapped_column(str_enum(Locale, "user_locale"), default=Locale.ar)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Two-factor sign-in (TOTP, RFC 6238). Required for admins (Addendum 3 §6).
    totp_secret_ciphertext: Mapped[str | None] = mapped_column(Text)  # Fernet, like admin secrets
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger)  # replay protection
    recovery_codes: Mapped[list[str]] = mapped_column(JSONB, default=list)  # sha256 hashes, single use


class RefreshToken(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 hex; raw token only in cookie
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)  # one login = one rotation family
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(String(16))  # rotated | logout | reuse
    user_agent: Mapped[str | None] = mapped_column(String(300))
    mfa: Mapped[bool] = mapped_column(Boolean, default=False)  # the login passed the second factor


class Classroom(IdMixin, TimestampMixin, Base):
    __tablename__ = "classrooms"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    school_year: Mapped[str | None] = mapped_column(String(16))  # e.g. "2026-2027"
    teacher_name: Mapped[str | None] = mapped_column(String(120))
    invite_token: Mapped[str | None] = mapped_column(String(64), unique=True)


# ---- children and their media ----------------------------------------------------------------


class Child(IdMixin, TimestampMixin, Base):
    __tablename__ = "children"

    guardian_user_id: Mapped[uuid.UUID | None] = mapped_column(  # None until a B2B invite is accepted
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="SET NULL"), index=True
    )
    first_name: Mapped[str] = mapped_column(String(40))
    gender: Mapped[Gender] = mapped_column(str_enum(Gender, "child_gender"))
    birth_year: Mapped[int] = mapped_column(SmallInteger)
    interests: Mapped[list[str]] = mapped_column(JSONB, default=list)
    wears_hijab: Mapped[bool] = mapped_column(Boolean, default=False)  # the parent's choice, never inferred
    wears_glasses: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)  # admin test child (acceptance runs)


class Consent(IdMixin, Base):
    __tablename__ = "consents"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    guardian_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    consent_text_version: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(32), default="photo_processing")
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class ChildPhoto(IdMixin, TimestampMixin, Base):
    __tablename__ = "child_photos"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str | None] = mapped_column(String(300))  # None once deleted
    status: Mapped[PhotoStatus] = mapped_column(
        str_enum(PhotoStatus, "photo_status"), default=PhotoStatus.uploaded
    )
    check_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Character(IdMixin, TimestampMixin, Base):
    __tablename__ = "characters"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    art_style: Mapped[str] = mapped_column(String(32))
    status: Mapped[CharacterStatus] = mapped_column(
        str_enum(CharacterStatus, "character_status"), default=CharacterStatus.generating
    )
    sheet_image_key: Mapped[str | None] = mapped_column(String(300))
    regen_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(100))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # seed, size, prompt id...


class Companion(IdMixin, TimestampMixin, Base):
    """Addendum 1 §1: the child's drawing turned into a reusable companion."""

    __tablename__ = "companions"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[uuid.UUID | None] = mapped_column(  # None → reusable across books
        ForeignKey("books.id", ondelete="SET NULL", use_alter=True)
    )
    name: Mapped[str] = mapped_column(String(30))
    type_hint: Mapped[CompanionType] = mapped_column(str_enum(CompanionType, "companion_type"))
    type_other: Mapped[str | None] = mapped_column(String(30))
    traits: Mapped[str | None] = mapped_column(String(120))
    description_en: Mapped[str | None] = mapped_column(Text)
    drawing_key: Mapped[str | None] = mapped_column(String(300))  # original photo, auto-deleted
    drawing_delete_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    cleaned_key: Mapped[str | None] = mapped_column(String(300))  # kept for the keepsake page
    sheet_key: Mapped[str | None] = mapped_column(String(300))
    regen_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(100))


# ---- themes and books ------------------------------------------------------------------------


class Theme(IdMixin, TimestampMixin, Base):
    __tablename__ = "themes"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title_ar: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str] = mapped_column(String(200))
    age_min: Mapped[int] = mapped_column(SmallInteger)
    age_max: Mapped[int] = mapped_column(SmallInteger)
    occasion: Mapped[str | None] = mapped_column(String(64))
    is_b2b: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    companion_slot: Mapped[bool] = mapped_column(Boolean, default=False)
    # cover, pages[] (scene, beat, layout, text templates, companion_action), default companion
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Book(IdMixin, TimestampMixin, Base):
    __tablename__ = "books"

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("characters.id", ondelete="SET NULL"))
    companion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companions.id", ondelete="SET NULL"))
    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("themes.id", ondelete="RESTRICT"))
    theme_version: Mapped[int] = mapped_column(Integer)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    language: Mapped[Locale] = mapped_column(str_enum(Locale, "book_language"))
    art_style: Mapped[str] = mapped_column(String(32))
    status: Mapped[BookStatus] = mapped_column(str_enum(BookStatus, "book_status"), default=BookStatus.draft)
    title: Mapped[str | None] = mapped_column(String(200))
    dedication: Mapped[str | None] = mapped_column(Text)
    pdf_interior_key: Mapped[str | None] = mapped_column(String(300))
    pdf_cover_key: Mapped[str | None] = mapped_column(String(300))
    proof_pdf_key: Mapped[str | None] = mapped_column(String(300))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    parent_message: Mapped[str | None] = mapped_column(String(120))  # dedication from the parent
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    # Addendum 3: everything that must stay stable across runs and redraws (seed, outfit lock, plan, mode,
    # models used), the adapted story incl. parents page + blurb, costs, flags, QA and preflight results.
    generation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    story: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    qa_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    preflight: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class BookPage(IdMixin, TimestampMixin, Base):
    __tablename__ = "book_pages"
    __table_args__ = (UniqueConstraint("book_id", "index"),)

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(SmallInteger)  # theme page ("beat"); 0 = cover
    text: Mapped[str | None] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text)  # for "restore original" in review
    image_key: Mapped[str | None] = mapped_column(String(300))  # as generated
    print_image_key: Mapped[str | None] = mapped_column(String(300))  # upscaled + fitted to the print box
    preview_image_key: Mapped[str | None] = mapped_column(String(300))  # approved low-res preview
    regen_count: Mapped[int] = mapped_column(SmallInteger, default=0)  # manual redraws (admin/parent)
    safety_status: Mapped[SafetyStatus] = mapped_column(
        str_enum(SafetyStatus, "safety_status"), default=SafetyStatus.pending
    )
    review: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Addendum 3 QA
    layout: Mapped[str | None] = mapped_column(String(16))  # full | split | spread | cover
    status: Mapped[PageStatus] = mapped_column(
        str_enum(PageStatus, "page_status"), default=PageStatus.pending
    )
    qa: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # chosen attempt's QA answers
    qa_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    attempts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))


# ---- orders and printing ---------------------------------------------------------------------


class PrintBatch(IdMixin, TimestampMixin, Base):
    __tablename__ = "print_batches"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    batch_date: Mapped[date] = mapped_column(Date)
    status: Mapped[PrintBatchStatus] = mapped_column(
        str_enum(PrintBatchStatus, "print_batch_status"), default=PrintBatchStatus.open
    )
    bundle_key: Mapped[str | None] = mapped_column(String(300))
    printer_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Phase 3 print batches: the printer's download link is a token whose sha256 is kept here (the raw token
    # is only in the printer's email); each click turns into a fresh signed URL of ≤ 15 minutes.
    printer_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    printer_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # orders, books, files at send
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    printing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    code: Mapped[str] = mapped_column(String(16), unique=True)  # QM-XXXXXX
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus, "order_status"), default=OrderStatus.new
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod, "payment_method"))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus, "payment_status"), default=PaymentStatus.unpaid
    )
    currency: Mapped[Currency] = mapped_column(str_enum(Currency, "currency"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shipping: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # name, phone, city, address
    phone: Mapped[str | None] = mapped_column(String(32), index=True)  # guests track orders by code + phone
    source: Mapped[str] = mapped_column(String(16), default="web")  # web | portal | admin
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shipping_zones.id", ondelete="SET NULL"))
    price_list_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("price_lists.id", ondelete="SET NULL"))
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("coupons.id", ondelete="SET NULL"))
    pricing: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # the pricing engine's breakdown
    cost_ils: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))  # unit costs at ordering
    print_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("print_batches.id", ondelete="SET NULL"), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)


class OrderItem(IdMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    product: Mapped[Product | None] = mapped_column(str_enum(Product, "product"))  # before the catalog
    # snapshots at ordering time, so later catalog edits never change a past order
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), index=True
    )
    sku: Mapped[str | None] = mapped_column(String(64))
    line: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # names and options
    style_slug: Mapped[str | None] = mapped_column(String(40))
    theme_slug: Mapped[str | None] = mapped_column(String(64))
    child_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"))
    personalization: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    addons: Mapped[list[Any]] = mapped_column(JSONB, default=list)  # [{slug, qty, unit_price, unit_cost_ils}]
    quantity: Mapped[int] = mapped_column(SmallInteger, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    costs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # print, packaging, AI estimate…


# ---- admin-managed settings ------------------------------------------------------------------


class AppSetting(Base):
    """One admin-managed setting (registry: qamra_core.app_settings). Secrets live in `secret_ciphertext`."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any | None] = mapped_column(JSONB)
    secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


# ---- leads -------------------------------------------------------------------------------------


class LeadStatus(enum.StrEnum):
    new = "new"
    contacted = "contacted"
    won = "won"
    lost = "lost"


class Lead(IdMixin, CreatedAtMixin, Base):
    """Kindergarten demo requests from the public site (Kindergartens page form)."""

    __tablename__ = "leads"

    kind: Mapped[str] = mapped_column(String(32), default="kindergarten_demo")
    org_name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    contact_name: Mapped[str] = mapped_column(String(120))
    contact_role: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))
    children_count: Mapped[int | None] = mapped_column(SmallInteger)
    event_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    locale: Mapped[Locale] = mapped_column(str_enum(Locale, "lead_locale"), default=Locale.ar)
    status: Mapped[LeadStatus] = mapped_column(str_enum(LeadStatus, "lead_status"), default=LeadStatus.new)


# ---- costs, audit ------------------------------------------------------------------------------


class GenerationCost(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "generation_costs"

    book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"), index=True)
    child_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("children.id", ondelete="SET NULL"))
    step: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    units: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    usd: Mapped[Decimal] = mapped_column(Numeric(10, 5))
    estimated: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(IdMixin, CreatedAtMixin, Base):
    """No PII here: ids and action names only (deleted children stay deleted)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


# ---- family voice (Addendum 1 §3; used in Phase 5) -------------------------------------------


class ShareToken(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "share_tokens"

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)  # printed in QR codes → stored as-is
    scope: Mapped[ShareScope] = mapped_column(str_enum(ShareScope, "share_scope"))
    label: Mapped[str | None] = mapped_column(String(60))  # e.g. "ستّي" for a recording invite
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Recording(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "recordings"
    __table_args__ = (UniqueConstraint("book_id", "page_index", "voice_label"),)

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    page_index: Mapped[int] = mapped_column(SmallInteger)
    voice_label: Mapped[str] = mapped_column(String(30))  # ماما، بابا، ستّي، سيدي
    storage_key: Mapped[str] = mapped_column(String(300))
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_by_share_token_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("share_tokens.id", ondelete="SET NULL")
    )


# ---- notifications (Phase 2: email) -----------------------------------------------------------


class NotificationStatus(enum.StrEnum):
    pending = "pending"
    sent = "sent"
    logged = "logged"  # no SMTP configured: written to the log instead of sent
    skipped = "skipped"  # nobody to write to (a guest order, a closed account, no printer address)
    failed = "failed"


class Notification(IdMixin, TimestampMixin, Base):
    """One outgoing message per `dedupe_key` (an order and a status, a book and a stage, a batch send): jobs
    may run twice, people hear once. No address, name or message body is stored here."""

    __tablename__ = "notifications"

    dedupe_key: Mapped[str] = mapped_column(String(120), unique=True)
    channel: Mapped[str] = mapped_column(String(16), default="email")
    template: Mapped[str] = mapped_column(String(40))
    status: Mapped[NotificationStatus] = mapped_column(
        str_enum(NotificationStatus, "notification_status"), default=NotificationStatus.pending
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), index=True
    )
    book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    print_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("print_batches.id", ondelete="SET NULL")
    )
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    error: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
