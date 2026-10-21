"""Migration 4e1c9a7b2d63 (2026-10-21): the cartoon and 3D rows' records move from guide v3 to v4 (the child's
own face shape, never a rounder, wider, younger face)."""

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

REVISION = "4e1c9a7b2d63"
SLUGS = ("3d", "cartoon")


def _module() -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob(f"*_{REVISION}_*.py")
    spec = importlib.util.spec_from_file_location(f"migration_{REVISION}", path)
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
        assert records[slug]["v4"] == _as_record(current[slug]), slug
        assert records[slug]["v3"] == _as_record(history_guide(slug, 3)), slug


async def _rows(adb: AsyncSession, where: str) -> list[tuple[str, int, str]]:
    rows = await adb.execute(
        text(f"SELECT slug, version, prompt FROM art_styles WHERE {where} ORDER BY slug")
    )
    return [(str(s), int(v), str(p)) for s, v, p in rows]


async def test_the_records_go_back_to_v3_and_forward_to_v4(adb: AsyncSession) -> None:
    await seed_store(adb)  # a fresh database: the rows come from the guides, at v4
    module = _module()
    mine = "slug IN ('3d', 'cartoon')"
    others = await _rows(adb, f"NOT ({mine})")

    def step(session: Session, forward: bool) -> None:
        module.record(session.connection(), forward=forward)

    assert [v for _, v, _ in await _rows(adb, mine)] == [4, 4]
    await adb.run_sync(step, False)
    back = await _rows(adb, mine)
    assert back == [(s, 3, module.RECORDS[s]["v3"]["prompt"]) for s in SLUGS]
    await adb.run_sync(step, False)  # rows already at v3 are left alone
    assert await _rows(adb, mine) == back
    await adb.run_sync(step, True)
    assert await _rows(adb, mine) == [(s, 4, module.RECORDS[s]["v4"]["prompt"]) for s in SLUGS]
    assert await _rows(adb, f"NOT ({mine})") == others  # no other style is touched
