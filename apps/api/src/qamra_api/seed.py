"""Load content/themes/*/theme.yaml into the database (idempotent upsert; runs on every deploy)."""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import CONTENT_DIR, load_theme
from qamra_core.db.models import Theme


async def upsert_themes(db: AsyncSession, content_dir: Path = CONTENT_DIR) -> list[str]:
    changed: list[str] = []
    for path in sorted((content_dir / "themes").glob("*/theme.yaml")):
        theme = load_theme(path.parent.name, content_dir)  # validates the story before it goes live
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        values = {
            "version": theme.version,
            "title_ar": theme.title_ar,
            "title_en": theme.title_en,
            "age_min": theme.age_range[0],
            "age_max": theme.age_range[1],
            "occasion": theme.catalog.occasions[0] if theme.catalog and theme.catalog.occasions else None,
            "is_b2b": theme.is_b2b,
            "active": theme.active,
            "companion_slot": theme.companion_slot,
            "definition": raw,
        }
        row = (await db.execute(select(Theme).where(Theme.slug == theme.slug))).scalar_one_or_none()
        if row is None:
            db.add(Theme(slug=theme.slug, **values))
            changed.append(f"+{theme.slug}")
        else:
            for k, v in values.items():
                setattr(row, k, v)
            changed.append(f"~{theme.slug}")
    await db.commit()
    return changed
