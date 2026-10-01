"""The units of «قلبي يعرف الله» as the engine's section styles (Addendum 10 §4.7): each unit's colour, icon
and motif
(content/islamic/units.yaml) become a thumb-index tab, a ribbon and a chip, so the child remembers a page by
its
symbol. Importing this module registers the `islamic` product's styles and the unit icons with the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from qamra_workbook.pictures.islamic import UNIT_GLYPHS, unit_glyph
from qamra_workbook.render import art
from qamra_workbook.render.people import shade
from qamra_workbook.render.sections import BOOK_SECTIONS, PATTERNS, SectionStyle

PRODUCT = "islamic"
UNITS_FILE = Path(__file__).resolve().parents[5] / "content/islamic/units.yaml"
# one tab pattern per unit of a volume, so neighbours differ in grayscale too
PATTERN_CYCLE = tuple(PATTERNS)
LIGHT = 165  # a unit colour brighter than this takes dark ink (white on it would not read)


@dataclass(frozen=True)
class Unit:
    id: str
    volume: str
    area: int
    title_ar: str
    color: str
    icon: str
    motif: str
    slot: int  # its position among its volume's units
    slots: int

    @property
    def glyph(self) -> str:
        """The icon as registered with the engine's icon table."""
        return f"isl-{unit_glyph(self.icon)}"

    @property
    def on_color(self) -> str:
        """The ink that reads on the unit's colour: white, or dark on a light colour."""
        r, g, b = (int(self.color[i : i + 2], 16) for i in (1, 3, 5))
        return "#1C2140" if 0.299 * r + 0.587 * g + 0.114 * b > LIGHT else "#FFFFFF"

    @property
    def style(self) -> SectionStyle:
        return SectionStyle(
            id=self.id,
            name_ar=self.title_ar,
            icon=self.glyph,
            color=self.color,
            tint=shade(self.color, 1.88),
            deep=shade(self.color, 0.55),
            pattern=PATTERN_CYCLE[self.slot % len(PATTERN_CYCLE)],
            slot=self.slot,
            slots=max(self.slots, 2),
        )


def load_units(path: Path = UNITS_FILE) -> dict[str, Unit]:
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))["units"]
    per_volume: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        per_volume.setdefault(str(row["volume"]), []).append(row)
    units: dict[str, Unit] = {}
    for volume, group in per_volume.items():
        for slot, row in enumerate(group):
            units[str(row["id"])] = Unit(
                id=str(row["id"]),
                volume=volume,
                area=int(str(row["area"])),
                title_ar=str(row["title_ar"]),
                color=str(row["color"]),
                icon=str(row["icon"]),
                motif=str(row["motif"]),
                slot=slot,
                slots=len(group),
            )
    return units


UNITS: dict[str, Unit] = load_units()


def volume_units(volume: str) -> list[Unit]:
    return [u for u in UNITS.values() if u.volume == volume]


# the passport and the certificate belong to no unit: gold and green, the colours of the series' own frame
FINALE = SectionStyle(
    id="finale",
    name_ar="رِحْلَةُ الْإِيمَانِ",
    icon="isl-star",
    color="#C9962B",
    tint=shade("#C9962B", 1.88),
    deep=shade("#C9962B", 0.5),
    pattern="stars",
    slot=7,
    slots=8,
)


def register() -> None:
    """Hand the unit icons and the unit styles to the engine (idempotent)."""
    for name, glyph in UNIT_GLYPHS.items():
        art.ICONS[f"isl-{name}"] = glyph
    BOOK_SECTIONS[PRODUCT] = {**{u.id: u.style for u in UNITS.values()}, FINALE.id: FINALE}


register()
