"""«شبه حقيقي» v3 (2026-10-10): the migration's record of the look and negatives is the guide's own text, and
its v2 record is the kept v2 guide and what migration a58eeffa5362 wrote. No database needed."""

import importlib.util
from pathlib import Path
from types import ModuleType

from qamra_ai.pipeline.style import StyleGuide, history_guide, style_guides
from qamra_core.migrations import MIGRATIONS_DIR


def _module(revision: str) -> ModuleType:
    [path] = (Path(MIGRATIONS_DIR) / "versions").glob(f"*_{revision}_*.py")
    spec = importlib.util.spec_from_file_location(f"migration_{revision}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _as_record(guide: StyleGuide) -> tuple[int, str, str]:
    """(version, look, negatives) as the row keeps them: one line, and one line per negative."""
    negatives = [" ".join(b.split()) for b in ("\n" + guide.negative).split("\n- ") if b.strip()]
    return guide.version, " ".join(guide.look.split()), "\n".join(f"- {b}" for b in negatives)


def _of(record: dict[str, object]) -> tuple[object, object, object]:
    return record["version"], record["prompt"], record["negative"]


def test_the_v3_record_is_the_guide() -> None:
    v3 = _module("968a4be3c42d")
    guide = next(g for g in style_guides() if g.slug == "semi-realistic")
    assert _of(v3.V3) == _as_record(guide)
    assert _of(v3.V2) == _as_record(history_guide("semi-realistic", 2))
    a58 = _module("a58eeffa5362")
    assert _of(v3.V2) == _of(a58.NOW)
