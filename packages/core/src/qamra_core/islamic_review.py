"""«قلبي يعرف الله» (Addendum 10 §3.3): which volumes the scholar has approved, and the review export.

A volume may be sold and printed only while every one of its units is `approved`. The units of a volume are
the ones `content/islamic/units.yaml` lists for it, plus one unit for the volume's front and back matter
(`matter-v1`…: the cover, the passport, the final assessment, the certificate). A unit added to the content
later has no approval yet, so its volume stops selling until the scholar approves it.

The export (`build_export`) is what the page engine reads: per volume whether it is approved and the name for
«راجعه علميًّا: …» (only when every scholar who approved it agreed to be named), per unit its status, and the
scholar's answers to the `scholar_decision` points. The worker writes it before every render and points
`QAMRA_ISLAMIC_REVIEW_FILE` at it; `qamra islamic-review-export` writes it to
`content/islamic/review-status.json` for local renders; `GET /api/admin/islamic/review/export` returns it.
See docs/decisions.md («قلبي يعرف الله»: the scholar's review).
"""

import json
import os
import tempfile
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from qamra_core.db.islamic import IslamicReviewer, IslamicScholarDecision, IslamicUnitReview, ReviewStatus

CONTENT_DIR = Path(os.environ.get("QAMRA_CONTENT_DIR") or Path(__file__).resolve().parents[4] / "content")
UNITS_FILE = CONTENT_DIR / "islamic" / "units.yaml"
EXPORT_ENV = "QAMRA_ISLAMIC_REVIEW_FILE"
EXPORT_DEFAULT = CONTENT_DIR / "islamic" / "review-status.json"
EXPORT_VERSION = 1

VOLUMES = ("V1", "V2", "V3", "V4", "V5", "R")
VOLUME_NAMES_AR = {
    "V1": "المجلد الأول",
    "V2": "المجلد الثاني",
    "V3": "المجلد الثالث",
    "V4": "المجلد الرابع",
    "V5": "المجلد الخامس",
    "R": "كتاب رمضان والعيد",
}
# the store's `volume` option: one volume, or a set (proposal §10: level 1, level 2, the five volumes)
SETS: dict[str, tuple[str, ...]] = {
    "L1": ("V1", "V2"),
    "L2": ("V3", "V4", "V5"),
    "set": ("V1", "V2", "V3", "V4", "V5"),
}


def volumes_of(option: str | None) -> tuple[str, ...]:
    """The volumes a variant's `volume` option stands for (empty: not a volume of the series)."""
    value = str(option or "").strip()
    if value in SETS:
        return SETS[value]
    return (value,) if value in VOLUMES else ()


def matter_unit(volume: str) -> str:
    """The review unit of a volume's front and back matter."""
    return f"matter-{volume.lower()}"


@dataclass(frozen=True)
class Unit:
    id: str
    volume: str
    title_ar: str
    matter: bool = False


@lru_cache(maxsize=4)
def _units(path: str, mtime: float) -> tuple[Unit, ...]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out = [
        Unit(str(u["id"]), str(u["volume"]), str(u.get("title_ar", "")))
        for u in data.get("units", [])
        if str(u.get("volume")) in VOLUMES
    ]
    present = {u.volume for u in out}
    out += [Unit(matter_unit(v), v, "صفحات البداية والنهاية", matter=True) for v in VOLUMES if v in present]
    return tuple(out)


def content_units(path: Path | None = None) -> tuple[Unit, ...]:
    """Every review unit, volume by volume in the content's order (the matter unit last in its volume)."""
    path = path or UNITS_FILE
    if not path.exists():
        return ()
    units = _units(str(path), path.stat().st_mtime)
    return tuple(sorted(units, key=lambda u: (VOLUMES.index(u.volume), u.matter)))


def units_by_volume(units: Iterable[Unit]) -> dict[str, list[Unit]]:
    out: dict[str, list[Unit]] = {}
    for u in units:
        out.setdefault(u.volume, []).append(u)
    return out


# ---- the state in the database ------------------------------------------------------------------------


