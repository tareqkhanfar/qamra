"""Admin CLI: `qamra create-user ...`, `qamra seed-themes`."""

import argparse
import asyncio
import getpass

from qamra_core.db.models import Locale, UserRole
from qamra_core.db.session import make_async_engine, make_async_sessionmaker

from qamra_api.auth import service as auth
from qamra_api.seed import upsert_themes
from qamra_api.settings import get_settings


async def create_user(email: str, name: str, role: UserRole, password: str) -> None:
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            user = await auth.register(
                db, email=email, password=password, full_name=name, locale=Locale.ar, role=role
            )
            await db.commit()
            print(f"created {user.role.value} {user.email} ({user.id})")
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


def main() -> None:
    p = argparse.ArgumentParser(prog="qamra")
    sub = p.add_subparsers(dest="cmd", required=True)
    cu = sub.add_parser("create-user")
    cu.add_argument("--email", required=True)
    cu.add_argument("--name", required=True)
    cu.add_argument("--role", choices=[r.value for r in UserRole], default="parent")
    cu.add_argument("--password", help="omit to be prompted (keeps it out of shell history)")
    sub.add_parser("seed-themes")
    args = p.parse_args()
    if args.cmd == "create-user":
        password = args.password or getpass.getpass("password: ")
        asyncio.run(create_user(args.email, args.name, UserRole(args.role), password))
    elif args.cmd == "seed-themes":
        asyncio.run(seed_themes())


if __name__ == "__main__":
    main()
