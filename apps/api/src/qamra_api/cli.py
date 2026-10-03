"""Admin CLI: `qamra create-user …`, `qamra seed-themes`, `qamra seed-store`, `qamra reset-2fa --email …`,
`qamra islamic-review-export [--out PATH]`."""

import argparse
import asyncio
import getpass
from datetime import UTC, datetime
from pathlib import Path

from qamra_api.auth import service as auth
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_api.settings import get_settings
from qamra_core.db.models import Locale, UserRole
from qamra_core.db.session import make_async_engine, make_async_sessionmaker
from qamra_core.db.store import StaffRole, UserStaffRole
from qamra_core.islamic_review import EXPORT_DEFAULT, build_export, load_state, write_export


async def create_user(email: str, name: str, role: UserRole, password: str, staff_roles: list[str]) -> None:
    """Staff (role admin) get staff roles too (Addendum 4 §3.6); the first one is usually the owner."""
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            user = await auth.register(
                db, email=email, password=password, full_name=name, locale=Locale.ar, role=role
            )
            if role == UserRole.admin:
                for staff_role in staff_roles:
                    db.add(
                        UserStaffRole(
                            user_id=user.id, role=StaffRole(staff_role), granted_at=datetime.now(UTC)
                        )
                    )
            await db.commit()
            print(
                f"created {user.role.value} {user.email} ({user.id})",
                staff_roles if role == UserRole.admin else "",
            )
    finally:
        await engine.dispose()


async def seed_themes() -> None:
    """Upsert every theme under content/themes into the database."""
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            print("themes:", " ".join(await upsert_themes(db)))
    finally:
        await engine.dispose()


async def seed_store_cmd() -> None:
    """Insert the starting catalog, add-ons, rules and art styles that don't exist yet."""
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            added = await seed_store(db)
            print("store:", " ".join(added) if added else "up to date")
    finally:
        await engine.dispose()


async def reset_2fa(email: str) -> None:
    """Server-side recovery when an admin lost the authenticator and the recovery codes.

    Turns 2FA off and signs the account out everywhere; the admin area then asks for a new setup.
    """
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            user = await auth.find_user_by_email(db, email)
            if user is None:
                raise SystemExit(f"no user {email}")
            user.totp_enabled_at = None
            user.totp_secret_ciphertext = None
            user.totp_last_step = None
            user.recovery_codes = []
            await auth.revoke_all_sessions(db, user, "mfa_reset")
            auth.audit(db, "user.mfa_reset_by_cli", user.id)
            await db.commit()
            print(f"2FA reset for {user.email}; all sessions signed out")
    finally:
        await engine.dispose()


async def islamic_review_export(out: Path) -> None:
    """«قلبي يعرف الله»: the scholar's review as the page engine reads it, for renders outside the worker (the
    worker writes its own before every render). The file is not committed: the database is the record."""
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            data = build_export(await load_state(db))
        approved = [v for v, info in data["volumes"].items() if info["approved"]]
        print(f"wrote {write_export(data, out)}; approved volumes: {', '.join(approved) or 'none'}")
    finally:
        await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(prog="qamra")
    sub = p.add_subparsers(dest="cmd", required=True)
    cu = sub.add_parser("create-user")
    cu.add_argument("--email", required=True)
    cu.add_argument("--name", required=True)
    cu.add_argument("--role", choices=[r.value for r in UserRole], default="parent")
    cu.add_argument("--password", help="omit to be prompted (keeps it out of shell history)")
    cu.add_argument(
        "--staff-roles",
        default="owner",
        help=f"for --role admin, comma-separated: {', '.join(r.value for r in StaffRole)}",
    )
    sub.add_parser("seed-themes")
    sub.add_parser("seed-store")
    r2 = sub.add_parser("reset-2fa")
    r2.add_argument("--email", required=True)
    ie = sub.add_parser("islamic-review-export")
    ie.add_argument("--out", type=Path, default=EXPORT_DEFAULT)
    args = p.parse_args()
    if args.cmd == "create-user":
        password = args.password or getpass.getpass("password: ")
        staff = [r.strip() for r in args.staff_roles.split(",") if r.strip()]
        asyncio.run(create_user(args.email, args.name, UserRole(args.role), password, staff))
    elif args.cmd == "seed-themes":
        asyncio.run(seed_themes())
    elif args.cmd == "seed-store":
        asyncio.run(seed_store_cmd())
    elif args.cmd == "reset-2fa":
        asyncio.run(reset_2fa(args.email))
    elif args.cmd == "islamic-review-export":
        asyncio.run(islamic_review_export(args.out))


if __name__ == "__main__":
    main()