@dataclass
class ReviewState:
    rows: dict[str, IslamicUnitReview] = field(default_factory=dict)  # by unit id
    decisions: dict[str, IslamicScholarDecision] = field(default_factory=dict)  # by source id
    reviewers: dict[uuid.UUID, IslamicReviewer] = field(default_factory=dict)  # by user id

    def status(self, unit_id: str) -> ReviewStatus:
        row = self.rows.get(unit_id)
        return row.status if row is not None else ReviewStatus.draft

    def approved_volumes(self, units: Iterable[Unit] | None = None) -> set[str]:
        """Volumes whose every unit is approved (a volume with no unit in the content is never approved)."""
        grouped = units_by_volume(content_units() if units is None else units)
        return {
            v
            for v, us in grouped.items()
            if us and all(self.status(u.id) == ReviewStatus.approved for u in us)
        }


async def load_state(db: AsyncSession) -> ReviewState:
    rows = {r.unit_id: r for r in (await db.execute(select(IslamicUnitReview))).scalars()}
    decisions = {d.source_id: d for d in (await db.execute(select(IslamicScholarDecision))).scalars()}
    reviewers = {r.user_id: r for r in (await db.execute(select(IslamicReviewer))).scalars()}
    return ReviewState(rows, decisions, reviewers)


def load_state_sync(db: Session) -> ReviewState:
    rows = {r.unit_id: r for r in db.execute(select(IslamicUnitReview)).scalars()}
    decisions = {d.source_id: d for d in db.execute(select(IslamicScholarDecision)).scalars()}
    reviewers = {r.user_id: r for r in db.execute(select(IslamicReviewer)).scalars()}
    return ReviewState(rows, decisions, reviewers)


def sellable_volumes(option: str | None, approved: set[str]) -> bool:
    """A variant sells when it stands for volumes and all of them are approved."""
    wanted = volumes_of(option)
    return bool(wanted) and set(wanted) <= approved


# ---- the export the engine reads ------------------------------------------------------------------------


def _day(value: datetime | None) -> str | None:
    return value.astimezone(UTC).date().isoformat() if value else None


def credit_name(names: list[tuple[str, bool]]) -> str | None:
    """«راجعه علميًّا: …»: the scholars' names joined with «و», only when every one of them agreed."""
    if not names or not all(ok for _, ok in names):
        return None
    unique = list(dict.fromkeys(n.strip() for n, _ in names if n.strip()))
    return " و".join(unique) if unique else None


def build_export(state: ReviewState, units: Iterable[Unit] | None = None) -> dict[str, Any]:
    units = tuple(content_units() if units is None else units)
    approved = state.approved_volumes(units)
    out_units: dict[str, Any] = {}
    volumes: dict[str, Any] = {}
    for volume, vunits in units_by_volume(units).items():
        names: dict[str, tuple[str, bool]] = {}
        dates: list[datetime] = []
        for u in vunits:
            row = state.rows.get(u.id)
            status = state.status(u.id)
            out_units[u.id] = {
                "volume": volume,
                "status": status.value,
                "reviewer": row.reviewer_name if row and status == ReviewStatus.approved else None,
                "approved_on": _day(row.approved_at) if row else None,
                "preview_run": row.preview_run if row else None,
            }
            if row is not None and status == ReviewStatus.approved and row.approved_at:
                dates.append(row.approved_at)
                profile = state.reviewers.get(row.reviewer_user_id) if row.reviewer_user_id else None
                key = str(row.reviewer_user_id or row.reviewer_name)
                if profile is not None:
                    names[key] = (profile.name_ar, profile.may_be_named)
                else:
                    names[key] = (row.reviewer_name or "", False)
        ok = volume in approved
        volumes[volume] = {
            "approved": ok,
            "units": [u.id for u in vunits],
            "approved_on": _day(max(dates)) if ok and dates else None,
            "credit_name": credit_name(list(names.values())) if ok else None,
        }
    return {
        "version": EXPORT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "volumes": volumes,
        "units": out_units,
        "decisions": {
            d.source_id: {
                "question": d.question,
                "decision": d.decision,
                "by": d.decided_by_name,
                "on": _day(d.decided_at),
            }
            for d in sorted(state.decisions.values(), key=lambda d: d.source_id)
        },
    }


def write_export(data: Mapping[str, Any], path: Path) -> Path:
    """Write atomically (a render reading it never sees half a file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=".review-", suffix=".json", delete=False
    ) as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    Path(fh.name).replace(path)
    return path
