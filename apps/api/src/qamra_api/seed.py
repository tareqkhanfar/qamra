"""Load content/themes/*/theme.yaml into the database (idempotent upsert; runs on every deploy).

Every theme keeps a version history (qamra_api.theme_versions). A file's definition goes live when its
version is newer than every version of the theme, or corrects its own live version in place. A theme whose
live version was published from the template studio is left alone (a higher file version replaces it).
"""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import CONTENT_DIR, load_theme
from qamra_api.theme_versions import ensure_live, sync_file, theme_columns
from qamra_core.db.models import Theme


async def upsert_themes(db: AsyncSession, content_dir: Path = CONTENT_DIR) -> list[str]:
    changed: list[str] = []
    for path in sorted((content_dir / "themes").glob("*/theme.yaml")):
        theme = load_theme(path.parent.name, content_dir)  # validates the story before it goes live
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        row = (await db.execute(select(Theme).where(Theme.slug == theme.slug))).scalar_one_or_none()
        if row is None:
            row = Theme(slug=theme.slug, definition=raw, **theme_columns(theme))
            db.add(row)
            await db.flush()
            await ensure_live(db, row)  # the first entry of its history
            changed.append(f"+{theme.slug}")
        else:
            changed.append(await sync_file(db, row, theme, raw))
    await db.commit()
    return changed
