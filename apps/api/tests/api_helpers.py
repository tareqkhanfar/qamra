from httpx import AsyncClient


async def register(
    client: AsyncClient,
    email: str = "salma.mom@example.com",
    password: str = "moonlight-2026",
    name: str = "أم سلمى",
) -> dict:  # type: ignore[type-arg]
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": password, "full_name": name}
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def make_admin(
    client: AsyncClient,
    adb,  # type: ignore[no-untyped-def]
    email: str = "admin@example.com",
    password: str = "moonlight-2026",
    roles: tuple[str, ...] = ("owner",),
) -> str:
    """Staff member with 2FA on and the given staff roles, signed in through password + TOTP.
    Returns the TOTP secret."""
    import uuid
    from datetime import UTC, datetime

    import pyotp

    from qamra_core.crypto import DEV_KEY, _cipher, encrypt
    from qamra_core.db.models import User, UserRole
    from qamra_core.db.store import StaffRole, UserStaffRole

    me = await register(client, email=email, password=password)
    user = await adb.get(User, uuid.UUID(me["id"]))
    assert user is not None
    secret = pyotp.random_base32()
    user.role = UserRole.admin
    user.totp_secret_ciphertext = encrypt(_cipher(DEV_KEY), secret)
    user.totp_enabled_at = datetime.now(UTC)
    for role in roles:
        adb.add(UserStaffRole(user_id=user.id, role=StaffRole(role), granted_at=datetime.now(UTC)))
    await adb.commit()
    await client.post("/api/auth/logout")
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200 and r.json() == {"mfa_required": True}, r.text
    r = await client.post("/api/auth/mfa/verify", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200 and r.json()["mfa_verified"], r.text
    return secret


async def complete_cart(adb) -> None:  # type: ignore[no-untyped-def]
    """Every open cart line gets a child and, for a story, a book: what «أكملوا بيانات الطفل» does through the
    create flow. For tests about prices and orders rather than the create flow (checkout refuses lines that
    wait for the child)."""
    from datetime import date

    from sqlalchemy import select

    from qamra_api.seed import upsert_themes
    from qamra_api.store.cart import STORY_LINES
    from qamra_core.db.models import Book, Child, Gender, Locale, Theme
    from qamra_core.db.store import Cart, CartItem, CartStatus, CatalogProduct, Variant

    rows = await adb.execute(
        select(CartItem, CatalogProduct.line)
        .join(Cart, Cart.id == CartItem.cart_id)
        .join(Variant, Variant.id == CartItem.variant_id)
        .join(CatalogProduct, CatalogProduct.id == Variant.product_id)
        .where(Cart.status == CartStatus.open)
    )
    for item, line in rows.all():
        if item.child_id is None:
            child = Child(
                first_name=item.personalization.get("child_name", "ليان"),
                gender=Gender.f,
                birth_year=date.today().year - 5,
            )
            adb.add(child)
            await adb.flush()
            item.child_id = child.id
        if line.value in STORY_LINES and item.book_id is None:
            theme = (await adb.execute(select(Theme).limit(1))).scalar_one_or_none()
            if theme is None:
                await upsert_themes(adb)
                theme = (await adb.execute(select(Theme).limit(1))).scalar_one()
            book = Book(
                child_id=item.child_id,
                theme_id=theme.id,
                theme_version=theme.version,
                language=Locale.ar,
                art_style=item.style_slug or "watercolor",
                generation={"line": line.value},
            )
            adb.add(book)
            await adb.flush()
            item.book_id = book.id
    await adb.commit()


async def open_jordan(adb) -> None:  # type: ignore[no-untyped-def]
    """Switch the Jordan delivery zones back on, as the admin would: they are seeded inactive (we deliver to
    the West Bank and Jerusalem only since 2026-10-05), and their JOD path is kept for when Jordan returns."""
    from sqlalchemy import update

    from qamra_core.db.store import ShippingZone

    await adb.execute(update(ShippingZone).where(ShippingZone.country == "JO").values(active=True))
    await adb.commit()


async def sell_every_addon(adb) -> None:  # type: ignore[no-untyped-def]
    """Switch every add-on on, as the admin can: the seed keeps the extras we cannot deliver switched off
    (owner's decision, 2026-10-07; migration 18342eeba4e4). For tests of the add-on and pricing mechanics,
    which use the whole catalog; test_order_flow_needs covers the switched-off ones."""
    from sqlalchemy import update

    from qamra_core.db.store import AddOn

    await adb.execute(update(AddOn).values(active=True))
    await adb.commit()
