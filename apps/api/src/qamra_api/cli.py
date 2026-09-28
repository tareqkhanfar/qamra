"""Admin CLI: `qamra create-user ...`, `qamra seed-themes`."""

import argparse
import asyncio
import getpass

import yaml
from qamra_core.db.models import Locale, Theme, UserRole
from qamra_core.db.session import make_async_engine, make_async_sessionmaker
from sqlalchemy import select

from qamra_api.auth import service as auth
from qamra_api.settings import get_settings

try:
    from qamra_ai.pipeline.theme import CONTENT_DIR, load_theme
except ImportError:  # pragma: no cover
    CONTENT_DIR = None  # type: ignore[assignment]


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
    """Upsert every theme under content/themes into the database (definitions stay editable in admin)."""
    settings = get_settings()
    engine = make_async_engine(settings.database_url, 1)
    try:
        async with make_async_sessionmaker(engine)() as db:
            for path in sorted((CONTENT_DIR / "themes").glob("*/theme.yaml")):
                theme = load_theme(path.parent.name)  # validates
                raw = yaml.safe_load(path.read_text(encoding="utf-8"))
                row = (await db.execute(select(Theme).where(Theme.slug == theme.slug))).scalar_one_or_none()
                values = dict(
                    version=theme.version,
                    title_ar=theme.title_ar,
                    title_en=theme.title_en,
                    age_min=theme.age_range[0],
                    age_max=theme.age_range[1],
                    occasion=raw.get("occasion"),
                    is_b2b=theme.is_b2b,
                    active=theme.active,
                    companion_slot=theme.companion_slot,
                    definition=raw,
                )
                if row is None:
                    db.add(Theme(slug=theme.slug, **values))
                    print(f"+ theme {theme.slug}")
                else:
                    for k, v in values.items():
                        setattr(row, k, v)
                    print(f"~ theme {theme.slug}")
            await db.commit()
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
