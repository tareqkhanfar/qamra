"""Migration 5b7e2c9d4f10 (2026-10-19): the watercolor row's record moves from guide v3 to v4 (clean, clear
colour, never a sepia or amber cast)."""

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

REVISION = "5b7e2c9d4f10"


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
    [current] = [g for g in style_guides() if g.slug == "watercolor"]
    assert records["v4"] == _as_record(current)
    assert records["v3"] == _as_record(history_guide("watercolor", 3))


async def _row(adb: AsyncSession) -> tuple[int, str]:
    version, prompt = (
        await adb.execute(text("SELECT version, prompt FROM art_styles WHERE slug = 'watercolor'"))
    ).one()
    return int(version), str(prompt)


async def test_the_record_goes_back_to_v3_and_forward_to_v4(adb: AsyncSession) -> None:
    await seed_store(adb)  # a fresh database: the row comes from the guide, at v4
    module = _module()
    before = list(
        await adb.execute(
            text("SELECT slug, version, prompt FROM art_styles WHERE slug <> 'watercolor' ORDER BY slug")
        )
    )

    def step(session: Session, forward: bool) -> None:
        module.record(session.connection(), forward=forward)

    assert (await _row(adb))[0] == 4
    await adb.run_sync(step, False)
    assert await _row(adb) == (3, module.RECORDS["v3"]["prompt"])
    await adb.run_sync(step, False)  # a row already at v3 is left alone
    assert (await _row(adb))[0] == 3
    await adb.run_sync(step, True)
    assert await _row(adb) == (4, module.RECORDS["v4"]["prompt"])
    others = await adb.execute(
        text("SELECT slug, version, prompt FROM art_styles WHERE slug <> 'watercolor' ORDER BY slug")
    )
    assert list(others) == before  # no other style is touched
