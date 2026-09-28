"""Server-side carts (Addendum 4 §5).

Guests hold their cart through an httpOnly cookie, and the database keeps only the token's hash. A signed-in
parent's cart is theirs across devices, and a guest cart is adopted when they sign in. The cart's currency
follows the shipping zone (Palestine → ILS, Jordan → JOD).
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.settings import ApiSettings
from qamra_core.db.models import Currency, Order, OrderStatus, User
from qamra_core.db.store import Cart, CartItem, CartStatus, Coupon, CouponKind, CouponRedemption
from qamra_core.pricing import CouponRule

COOKIE = "qamra_cart"
TTL = timedelta(days=30)
GENDERS = ("m", "f")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def find_cart(db: AsyncSession, request: Request, user: User | None) -> Cart | None:
    cart = None
    if user is not None:
        cart = (
            await db.execute(
                select(Cart)
                .where(Cart.user_id == user.id, Cart.status == CartStatus.open)
                .order_by(Cart.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    token = request.cookies.get(COOKIE)
    if cart is None and token:
        cart = (
            await db.execute(
                select(Cart).where(Cart.token_hash == token_hash(token), Cart.status == CartStatus.open)
            )
        ).scalar_one_or_none()
        if cart is not None and cart.user_id is None and user is not None:
            cart.user_id = user.id  # signing in adopts the guest cart
    return cart


async def ensure_cart(
    db: AsyncSession, request: Request, response: Response, user: User | None, settings: ApiSettings
) -> Cart:
    cart = await find_cart(db, request, user)
    if cart is not None:
        return cart
    token = secrets.token_urlsafe(32)
    cart = Cart(
        token_hash=token_hash(token),
        user_id=user.id if user is not None else None,
        currency=Currency.ILS,
        expires_at=datetime.now(UTC) + TTL,
    )
    db.add(cart)
    await db.flush()
    response.set_cookie(
        COOKIE,
        token,
        max_age=int(TTL.total_seconds()),
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return cart


async def cart_items(db: AsyncSession, cart: Cart) -> list[CartItem]:
    rows = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.created_at))
    return list(rows.scalars())


def clean_personalization(raw: dict[str, Any]) -> dict[str, Any]:
    """Only the fields the storefront collects; photos never live here (they go through consent + storage)."""
    out: dict[str, Any] = {}
    name = " ".join(str(raw.get("child_name", "")).split())
    if name:
        if len(name) > 40:
            raise ValueError("child_name")
        out["child_name"] = name
    if raw.get("gender") is not None:
        if raw["gender"] not in GENDERS:
            raise ValueError("gender")
        out["gender"] = raw["gender"]
    if raw.get("age") is not None:
        age = int(raw["age"])
        if not 2 <= age <= 12:
            raise ValueError("age")
        out["age"] = age
    for flag in ("hijab", "glasses"):
        if raw.get(flag) is not None:
            out[flag] = bool(raw[flag])
    for key, limit in (("dedication", 120), ("custom_brief", 1200)):
        text = str(raw.get(key) or "").strip()
        if text:
            if len(text) > limit:
                raise ValueError(key)
            out[key] = text
    return out


def _digits(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())[-9:]


async def coupon_rule(
    db: AsyncSession,
    code: str,
    currency: Currency,
    *,
    user_id: uuid.UUID | None = None,
    phone: str | None = None,
) -> tuple[CouponRule | None, Coupon | None, str | None]:
    """Load a coupon and check everything that needs the database. The customer checks (first order, uses
    per customer) run once we know who they are: the user in the cart, the phone at checkout."""
    coupon = (
        await db.execute(select(Coupon).where(Coupon.code == code.strip().upper()))
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if coupon is None or not coupon.active:
        return None, None, "unknown"
    if (coupon.starts_at and now < coupon.starts_at) or (coupon.ends_at and now >= coupon.ends_at):
        return None, coupon, "expired"
    if coupon.max_uses is not None and coupon.uses >= coupon.max_uses:
        return None, coupon, "used_up"
    if coupon.kind == CouponKind.fixed and coupon.currency not in (None, currency):
        return None, coupon, "currency"
    who = []
    if user_id is not None:
        who.append(Order.user_id == user_id)
    if phone:
        who.append(Order.phone == phone)
    if who and coupon.first_order_only:
        previous = (
            await db.execute(
                select(func.count())
                .select_from(Order)
                .where(or_(*who), Order.status != OrderStatus.cancelled)
            )
        ).scalar_one()
        if previous:
            return None, coupon, "first_order_only"
    if who and coupon.per_customer is not None:
        mine = []
        if user_id is not None:
            mine.append(CouponRedemption.user_id == user_id)
        if phone:
            mine.append(CouponRedemption.phone == phone)
        used = (
            await db.execute(
                select(func.count())
                .select_from(CouponRedemption)
                .where(CouponRedemption.coupon_id == coupon.id, or_(*mine))
            )
        ).scalar_one()
        if used >= coupon.per_customer:
            return None, coupon, "already_used"
    rule = CouponRule(
        code=coupon.code,
        kind=coupon.kind.value,
        value=coupon.value,
        min_subtotal=coupon.min_subtotal,
        lines=tuple(coupon.lines),
    )
    return rule, coupon, None


def same_phone(a: str, b: str) -> bool:
    return len(_digits(a)) >= 7 and _digits(a) == _digits(b)
