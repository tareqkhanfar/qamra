"""Load content/themes/*/theme.yaml into the database (idempotent upsert; runs on every deploy).

Every theme keeps a version history (qamra_api.theme_versions). A file's definition goes live when its
version is newer than every version of the theme, or corrects its own live version in place. A theme whose
live version was published from the template studio is left alone (a higher file version replaces it).

A tashkeel or wording fix in a theme file (`qamra_ai.pipeline.vowelize.FIXES`: `CORRECTIONS`, `TEXT_FIXES`)
is also made in the theme's stored versions and in every Classic template's pinned definition and cached
vowelization, which is re-keyed to the corrected words: the fixed text prints at once and no text is sent to
the model again.
"""

from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.classic import parse_variant
from qamra_ai.pipeline.theme import CONTENT_DIR, load_theme
from qamra_ai.pipeline.vowelize import FIXES, corrected_cache, corrected_definition
from qamra_api.theme_versions import ensure_live, sync_file, theme_columns
from qamra_core.db.classic import ClassicTemplate
from qamra_core.db.models import Theme
from qamra_core.db.studio import ThemeVersion


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
    changed += await correct_texts(db)
    await db.commit()
    return changed


async def correct_texts(db: AsyncSession) -> list[str]:
    """The `FIXES` made in the stored themes, their versions and the Classic templates (idempotent):
    «!slug:style:variant» for each template corrected, «…:texts» when its cached vowelization was corrected
    and re-keyed too."""
    slugs = sorted({c.theme for c in FIXES})
    rows = (await db.execute(select(Theme).where(Theme.slug.in_(slugs)))).scalars().all()
    out: list[str] = []
    for row in rows:
        row.definition = corrected_definition(row.definition)
        versions = await db.execute(select(ThemeVersion).where(ThemeVersion.theme_id == row.id))
        for version in versions.scalars():
            version.definition = corrected_definition(version.definition)
        templates = await db.execute(select(ClassicTemplate).where(ClassicTemplate.theme_id == row.id))
        for t in templates.scalars():
            pinned = t.generation.get("theme_def")
            if not pinned:
                continue
            done = corrected_cache(pinned, t.generation.get("texts") or {}, parse_variant(t.variant).gender)
            if done is None:
                continue
            definition, cache = done
            rekeyed = bool(cache) and cache.get("hash") != (t.generation.get("texts") or {}).get("hash")
            t.generation = {**t.generation, "theme_def": definition, **({"texts": cache} if cache else {})}
            out.append(f"!{row.slug}:{t.art_style}:{t.variant}" + (":texts" if rekeyed else ""))
    await db.flush()
    return out
