"""Migration 2351cdc1195c (portrait first, 2026-10-10): `characters.portrait_image_key`, and the style
rows' record of the 3D, cartoon and watercolor guides moving from v2 to v3."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_ai.pipeline.style import StyleGuide, history_guide, style_guides
from qamra_api.seed_store import seed_store
from qamra_core.migrations import MIGRATIONS_DIR

REVISION = "2351cdc1195c"
SLUGS = ("3d", "cartoon", "watercolor")


def _module(revision: str = REVISION) -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob(f"*_{revision}_*.py")
    spec = importlib.util.spec_from_file_location(f"migration_{revision}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _as_record(guide: StyleGuide) -> dict[str, Any]:
    negatives = [" ".join(b.split()) for b in ("\n" + guide.negative).split("\n- ") if b.strip()]
    return {
        "prompt": " ".join(guide.look.split()),
        "negative": "\n".join(f"- {b}" for b in negatives),
        "version": guide.version,
    }


def test_the_records_are_the_guides() -> None:
    records = _module().RECORDS
    current = {g.slug: g for g in style_guides()}
    assert set(records) == set(SLUGS)
    for slug in SLUGS:
        # every one moved on to v4 (watercolor 5b7e2c9d4f10, cartoon and 3D 4e1c9a7b2d63): v3 is in history/
        v3 = history_guide(slug, 3) if current[slug].version > 3 else current[slug]
        assert records[slug]["v3"] == _as_record(v3), slug
        assert records[slug]["v2"] == _as_record(history_guide(slug, 2)), slug


async def _rows(adb: AsyncSession) -> dict[str, tuple[int, str]]:
    rows = await adb.execute(
        text("SELECT slug, version, prompt FROM art_styles WHERE slug IN ('3d', 'cartoon', 'watercolor')")
    )
    return {slug: (int(version), str(prompt)) for slug, version, prompt in rows}


async def test_the_record_goes_back_to_v2_and_forward_to_v3(adb: AsyncSession) -> None:
    await seed_store(adb)  # a fresh database: the rows come from the guides (all three at v4)
    module = _module()
    # back to v3 first, as before the later migrations (cartoon and 3D, then watercolor)
    for later in (_module("4e1c9a7b2d63"), _module("5b7e2c9d4f10")):
        await adb.run_sync(lambda session, m=later: m.record(session.connection(), forward=False))

    def step(session: Session, forward: bool) -> None:
        module.record(session.connection(), forward=forward)

    assert {slug: v for slug, (v, _) in (await _rows(adb)).items()} == dict.fromkeys(SLUGS, 3)
    await adb.run_sync(step, False)
    back = await _rows(adb)
    for slug in SLUGS:
        assert back[slug] == (2, module.RECORDS[slug]["v2"]["prompt"])
    await adb.run_sync(step, False)  # a row already at v2 is left alone
    assert await _rows(adb) == back
    await adb.run_sync(step, True)
    for slug, (version, prompt) in (await _rows(adb)).items():
        assert (version, prompt) == (3, module.RECORDS[slug]["v3"]["prompt"])
    column = await adb.execute(
        text(
            "SELECT data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'characters' AND column_name = 'portrait_image_key'"
        )
    )
    assert column.one() == ("character varying", "YES")
